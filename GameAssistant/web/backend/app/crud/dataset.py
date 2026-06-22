"""CRUD operations for Dataset and DatasetVersion."""
import io
import os
import random
import zipfile
from typing import Optional

from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset, DatasetVersion, DatasetVersionImage
from app.models.annotation import Annotation, AnnotationClass
from app.models.image import Image
from app.crud.base import CRUDBase
from app.config import settings


class CRUDDataset(CRUDBase[Dataset]):
    async def get_multi_paginated(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Dataset], int]:
        query = select(Dataset).where(Dataset.is_deleted == False)
        count_q = select(func.count(Dataset.id)).where(Dataset.is_deleted == False)

        total_r = await db.execute(count_q)
        total = total_r.scalar() or 0

        query = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def soft_delete(self, db: AsyncSession, id: str) -> bool:
        await db.execute(update(Dataset).where(Dataset.id == id).values(is_deleted=True))
        await db.flush()
        return True


class CRUDDatasetVersion(CRUDBase[DatasetVersion]):
    async def get_multi_by_dataset(
        self, db: AsyncSession, dataset_id: str
    ) -> list[DatasetVersion]:
        result = await db.execute(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_next_version_number(
        self, db: AsyncSession, dataset_id: str
    ) -> int:
        result = await db.execute(
            select(func.max(DatasetVersion.version_number))
            .where(DatasetVersion.dataset_id == dataset_id)
        )
        max_v = result.scalar()
        return (max_v or 0) + 1

    async def get_version_stats(
        self, db: AsyncSession, version_id: str
    ) -> dict:
        result = await db.execute(
            select(DatasetVersionImage).where(
                DatasetVersionImage.dataset_version_id == version_id
            )
        )
        images = list(result.scalars().all())
        total = len(images)
        train = sum(1 for i in images if i.split == "train")
        val = sum(1 for i in images if i.split == "val")
        test = sum(1 for i in images if i.split == "test")

        image_ids = [i.image_id for i in images]
        annotated = 0
        if image_ids:
            ann_r = await db.execute(
                select(func.count(Annotation.id))
                .where(Annotation.image_id.in_(image_ids))
            )
            annotated = ann_r.scalar() or 0

        return dict(total=total, train=train, val=val, test=test,
                     annotated=annotated, unannotated=total - annotated)

    async def add_images(
        self,
        db: AsyncSession,
        version_id: str,
        image_ids: list[str],
        split: str = "train",
    ) -> int:
        existing = await db.execute(
            select(DatasetVersionImage.image_id).where(
                and_(
                    DatasetVersionImage.dataset_version_id == version_id,
                    DatasetVersionImage.image_id.in_(image_ids),
                )
            )
        )
        existing_ids = {r[0] for r in existing.all()}
        to_add = [i for i in image_ids if i not in existing_ids]
        if not to_add:
            return 0

        records = [
            DatasetVersionImage(
                dataset_version_id=version_id,
                image_id=img_id,
                split=split,
            )
            for img_id in to_add
        ]
        db.add_all(records)

        await db.execute(
            update(DatasetVersion)
            .where(DatasetVersion.id == version_id)
            .values(image_count=DatasetVersion.image_count + len(to_add))
        )
        await db.flush()
        return len(to_add)

    async def generate_yolo_dataset(
        self, db: AsyncSession, version_id: str
    ) -> str:
        """Generate YOLO-format dataset and return path to ZIP."""
        version: DatasetVersion = await self.get(db, version_id)
        if not version:
            raise ValueError("Version not found")

        image_ids_result = await db.execute(
            select(DatasetVersionImage.image_id, DatasetVersionImage.split)
            .where(DatasetVersionImage.dataset_version_id == version_id)
        )
        image_splits: list[tuple] = list(image_ids_result.all())

        if not image_splits:
            raise ValueError("No images in version")

        images_result = await db.execute(
            select(Image).where(Image.id.in_([i[0] for i in image_splits]))
        )
        images: dict[str, Image] = {img.id: img for img in images_result.scalars().all()}

        ann_result = await db.execute(
            select(Annotation).where(
                Annotation.image_id.in_([i[0] for i in image_splits])
            )
        )
        annotations: dict[str, list[Annotation]] = {}
        for ann in ann_result.scalars().all():
            annotations.setdefault(ann.image_id, []).append(ann)

        class_ids: list = version.class_ids or []
        class_map: dict[str, int] = {}
        for cid in class_ids:
            cls_r = await db.execute(
                select(AnnotationClass).where(AnnotationClass.id == cid)
            )
            cls = cls_r.scalar_one_or_none()
            if cls:
                class_map[cls.id] = cls.yolo_class_id

        zip_buf = io.BytesIO()
        splits = {"train": [], "val": [], "test": []}
        for img_id, split in image_splits:
            if split not in splits:
                continue
            img = images.get(img_id)
            if not img:
                continue

            img_anns = annotations.get(img_id, [])
            txt_name = img.filename.rsplit(".", 1)[0] + ".txt"
            if img_anns:
                lines = []
                for ann in img_anns:
                    if ann.class_id in class_map:
                        yolo_id = class_map[ann.class_id]
                        cx = (ann.bbox_x + ann.bbox_width / 2) / img.width
                        cy = (ann.bbox_y + ann.bbox_height / 2) / img.height
                        w = ann.bbox_width / img.width
                        h = ann.bbox_height / img.height
                        lines.append(f"{yolo_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                splits[split].append((img, txt_name, "\n".join(lines) + "\n" if lines else ""))

        os.makedirs(settings.MODEL_DIR, exist_ok=True)
        zip_path = os.path.join(settings.MODEL_DIR, f"dataset_v{version.version_number}_{version.id}.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for split_name in ["train", "val", "test"]:
                if not splits[split_name]:
                    continue
                for img, txt_name, label_content in splits[split_name]:
                    img_full = os.path.join(settings.UPLOAD_DIR, img.file_path)
                    if os.path.exists(img_full):
                        zf.write(img_full, f"{split_name}/images/{img.filename}")
                    if label_content:
                        zf.writestr(f"{split_name}/labels/{txt_name}", label_content)

            names_content = "\n".join(
                f"  - class_{i}" for i in range(len(class_map))
            )
            yaml_content = f"""path: .
train: train/images
val: val/images
test: test/images
names:
{names_content}
"""
            zf.writestr("dataset.yaml", yaml_content)

        await db.execute(
            update(DatasetVersion)
            .where(DatasetVersion.id == version_id)
            .values(
                status="ready",
                yolo_dataset_path=zip_path,
                dataset_yaml_content=yaml_content,
            )
        )
        await db.flush()
        return zip_path


dataset_crud = CRUDDataset(Dataset)
dataset_version_crud = CRUDDatasetVersion(DatasetVersion)
