"""CRUD operations for Model."""
import os
import uuid
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model import Model
from app.crud.base import CRUDBase
from app.config import settings


class CRUDModel(CRUDBase[Model]):
    async def get_multi_paginated(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        architecture: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[Model], int]:
        query = select(Model).where(Model.is_deleted == False)
        count_q = select(func.count(Model.id)).where(Model.is_deleted == False)

        if architecture:
            query = query.where(Model.architecture == architecture)
            count_q = count_q.where(Model.architecture == architecture)
        if is_active is not None:
            query = query.where(Model.is_active == is_active)
            count_q = count_q.where(Model.is_active == is_active)

        total_r = await db.execute(count_q)
        total = total_r.scalar() or 0

        query = query.order_by(Model.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def soft_delete(self, db: AsyncSession, id: str) -> bool:
        await db.execute(update(Model).where(Model.id == id).values(is_deleted=True))
        await db.flush()
        return True

    async def set_active(self, db: AsyncSession, id: str) -> bool:
        """Mark a model as active and deactivate all others of the same architecture."""
        job: Model = await self.get(db, id)
        if not job or job.is_deleted:
            return False

        await db.execute(
            update(Model)
            .where(Model.architecture == job.architecture, Model.is_deleted == False)
            .values(is_active=False)
        )
        await db.execute(
            update(Model).where(Model.id == id).values(is_active=True)
        )
        await db.flush()
        return True


def _save_model_file(content: bytes, original_name: str) -> str:
    """Save uploaded model file and return relative path."""
    ext = os.path.splitext(original_name)[1].lower() or ".pt"
    new_name = f"{uuid.uuid4()}{ext}"
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    full_path = os.path.join(settings.MODEL_DIR, new_name)
    with open(full_path, "wb") as f:
        f.write(content)
    return new_name


model_crud = CRUDModel(Model)
