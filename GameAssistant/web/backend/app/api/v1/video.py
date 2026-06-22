import os
import uuid
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.video import SourceVideo, VideoExtractionTask
from app.schemas.video import (
    SourceVideoResponse,
    SourceVideoListResponse,
    VideoUploadResponse,
    ExtractionTaskCreate,
    ExtractionTaskResponse,
    ExtractionTaskCreateResponse,
    ExtractionTaskListResponse,
    ExtractionStrategy,
    ExtractionStatus,
)
from app.crud.video import source_video_crud, extraction_task_crud
from app.crud.image import image_crud
from app.security import get_current_user
from app.config import settings

router = APIRouter()

# Allowed video extensions
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
MAX_VIDEO_SIZE = 10 * 1024 * 1024 * 1024  # 10GB


def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase."""
    return os.path.splitext(filename)[1].lower()


def is_allowed_video(filename: str) -> bool:
    """Check if file is an allowed video type."""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS


def get_video_metadata(video_path: str) -> dict:
    """Get video metadata using OpenCV."""
    import cv2
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot open video file"
        )
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0
    
    cap.release()
    
    return {
        "fps": float(fps),
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration": float(duration),
    }


async def extract_frames_task(
    task_id: str,
    video_path: str,
    strategy: str,
    interval_seconds: Optional[float],
    frame_count: Optional[int],
    scene_threshold: Optional[float],
    user_id: Optional[str],
    db_url: str,
):
    """Background task to extract frames from video."""
    from app.database import AsyncSessionLocal, engine
    
    async with AsyncSessionLocal() as db:
        try:
            import cv2
            import numpy as np
            from PIL import Image
            import io
            
            # Update task status to running
            await extraction_task_crud.update_status(db, task_id, "running")
            await db.commit()
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                await extraction_task_crud.update_status(
                    db, task_id, "failed", "Cannot open video file"
                )
                await db.commit()
                return
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate which frames to extract based on strategy
            frames_to_extract = []
            
            if strategy == "interval" and interval_seconds:
                interval_frames = int(interval_seconds * fps)
                if interval_frames > 0:
                    frames_to_extract = list(range(0, total_frames, interval_frames))
            elif strategy == "count" and frame_count:
                if frame_count > 0 and total_frames > 0:
                    step = total_frames / frame_count
                    frames_to_extract = [int(i * step) for i in range(frame_count)]
            elif strategy == "scene_change" and scene_threshold:
                # Simple scene change detection using frame difference
                prev_frame = None
                frame_idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    if prev_frame is not None:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                        diff = cv2.absdiff(gray, prev_gray)
                        mean_diff = np.mean(diff)
                        
                        if mean_diff > scene_threshold * 255:
                            frames_to_extract.append(frame_idx)
                    
                    prev_frame = frame.copy()
                    frame_idx += 1
            else:
                # Default: extract every 30 frames (1 second at 30fps)
                frames_to_extract = list(range(0, total_frames, 30))
            
            # Remove duplicates and sort
            frames_to_extract = sorted(set(frames_to_extract))
            await extraction_task_crud.set_total_frames(db, task_id, len(frames_to_extract))
            await db.commit()
            
            # Create images directory
            images_dir = os.path.join(settings.UPLOAD_DIR, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            # Extract frames
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            current_frame = 0
            extracted_count = 0
            duplicates_skipped = 0
            
            for target_frame in frames_to_extract:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, frame = cap.read()
                
                if not ret:
                    continue
                
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Save frame as image
                pil_image = Image.fromarray(rgb_frame)
                
                # Generate unique filename
                timestamp = target_frame / fps if fps > 0 else target_frame
                new_filename = f"{uuid.uuid4()}.jpg"
                file_path = os.path.join("images", new_filename)
                full_path = os.path.join(settings.UPLOAD_DIR, file_path)
                
                # Save image
                pil_image.save(full_path, "JPEG", quality=95)
                
                # Get file size
                file_size = os.path.getsize(full_path)
                
                # Calculate MD5
                with open(full_path, "rb") as f:
                    md5_hash = hashlib.md5(f.read()).hexdigest()
                
                # Check for duplicates (skip if exists)
                existing = await image_crud.get_by_md5(db, md5_hash)
                if existing:
                    os.remove(full_path)
                    duplicates_skipped += 1
                    await extraction_task_crud.increment_extracted(db, task_id, 1)
                    await db.commit()
                    current_frame += 1
                    continue
                
                # Create image record
                image_data = {
                    "filename": new_filename,
                    "original_filename": f"frame_{timestamp:.2f}s.jpg",
                    "file_path": file_path,
                    "file_size": file_size,
                    "width": pil_image.width,
                    "height": pil_image.height,
                    "md5_hash": md5_hash,
                    "source": "video",
                    "source_video_id": None,  # Will be set after we get the task
                    "source_video_timestamp": timestamp,
                    "uploaded_by": user_id,
                }
                
                # Get video_id from task
                task = await extraction_task_crud.get(db, task_id)
                if task:
                    image_data["source_video_id"] = task.video_id
                
                await image_crud.create(db, image_data)
                await extraction_task_crud.increment_extracted(db, task_id, 1)
                await db.commit()
                
                extracted_count += 1
                current_frame += 1
            
            cap.release()
            
            # Update task status to completed
            await extraction_task_crud.update_status(db, task_id, "completed")
            await db.commit()
            
        except Exception as e:
            await extraction_task_crud.update_status(
                db, task_id, "failed", str(e)
            )
            await db.commit()
        finally:
            await engine.dispose()


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a video file."""
    # Validate file extension
    if not is_allowed_video(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if file_size > MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum limit of {MAX_VIDEO_SIZE // (1024**3)}GB"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file not allowed"
        )

    # Generate unique filename
    original_filename = file.filename
    file_ext = get_file_extension(original_filename)
    new_filename = f"{uuid.uuid4()}{file_ext}"

    # Create videos directory if not exists
    videos_dir = os.path.join(settings.UPLOAD_DIR, "videos")
    os.makedirs(videos_dir, exist_ok=True)

    # Save file temporarily
    temp_path = os.path.join(videos_dir, new_filename)
    with open(temp_path, "wb") as f:
        f.write(content)

    # Get video metadata
    try:
        metadata = get_video_metadata(temp_path)
    except Exception as e:
        os.remove(temp_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read video metadata: {str(e)}"
        )

    # Create database record
    file_path = os.path.join("videos", new_filename)
    video_data = {
        "filename": new_filename,
        "original_filename": original_filename,
        "file_path": file_path,
        "file_size": file_size,
        "duration": metadata["duration"],
        "width": metadata["width"],
        "height": metadata["height"],
        "fps": metadata["fps"],
        "uploaded_by": current_user.id,
    }

    db_video = await source_video_crud.create(db, video_data)
    await db.commit()

    return VideoUploadResponse(
        success=True,
        message="Video uploaded successfully",
        video=db_video,
    )


@router.get("/", response_model=SourceVideoListResponse)
async def list_videos(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated list of videos."""
    skip = (page - 1) * page_size

    videos, total = await source_video_crud.get_multi_paginated(
        db,
        skip=skip,
        limit=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return SourceVideoListResponse(
        items=videos,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{video_id}", response_model=SourceVideoResponse)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get video details by ID."""
    video = await source_video_crud.get(db, video_id)
    if not video or video.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    return video


@router.get("/{video_id}/serve")
async def serve_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream video file for viewing."""
    video = await source_video_crud.get(db, video_id)
    if not video or video.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    full_path = os.path.join(settings.UPLOAD_DIR, video.file_path)

    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found on disk"
        )

    # Determine content type
    ext = get_file_extension(video.filename)
    content_types = {
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv',
        '.flv': 'video/x-flv',
        '.webm': 'video/webm',
    }
    content_type = content_types.get(ext, 'video/mp4')

    def iterfile():
        with open(full_path, "rb") as f:
            while chunk := f.read(8192 * 1024):  # 8MB chunks for video
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{video.original_filename}"',
            "Accept-Ranges": "bytes",
        }
    )


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a video."""
    video = await source_video_crud.get(db, video_id)
    if not video or video.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Soft delete
    await source_video_crud.soft_delete(db, video_id)
    await db.commit()

    # Optionally delete file from disk
    full_path = os.path.join(settings.UPLOAD_DIR, video.file_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except OSError:
            pass

    return {"success": True, "message": "Video deleted successfully"}


# ============ Extraction Task Endpoints ============

@router.post("/{video_id}/extract-frames", response_model=ExtractionTaskCreateResponse)
async def create_extraction_task(
    video_id: str,
    task_data: ExtractionTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new frame extraction task."""
    # Check if video exists
    video = await source_video_crud.get(db, video_id)
    if not video or video.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Validate strategy parameters
    if task_data.strategy == ExtractionStrategy.INTERVAL and not task_data.interval_seconds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="interval_seconds is required for interval strategy"
        )
    
    if task_data.strategy == ExtractionStrategy.COUNT and not task_data.frame_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="frame_count is required for count strategy"
        )

    if task_data.strategy == ExtractionStrategy.SCENE_CHANGE and not task_data.scene_threshold:
        # Set default scene threshold
        task_data.scene_threshold = 0.3

    # Create task record
    task_values = {
        "video_id": video_id,
        "strategy": task_data.strategy.value,
        "interval_seconds": task_data.interval_seconds,
        "frame_count": task_data.frame_count,
        "scene_threshold": task_data.scene_threshold,
        "status": "pending",
        "created_by": current_user.id,
    }

    db_task = await extraction_task_crud.create(db, task_values)
    await db.commit()

    # Get video file path
    video_path = os.path.join(settings.UPLOAD_DIR, video.file_path)

    # Start background extraction
    background_tasks.add_task(
        extract_frames_task,
        task_id=db_task.id,
        video_path=video_path,
        strategy=task_data.strategy.value,
        interval_seconds=task_data.interval_seconds,
        frame_count=task_data.frame_count,
        scene_threshold=task_data.scene_threshold,
        user_id=current_user.id,
        db_url=settings.DB_URL,
    )

    return ExtractionTaskCreateResponse(
        success=True,
        message="Extraction task created and running in background",
        task=db_task,
    )


@router.get("/tasks/{task_id}", response_model=ExtractionTaskResponse)
async def get_extraction_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get extraction task details."""
    task = await extraction_task_crud.get(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction task not found"
        )
    return task


@router.get("/tasks/list", response_model=ExtractionTaskListResponse)
async def list_extraction_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Filter by status: pending/running/completed/failed"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated list of extraction tasks."""
    skip = (page - 1) * page_size

    tasks, total = await extraction_task_crud.get_multi_paginated(
        db,
        skip=skip,
        limit=page_size,
        status=status,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return ExtractionTaskListResponse(
        items=tasks,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
