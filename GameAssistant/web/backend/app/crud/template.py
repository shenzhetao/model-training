"""CRUD operations for Template and TemplateClass."""
import os
import uuid
import io
from typing import Optional

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template, TemplateClass
from app.models.image import Image
from app.crud.base import CRUDBase
from app.crud.annotation import annotation_class_crud
from app.config import settings


class CRUDTemplateClass(CRUDBase[TemplateClass]):
    async def get_all_ordered(self, db: AsyncSession) -> list[TemplateClass]:
        result = await db.execute(
            select(TemplateClass).order_by(TemplateClass.sort_order)
        )
        return list(result.scalars().all())


class CRUDTemplate(CRUDBase[Template]):
    async def get_multi_paginated(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        class_name: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[Template], int]:
        query = select(Template).where(Template.is_deleted == False)
        count_q = select(func.count(Template.id)).where(Template.is_deleted == False)

        if class_name:
            query = query.where(Template.class_name == class_name)
            count_q = count_q.where(Template.class_name == class_name)
        if is_active is not None:
            query = query.where(Template.is_active == is_active)
            count_q = count_q.where(Template.is_active == is_active)

        total_r = await db.execute(count_q)
        total = total_r.scalar() or 0

        query = query.order_by(Template.class_name, Template.name).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_class(self, db: AsyncSession, class_name: str) -> list[Template]:
        result = await db.execute(
            select(Template).where(
                Template.class_name == class_name,
                Template.is_deleted == False,
                Template.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def soft_delete(self, db: AsyncSession, id: str) -> bool:
        await db.execute(
            update(Template).where(Template.id == id).values(is_deleted=True)
        )
        await db.flush()
        return True


class TemplateUploadHelper:
    """Helper for handling template file uploads."""

    @staticmethod
    def save_template_file(content: bytes, class_name: str, original_name: str) -> tuple[str, int, int]:
        """Save template file and return (file_path, width, height)."""
        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(content))
        w, h = img.size

        ext = os.path.splitext(original_name)[1].lower() or ".png"
        new_name = f"{uuid.uuid4()}{ext}"

        cls_dir = os.path.join(settings.TEMPLATE_DIR, class_name)
        os.makedirs(cls_dir, exist_ok=True)
        file_path = os.path.join(cls_dir, new_name)
        full = os.path.join(settings.TEMPLATE_DIR, file_path)

        img.save(full)
        return file_path, w, h


template_class_crud = CRUDTemplateClass(TemplateClass)
template_crud = CRUDTemplate(Template)
