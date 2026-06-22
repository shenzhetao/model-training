"""Model management API — upload, list, activate trained YOLO models."""
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.security import get_current_user
from app.schemas.model import ModelCreate, ModelUpdate, ModelResponse, ModelStatsResponse
from app.crud.model import model_crud, _save_model_file

router = APIRouter()

ALLOWED_FORMATS = {".pt", ".pth", ".onnx", ".tflite", ".savedmodel"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


@router.get("/", response_model=list[ModelResponse])
async def list_models(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    architecture: str = Query(None),
    is_active: bool = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all trained models."""
    skip = (page - 1) * page_size
    models, total = await model_crud.get_multi_paginated(
        db, skip=skip, limit=page_size,
        architecture=architecture, is_active=is_active,
    )
    return models


@router.post("/", response_model=ModelResponse)
async def upload_model(
    file: UploadFile = File(...),
    name: str = Query(..., description="Model display name"),
    architecture: str = Query("yolov8n", description="Model architecture"),
    dataset_version_id: str = Query(None),
    class_ids: str = Query("[]", description="JSON array of class IDs"),
    yolo_class_names: str = Query("[]", description="JSON array of class names"),
    description: str = Query(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a trained model file (.pt, .onnx, etc.)."""
    import json

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Format not allowed. Allowed: {', '.join(ALLOWED_FORMATS)}"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 500MB")

    try:
        file_path = _save_model_file(content, file.filename or f"{name}.pt")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save model: {e}")

    try:
        class_ids_list = json.loads(class_ids) if class_ids else []
        class_names_list = json.loads(yolo_class_names) if yolo_class_names else []
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON for class_ids or yolo_class_names")

    data = {
        "name": name,
        "description": description,
        "architecture": architecture,
        "format": ext.lstrip("."),
        "file_path": file_path,
        "file_size": len(content),
        "dataset_version_id": dataset_version_id,
        "class_ids": class_ids_list,
        "yolo_class_names": class_names_list,
        "uploaded_by": current_user.id,
        "is_active": False,
    }
    obj = await model_crud.create(db, data)
    await db.commit()
    return obj


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get model details."""
    m = await model_crud.get(db, model_id)
    if not m or m.is_deleted:
        raise HTTPException(status_code=404, detail="Model not found")
    return m


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: str,
    obj_in: ModelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update model metadata or tags."""
    m = await model_crud.get(db, model_id)
    if not m or m.is_deleted:
        raise HTTPException(status_code=404, detail="Model not found")
    updated = await model_crud.update(db, model_id, obj_in.model_dump(exclude_unset=True))
    await db.commit()
    return updated


@router.delete("/{model_id}")
async def delete_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a model."""
    m = await model_crud.get(db, model_id)
    if not m or m.is_deleted:
        raise HTTPException(status_code=404, detail="Model not found")
    await model_crud.soft_delete(db, model_id)
    await db.commit()
    return {"success": True, "message": "Model deleted"}


@router.post("/{model_id}/activate")
async def activate_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set a model as the active/default model for its architecture."""
    m = await model_crud.get(db, model_id)
    if not m or m.is_deleted:
        raise HTTPException(status_code=404, detail="Model not found")
    await model_crud.set_active(db, model_id)
    await db.commit()
    return {"success": True, "message": f"Model '{m.name}' set as active"}


@router.get("/stats/overview", response_model=ModelStatsResponse)
async def get_model_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get model statistics."""
    from sqlalchemy import select, func

    result = await db.execute(
        select(Model).where(Model.is_deleted == False)
    )
    models = list(result.scalars().all())
    total = len(models)
    active = sum(1 for m in models if m.is_active)
    total_size_mb = sum(m.file_size for m in models) / (1024 * 1024)

    by_arch: dict[str, int] = {}
    for m in models:
        by_arch[m.architecture] = by_arch.get(m.architecture, 0) + 1

    return ModelStatsResponse(
        total_models=total,
        active_models=active,
        total_size_mb=round(total_size_mb, 2),
        by_architecture=by_arch,
    )
