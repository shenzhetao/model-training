"""CRUD operations for TrainingJob and TrainingLog."""
import asyncio
import subprocess
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import TrainingJob, TrainingLog
from app.models.dataset import DatasetVersion
from app.models.model import Model
from app.crud.base import CRUDBase
from app.config import settings


class CRUDTrainingJob(CRUDBase[TrainingJob]):
    async def get_multi_paginated(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        dataset_version_id: Optional[str] = None,
    ) -> tuple[list[TrainingJob], int]:
        query = select(TrainingJob)
        count_q = select(func.count(TrainingJob.id))

        if status:
            query = query.where(TrainingJob.status == status)
            count_q = count_q.where(TrainingJob.status == status)
        if dataset_version_id:
            query = query.where(TrainingJob.dataset_version_id == dataset_version_id)
            count_q = count_q.where(TrainingJob.dataset_version_id == dataset_version_id)

        total_r = await db.execute(count_q)
        total = total_r.scalar() or 0

        query = query.order_by(TrainingJob.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def start_training(
        self, db: AsyncSession, job_id: str
    ) -> bool:
        """Launch training as a background subprocess and update job with process_id."""
        job: TrainingJob = await self.get(db, job_id)
        if not job or job.status not in ("pending", "paused"):
            return False

        await db.execute(
            update(TrainingJob)
            .where(TrainingJob.id == job_id)
            .values(
                status="running",
                started_at=datetime.utcnow(),
                current_epoch=0,
            )
        )
        await db.flush()
        return True


class CRUDTrainingLog(CRUDBase[TrainingLog]):
    async def get_by_job(
        self, db: AsyncSession, job_id: str
    ) -> list[TrainingLog]:
        result = await db.execute(
            select(TrainingLog)
            .where(TrainingLog.training_job_id == job_id)
            .order_by(TrainingLog.epoch)
        )
        return list(result.scalars().all())

    async def get_latest(
        self, db: AsyncSession, job_id: str
    ) -> Optional[TrainingLog]:
        result = await db.execute(
            select(TrainingLog)
            .where(TrainingLog.training_job_id == job_id)
            .order_by(TrainingLog.epoch.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class TrainingHelper:
    """Helper to construct YOLO training command."""

    @staticmethod
    def build_command(job: TrainingJob, dataset_yaml: str, output_dir: str) -> list[str]:
        cmd = [
            "python", "-m", "ultralytics", "train",
            "--model", job.base_model_architecture,
            "--data", dataset_yaml,
            "--epochs", str(job.epochs),
            "--batch", str(job.batch_size),
            "--imgsz", str(job.img_size),
            "--lr0", str(job.lr0),
            "--lrf", str(job.lrf),
            "--weight-decay", str(job.weight_decay),
            "--momentum", str(job.momentum),
            "--patience", str(job.patience),
            "--mosaic", str(job.mosaic),
            "--mixup", str(job.mixup),
            "--hsv-h", str(job.hsv_h),
            "--hsv-s", str(job.hsv_s),
            "--hsv-v", str(job.hsv_v),
            "--degrees", "0.0",
            "--translate", "0.1",
            "--scale", "0.5",
            "--fliplr", str(job.flip_lr),
            "--project", output_dir,
            "--name", job.id,
            "--exist-ok",
            "--device", "0",
        ]
        return cmd


training_job_crud = CRUDTrainingJob(TrainingJob)
training_log_crud = CRUDTrainingLog(TrainingLog)
