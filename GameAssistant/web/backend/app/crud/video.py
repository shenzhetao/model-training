from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import Optional
from app.models.video import SourceVideo, VideoExtractionTask
from app.crud.base import CRUDBase


class CRUDSourceVideo(CRUDBase[SourceVideo]):
    """CRUD operations for SourceVideo model."""

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SourceVideo], int]:
        """Get paginated videos with optional filters."""
        query = select(SourceVideo).where(SourceVideo.is_deleted == False)
        count_query = select(func.count(SourceVideo.id)).where(SourceVideo.is_deleted == False)

        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(SourceVideo.uploaded_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        videos = list(result.scalars().all())

        return videos, total

    async def soft_delete(self, db: AsyncSession, id: str) -> bool:
        """Soft delete a video by setting is_deleted=True."""
        await db.execute(
            update(SourceVideo).where(SourceVideo.id == id).values(is_deleted=True)
        )
        await db.flush()
        return True


class CRUDVideoExtractionTask(CRUDBase[VideoExtractionTask]):
    """CRUD operations for VideoExtractionTask model."""

    async def get_by_video_id(
        self,
        db: AsyncSession,
        video_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[VideoExtractionTask], int]:
        """Get extraction tasks for a specific video."""
        query = select(VideoExtractionTask).where(VideoExtractionTask.video_id == video_id)
        count_query = select(func.count(VideoExtractionTask.id)).where(
            VideoExtractionTask.video_id == video_id
        )

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(VideoExtractionTask.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        tasks = list(result.scalars().all())

        return tasks, total

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> tuple[list[VideoExtractionTask], int]:
        """Get paginated extraction tasks."""
        query = select(VideoExtractionTask)
        count_query = select(func.count(VideoExtractionTask.id))

        if status:
            query = query.where(VideoExtractionTask.status == status)
            count_query = count_query.where(VideoExtractionTask.status == status)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(VideoExtractionTask.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        tasks = list(result.scalars().all())

        return tasks, total

    async def update_status(
        self,
        db: AsyncSession,
        task_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update task status."""
        from datetime import datetime
        values = {"status": status}
        if error_message:
            values["error_message"] = error_message
        if status == "running":
            values["started_at"] = datetime.utcnow()
        elif status in ("completed", "failed"):
            values["completed_at"] = datetime.utcnow()

        await db.execute(
            update(VideoExtractionTask).where(VideoExtractionTask.id == task_id).values(**values)
        )
        await db.flush()
        return True

    async def increment_extracted(
        self, db: AsyncSession, task_id: str, count: int = 1
    ) -> bool:
        """Increment extracted frames count."""
        await db.execute(
            update(VideoExtractionTask)
            .where(VideoExtractionTask.id == task_id)
            .values(extracted_frames=VideoExtractionTask.extracted_frames + count)
        )
        await db.flush()
        return True

    async def set_total_frames(
        self, db: AsyncSession, task_id: str, total_frames: int
    ) -> bool:
        """Set total frames count."""
        await db.execute(
            update(VideoExtractionTask)
            .where(VideoExtractionTask.id == task_id)
            .values(total_frames=total_frames)
        )
        await db.flush()
        return True


source_video_crud = CRUDSourceVideo(SourceVideo)
extraction_task_crud = CRUDVideoExtractionTask(VideoExtractionTask)
