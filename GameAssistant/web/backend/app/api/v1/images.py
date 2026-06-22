import os
import uuid
import hashlib
import zipfile
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image as PILImage

from app.database import get_db
from app.models.user import User
from app.schemas.image import (
    ImageResponse,
    ImageUploadResponse,
    BatchUploadResponse,
    ImageDeleteResponse,
    ImageListResponse,
)
from app.crud.image import image_crud
from app.security import get_current_user
from app.config import settings

router = APIRouter()

# Allowed image extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
MAX_SINGLE_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_BATCH_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB


def calculate_md5(file_content: bytes) -> str:
    """Calculate MD5 hash of file content."""
    return hashlib.md5(file_content).hexdigest()


def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase."""
    return os.path.splitext(filename)[1].lower()


def is_allowed_image(filename: str) -> bool:
    """Check if file is an allowed image type."""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS


async def process_single_image(
    file: UploadFile,
    db: AsyncSession,
    user_id: Optional[str] = None,
    source: str = "upload",
) -> ImageResponse:
    """Process and save a single image file."""
    # Validate file extension
    if not is_allowed_image(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if file_size > MAX_SINGLE_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum limit of {MAX_SINGLE_FILE_SIZE // (1024*1024)}MB"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file not allowed"
        )

    # Calculate MD5
    md5_hash = calculate_md5(content)

    # Check for duplicates
    existing = await image_crud.get_by_md5(db, md5_hash)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Duplicate image detected",
                "existing_image_id": existing.id
            }
        )

    # Get image dimensions
    try:
        image = PILImage.open(io.BytesIO(content))
        width, height = image.size
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file"
        )

    # Generate unique filename
    original_filename = file.filename
    file_ext = get_file_extension(original_filename)
    new_filename = f"{uuid.uuid4()}{file_ext}"

    # Create images directory if not exists
    images_dir = os.path.join(settings.UPLOAD_DIR, "images")
    os.makedirs(images_dir, exist_ok=True)

    # Save file
    file_path = os.path.join("images", new_filename)
    full_path = os.path.join(settings.UPLOAD_DIR, file_path)
    with open(full_path, "wb") as f:
        f.write(content)

    # Create database record
    image_data = {
        "filename": new_filename,
        "original_filename": original_filename,
        "file_path": file_path,
        "file_size": file_size,
        "width": width,
        "height": height,
        "md5_hash": md5_hash,
        "source": source,
        "uploaded_by": user_id,
    }

    db_image = await image_crud.create(db, image_data)
    await db.commit()
    return db_image


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_single_image(
    file: UploadFile = File(...),
    source: str = Query(default="upload", description="Image source: upload/adb/video"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a single image file."""
    try:
        image = await process_single_image(file, db, current_user.id, source)
        return ImageUploadResponse(
            success=True,
            message="Image uploaded successfully",
            image=image,
            is_duplicate=False,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_batch_images(
    file: UploadFile = File(...),
    source: str = Query(default="upload", description="Image source: upload/adb/video"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload images in a ZIP file."""
    # Validate ZIP file
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ZIP files are allowed for batch upload"
        )

    # Read ZIP content
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_BATCH_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ZIP file size exceeds maximum limit of {MAX_BATCH_FILE_SIZE // (1024*1024*1024)}GB"
        )

    uploaded_images = []
    errors = []
    skipped = 0
    duplicates = 0
    failed = 0

    try:
        with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
            # Check for ZIP bomb
            total_size = sum(info.file_size for info in zf.infolist())
            if total_size > 10 * MAX_BATCH_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ZIP file appears to be a bomb (excessive compression ratio)"
                )

            # Create images directory
            images_dir = os.path.join(settings.UPLOAD_DIR, "images")
            os.makedirs(images_dir, exist_ok=True)

            for zip_info in zf.infolist():
                if zip_info.is_dir():
                    continue

                filename = zip_info.filename

                # Skip non-image files
                if not is_allowed_image(filename):
                    continue

                try:
                    # Read file from ZIP
                    file_content = zf.read(filename)

                    # Skip empty files
                    if len(file_content) == 0:
                        skipped += 1
                        continue

                    # Check for duplicates
                    md5_hash = calculate_md5(file_content)
                    existing = await image_crud.get_by_md5(db, md5_hash)

                    if existing:
                        duplicates += 1
                        continue

                    # Get image dimensions
                    try:
                        image = PILImage.open(io.BytesIO(file_content))
                        width, height = image.size
                    except Exception:
                        errors.append(f"{filename}: Invalid image file")
                        failed += 1
                        continue

                    # Generate unique filename
                    original_filename = os.path.basename(filename)
                    file_ext = get_file_extension(original_filename)
                    if not file_ext:
                        file_ext = '.jpg'
                    new_filename = f"{uuid.uuid4()}{file_ext}"

                    # Save file
                    file_path = os.path.join("images", new_filename)
                    full_path = os.path.join(settings.UPLOAD_DIR, file_path)
                    with open(full_path, "wb") as f:
                        f.write(file_content)

                    # Create database record
                    image_data = {
                        "filename": new_filename,
                        "original_filename": original_filename,
                        "file_path": file_path,
                        "file_size": len(file_content),
                        "width": width,
                        "height": height,
                        "md5_hash": md5_hash,
                        "source": source,
                        "uploaded_by": current_user.id,
                    }

                    db_image = await image_crud.create(db, image_data)
                    uploaded_images.append(db_image)

                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
                    failed += 1

            await db.commit()

    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ZIP file"
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process ZIP file: {str(e)}"
        )

    return BatchUploadResponse(
        success=True,
        message=f"Batch upload completed. {len(uploaded_images)} images uploaded.",
        total=len(uploaded_images) + skipped + duplicates + failed,
        uploaded=len(uploaded_images),
        skipped=skipped,
        failed=failed,
        duplicates=duplicates,
        images=uploaded_images,
        errors=errors[:50],  # Limit error messages
    )


@router.get("/", response_model=ImageListResponse)
async def list_images(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source: Optional[str] = Query(default=None, description="Filter by source: upload/adb/video"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated list of images."""
    skip = (page - 1) * page_size

    images, total = await image_crud.get_multi_paginated(
        db,
        skip=skip,
        limit=page_size,
        source=source,
        uploaded_by=None,  # Show all users' images for admin
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return ImageListResponse(
        items=images,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get image details by ID."""
    image = await image_crud.get(db, image_id)
    if not image or image.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    return image


@router.get("/{image_id}/serve")
async def serve_image(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream image file for viewing."""
    image = await image_crud.get(db, image_id)
    if not image or image.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    full_path = os.path.join(settings.UPLOAD_DIR, image.file_path)

    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found on disk"
        )

    # Determine content type
    ext = get_file_extension(image.filename)
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
    }
    content_type = content_types.get(ext, 'application/octet-stream')

    def iterfile():
        with open(full_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{image.original_filename}"',
            "Cache-Control": "public, max-age=31536000",
        }
    )


@router.delete("/{image_id}", response_model=ImageDeleteResponse)
async def delete_single_image(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a single image."""
    image = await image_crud.get(db, image_id)
    if not image or image.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    # Check permissions (only uploader or admin can delete)
    if image.uploaded_by and image.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this image"
        )

    # Soft delete
    await image_crud.soft_delete(db, image_id)
    await db.commit()

    # Optionally delete file from disk
    full_path = os.path.join(settings.UPLOAD_DIR, image.file_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except OSError:
            pass  # File might already be deleted

    return ImageDeleteResponse(
        success=True,
        message="Image deleted successfully",
        deleted_count=1,
    )


@router.delete("/", response_model=ImageDeleteResponse)
async def delete_batch_images(
    image_ids: str = Query(..., description="Comma-separated list of image IDs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete multiple images."""
    try:
        ids = [id.strip() for id in image_ids.split(",") if id.strip()]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_ids format"
        )

    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image IDs provided"
        )

    if len(ids) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 1000 images can be deleted at once"
        )

    # Get images to delete
    deleted_count = 0
    for image_id in ids:
        image = await image_crud.get(db, image_id)
        if image and not image.is_deleted:
            # Check permissions
            if image.uploaded_by and image.uploaded_by != current_user.id and current_user.role != "admin":
                continue

            await image_crud.soft_delete(db, image_id)

            # Optionally delete file from disk
            full_path = os.path.join(settings.UPLOAD_DIR, image.file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except OSError:
                    pass

            deleted_count += 1

    await db.commit()

    return ImageDeleteResponse(
        success=True,
        message=f"{deleted_count} images deleted successfully",
        deleted_count=deleted_count,
    )
