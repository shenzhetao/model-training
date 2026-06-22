"""CRUD for inference results."""
from typing import Optional

from sqlalchemy import select, update, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inference import InferenceResult
from app.crud.base import CRUDBase


class CRUDInferenceResult(CRUDBase[InferenceResult]):
    async def get_multi_paginated(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        source_type: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> tuple[list[InferenceResult], int]:
        query = select(InferenceResult)
        count_q = select(func.count(InferenceResult.id))

        if source_type:
            query = query.where(InferenceResult.source_type == source_type)
            count_q = count_q.where(InferenceResult.source_type == source_type)
        if model_id:
            query = query.where(InferenceResult.model_id == model_id)
            count_q = count_q.where(InferenceResult.model_id == model_id)

        total_r = await db.execute(count_q)
        total = total_r.scalar() or 0

        query = query.order_by(InferenceResult.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def get_stats(self, db: AsyncSession) -> dict:
        total_r = await db.execute(select(func.count(InferenceResult.id)))
        total = total_r.scalar() or 0

        device_r = await db.execute(
            select(func.count(InferenceResult.id))
            .where(InferenceResult.source_type == "device")
        )
        device = device_r.scalar() or 0

        image_r = await db.execute(
            select(func.count(InferenceResult.id))
            .where(InferenceResult.source_type == "image")
        )
        image = image_r.scalar() or 0

        video_r = await db.execute(
            select(func.count(InferenceResult.id))
            .where(InferenceResult.source_type == "video")
        )
        video = video_r.scalar() or 0

        return {"total": total, "device": device, "image": image, "video": video}


inference_result_crud = CRUDInferenceResult(InferenceResult)
