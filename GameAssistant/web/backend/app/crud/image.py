from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from typing import Optional
from app.models.image import Image
from app.crud.base import CRUDBase


class CRUDImage(CRUDBase[Image]):
    """CRUD operations for Image model."""

    async def get_by_md5(self, db: AsyncSession, md5_hash: str) -> Optional[Image]:
        """Get image by MD5 hash."""
        result = await db.execute(
            select(Image).where(Image.md5_hash == md5_hash, Image.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        source: Optional[str] = None,
        uploaded_by: Optional[str] = None,
    ) -> tuple[list[Image], int]:
        """Get paginated images with optional filters."""
        query = select(Image).where(Image.is_deleted == False)
        count_query = select(func.count(Image.id)).where(Image.is_deleted == False)

        if source:
            query = query.where(Image.source == source)
            count_query = count_query.where(Image.source == source)

        if uploaded_by:
            query = query.where(Image.uploaded_by == uploaded_by)
            count_query = count_query.where(Image.uploaded_by == uploaded_by)

        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Image.uploaded_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        images = list(result.scalars().all())

        return images, total

    async def soft_delete(self, db: AsyncSession, id: str) -> bool:
        """Soft delete an image by setting is_deleted=True."""
        await db.execute(
            update(Image).where(Image.id == id).values(is_deleted=True)
        )
        await db.flush()
        return True

    async def soft_delete_batch(self, db: AsyncSession, ids: list[str]) -> int:
        """Soft delete multiple images."""
        result = await db.execute(
            update(Image).where(Image.id.in_(ids)).values(is_deleted=True)
        )
        await db.flush()
        return result.rowcount

    async def get_deleted(self, db: AsyncSession, skip: int = 0, limit: int = 20) -> list[Image]:
        """Get soft-deleted images for recovery."""
        result = await db.execute(
            select(Image)
            .where(Image.is_deleted == True)
            .order_by(Image.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


image_crud = CRUDImage(Image)
