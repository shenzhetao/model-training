"""Inference history API — record and retrieve inference results."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.security import get_current_user
from app.schemas.inference import (
    InferenceResultCreate, InferenceResultResponse,
)
from app.crud.inference import inference_result_crud

router = APIRouter()


@router.get("/", response_model=list[InferenceResultResponse])
async def list_inference_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_type: Optional[str] = Query(None),
    model_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List inference history."""
    skip = (page - 1) * page_size
    results, total = await inference_result_crud.get_multi_paginated(
        db, skip=skip, limit=page_size,
        source_type=source_type, model_id=model_id,
    )
    return results


@router.post("/", response_model=InferenceResultResponse)
async def create_inference_result(
    obj_in: InferenceResultCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record an inference result."""
    data = {
        **obj_in.model_dump(),
        "created_by": current_user.id,
    }
    obj = await inference_result_crud.create(db, data)
    await db.commit()
    return obj


@router.get("/{result_id}", response_model=InferenceResultResponse)
async def get_inference_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific inference result."""
    from fastapi import HTTPException
    obj = await inference_result_crud.get(db, result_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return obj


@router.delete("/{result_id}")
async def delete_inference_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an inference result."""
    from fastapi import HTTPException
    from sqlalchemy import delete
    obj = await inference_result_crud.get(db, result_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    await db.execute(delete(InferenceResult).where(InferenceResult.id == result_id))
    await db.commit()
    return {"success": True}


@router.get("/stats/summary")
async def get_inference_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get inference statistics."""
    return await inference_result_crud.get_stats(db)


from app.models.inference import InferenceResult
