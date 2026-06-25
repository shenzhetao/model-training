"""CRUD operations for Annotation, AnnotationClass, and AnnotationProject."""
import io
import os
import zipfile
from collections import defaultdict
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import (
    Annotation, AnnotationClass, AnnotationProject,
    AnnotationProjectImage, AnnotationReview,
)
from app.models.image import Image
from app.crud.base import CRUDBase
from app.config import settings


class CRUDAnnotationClass(CRUDBase[AnnotationClass]):
    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[AnnotationClass]:
        result = await db.execute(
            select(AnnotationClass).where(AnnotationClass.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_yolo_id(self, db: AsyncSession, yolo_class_id: int) -> Optional[AnnotationClass]:
        result = await db.execute(
            select(AnnotationClass).where(AnnotationClass.yolo_class_id == yolo_class_id)
        )
        return result.scalar_one_or_none()

    async def get_all_ordered(self, db: AsyncSession) -> list[AnnotationClass]:
        result = await db.execute(
            select(AnnotationClass).order_by(AnnotationClass.sort_order, AnnotationClass.yolo_class_id)
        )
        return list(result.scalars().all())


class CRUDAnnotation(CRUDBase[Annotation]):
    async def get_by_image(
        self, db: AsyncSession, image_id: str, project_id: Optional[str] = None
    ) -> list[Annotation]:
        query = select(Annotation).where(Annotation.image_id == image_id)
        if project_id:
            query = query.where(Annotation.project_id == project_id)
        result = await db.execute(
            query.order_by(Annotation.annotated_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_image_class(
        self, db: AsyncSession, image_id: str, class_id: str
    ) -> list[Annotation]:
        result = await db.execute(
            select(Annotation).where(
                and_(
                    Annotation.image_id == image_id,
                    Annotation.class_id == class_id,
                )
            )
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        db: AsyncSession,
        obj_in: dict,
        annotated_by: Optional[str] = None,
    ) -> tuple[Annotation, bool]:
        """Insert or update an annotation. Returns (annotation, is_new)."""
        existing = await db.execute(
            select(Annotation).where(
                and_(
                    Annotation.image_id == obj_in["image_id"],
                    Annotation.project_id == obj_in["project_id"],
                    Annotation.class_id == obj_in["class_id"],
                    Annotation.bbox_x == obj_in["bbox_x"],
                    Annotation.bbox_y == obj_in["bbox_y"],
                    Annotation.bbox_width == obj_in["bbox_width"],
                    Annotation.bbox_height == obj_in["bbox_height"],
                )
            )
        )
        record = existing.scalar_one_or_none()
        is_new = record is None
        if is_new:
            if annotated_by:
                obj_in["annotated_by"] = annotated_by
            record = Annotation(**obj_in)
            db.add(record)
            await db.flush()
            await db.refresh(record)
        return record, is_new

    async def delete_by_image(self, db: AsyncSession, image_id: str) -> int:
        result = await db.execute(
            delete(Annotation).where(Annotation.image_id == image_id)
        )
        await db.flush()
        return result.rowcount

    async def count_by_project(
        self, db: AsyncSession, project_id: str
    ) -> tuple[int, int]:
        """Count (total_annotations, auto_annotations) for a project, filtered by annotation.project_id."""
        total_result = await db.execute(
            select(func.count(Annotation.id))
            .where(Annotation.project_id == project_id)
        )
        total = total_result.scalar() or 0
        auto_result = await db.execute(
            select(func.count(Annotation.id))
            .where(
                and_(
                    Annotation.project_id == project_id,
                    Annotation.is_auto_annotated == True,
                )
            )
        )
        auto = auto_result.scalar() or 0
        return total, auto

    async def export_yolo_zip(
        self,
        db: AsyncSession,
        image_ids: list[str],
        project_id: Optional[str] = None,
    ) -> bytes:
        """Export annotations as a ZIP containing YOLO TXT files and images."""
        if not image_ids:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED):
                pass
            return zip_buffer.getvalue()

        class_map: dict[str, int] = {}
        classes_result = await db.execute(select(AnnotationClass))
        for cls in classes_result.scalars().all():
            class_map[cls.id] = cls.yolo_class_id

        img_result = await db.execute(
            select(Image).where(Image.id.in_(image_ids))
        )
        images: dict[str, Image] = {img.id: img for img in img_result.scalars().all()}

        ann_result = await db.execute(
            select(Annotation).where(Annotation.image_id.in_(image_ids))
        )
        annotations: dict[str, list[Annotation]] = defaultdict(list)
        for ann in ann_result.scalars().all():
            annotations[ann.image_id].append(ann)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for img_id, img in images.items():
                img_anns = annotations.get(img_id, [])
                if not img_anns:
                    continue

                # Use original_filename for the .txt so YOLO can match by name
                base_name = os.path.splitext(img.original_filename)[0]
                txt_name = f"{base_name}.txt"

                lines = []
                for ann in img_anns:
                    if ann.class_id in class_map:
                        yolo_id = class_map[ann.class_id]
                        cx = (ann.bbox_x + ann.bbox_width / 2) / img.width
                        cy = (ann.bbox_y + ann.bbox_height / 2) / img.height
                        w = ann.bbox_width / img.width
                        h = ann.bbox_height / img.height
                        lines.append(
                            f"{yolo_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"
                        )

                if lines:
                    zf.writestr(txt_name, "\n".join(lines) + "\n")

                # Read and add the actual image file
                img_ext = os.path.splitext(img.original_filename)[1]
                zip_img_name = f"images/{base_name}{img_ext}"
                full_path = os.path.join(settings.UPLOAD_DIR, img.file_path)
                if os.path.exists(full_path):
                    with open(full_path, "rb") as f:
                        zf.writestr(zip_img_name, f.read())

        return zip_buffer.getvalue()


class CRUDAnnotationProject(CRUDBase[AnnotationProject]):
    async def get_multi_paginated(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> tuple[list[AnnotationProject], int]:
        query = select(AnnotationProject)
        count_query = select(func.count(AnnotationProject.id))

        if status:
            query = query.where(AnnotationProject.status == status)
            count_query = count_query.where(AnnotationProject.status == status)
        if assigned_to:
            query = query.where(AnnotationProject.assigned_to == assigned_to)
            count_query = count_query.where(AnnotationProject.assigned_to == assigned_to)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(AnnotationProject.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        projects = list(result.scalars().all())

        return projects, total

    async def add_images(
        self, db: AsyncSession, project_id: str, image_ids: list[str]
    ) -> int:
        existing = await db.execute(
            select(AnnotationProjectImage.image_id).where(
                and_(
                    AnnotationProjectImage.annotation_project_id == project_id,
                    AnnotationProjectImage.image_id.in_(image_ids),
                )
            )
        )
        existing_ids = {r[0] for r in existing.all()}
        to_add = [i for i in image_ids if i not in existing_ids]
        if not to_add:
            return 0

        records = [
            AnnotationProjectImage(
                annotation_project_id=project_id,
                image_id=img_id,
            )
            for img_id in to_add
        ]
        db.add_all(records)

        await db.execute(
            update(AnnotationProject)
            .where(AnnotationProject.id == project_id)
            .values(total_images=AnnotationProject.total_images + len(to_add))
        )
        await db.flush()
        return len(to_add)

    async def remove_images(
        self, db: AsyncSession, project_id: str, image_ids: list[str]
    ) -> int:
        result = await db.execute(
            delete(AnnotationProjectImage).where(
                and_(
                    AnnotationProjectImage.annotation_project_id == project_id,
                    AnnotationProjectImage.image_id.in_(image_ids),
                )
            )
        )
        removed = result.rowcount
        if removed:
            await db.execute(
                update(AnnotationProject)
                .where(AnnotationProject.id == project_id)
                .values(total_images=AnnotationProject.total_images - removed)
            )
        await db.flush()
        return removed

    async def get_project_images(
        self, db: AsyncSession, project_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[AnnotationProjectImage], int]:
        count_result = await db.execute(
            select(func.count(AnnotationProjectImage.id))
            .where(AnnotationProjectImage.annotation_project_id == project_id)
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            select(AnnotationProjectImage)
            .where(AnnotationProjectImage.annotation_project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()
        return list(items), total

    async def get_project_image_ids(
        self, db: AsyncSession, project_id: str
    ) -> list[str]:
        result = await db.execute(
            select(AnnotationProjectImage.image_id)
            .where(AnnotationProjectImage.annotation_project_id == project_id)
        )
        return [r[0] for r in result.all()]


annotation_class_crud = CRUDAnnotationClass(AnnotationClass)
annotation_crud = CRUDAnnotation(Annotation)
annotation_project_crud = CRUDAnnotationProject(AnnotationProject)
