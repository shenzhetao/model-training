"""Dataset management API — create datasets, manage versions, generate YOLO format."""
import json
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.security import get_current_user
from app.schemas.dataset import (
    DatasetCreate, DatasetUpdate, DatasetResponse,
    DatasetVersionCreate, DatasetVersionUpdate, DatasetVersionResponse,
    DatasetAddImagesRequest, DatasetVersionStatsResponse,
)
from app.crud.dataset import dataset_crud, dataset_version_crud
from app.crud.image import image_crud
from app.config import settings

router = APIRouter()


# ── Dataset routes ─────────────────────────────────────────

@router.get("/", response_model=list[DatasetResponse])
async def list_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all datasets."""
    skip = (page - 1) * page_size
    datasets, total = await dataset_crud.get_multi_paginated(db, skip=skip, limit=page_size)
    return datasets


@router.post("/", response_model=DatasetResponse)
async def create_dataset(
    obj_in: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new dataset."""
    obj = await dataset_crud.create(db, {
        **obj_in.model_dump(),
        "created_by": current_user.id,
    })
    await db.commit()
    return obj


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dataset details."""
    ds = await dataset_crud.get(db, dataset_id)
    if not ds or ds.is_deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: str,
    obj_in: DatasetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a dataset."""
    ds = await dataset_crud.get(db, dataset_id)
    if not ds or ds.is_deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    updated = await dataset_crud.update(db, dataset_id, obj_in.model_dump(exclude_unset=True))
    await db.commit()
    return updated


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a dataset."""
    ds = await dataset_crud.get(db, dataset_id)
    if not ds or ds.is_deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await dataset_crud.soft_delete(db, dataset_id)
    await db.commit()
    return {"success": True, "message": "Dataset deleted"}


# ── Dataset Version routes ─────────────────────────────────

@router.get("/{dataset_id}/versions", response_model=list[DatasetVersionResponse])
async def list_dataset_versions(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all versions for a dataset."""
    ds = await dataset_crud.get(db, dataset_id)
    if not ds or ds.is_deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return await dataset_version_crud.get_multi_by_dataset(db, dataset_id)


@router.post("/{dataset_id}/versions", response_model=DatasetVersionResponse)
async def create_dataset_version(
    dataset_id: str,
    obj_in: DatasetVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new version for a dataset."""
    ds = await dataset_crud.get(db, dataset_id)
    if not ds or ds.is_deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")

    next_vn = await dataset_version_crud.get_next_version_number(db, dataset_id)
    version = await dataset_version_crud.create(db, {
        **obj_in.model_dump(),
        "dataset_id": dataset_id,
        "version_number": next_vn,
        "created_by": current_user.id,
        "status": "ready",
    })
    await db.commit()
    return version


@router.get("/{dataset_id}/versions/{version_id}", response_model=DatasetVersionResponse)
async def get_dataset_version(
    dataset_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dataset version details."""
    version = await dataset_version_crud.get(db, version_id)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.put("/{dataset_id}/versions/{version_id}", response_model=DatasetVersionResponse)
async def update_dataset_version(
    dataset_id: str,
    version_id: str,
    obj_in: DatasetVersionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a dataset version."""
    version = await dataset_version_crud.get(db, version_id)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")
    updated = await dataset_version_crud.update(db, version_id, obj_in.model_dump(exclude_unset=True))
    await db.commit()
    return updated


# ── Version image management ───────────────────────────────

@router.post("/{dataset_id}/versions/{version_id}/images")
async def add_images_to_version(
    dataset_id: str,
    version_id: str,
    req: DatasetAddImagesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add images to a dataset version."""
    version = await dataset_version_crud.get(db, version_id)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")

    if req.split not in ("train", "val", "test"):
        raise HTTPException(status_code=400, detail="split must be train/val/test")

    added = await dataset_version_crud.add_images(db, version_id, req.image_ids, req.split)
    await db.commit()
    return {"success": True, "added": added}


@router.get("/{dataset_id}/versions/{version_id}/stats", response_model=DatasetVersionStatsResponse)
async def get_version_stats(
    dataset_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get image split stats for a dataset version."""
    version = await dataset_version_crud.get(db, version_id)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")

    stats = await dataset_version_crud.get_version_stats(db, version_id)
    return DatasetVersionStatsResponse(**stats)


# ── YOLO generation ───────────────────────────────────────

@router.post("/{dataset_id}/versions/{version_id}/generate-yolo")
async def generate_yolo_dataset(
    dataset_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate YOLO-format dataset ZIP for a version."""
    version = await dataset_version_crud.get(db, version_id)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")

    try:
        zip_path = await dataset_version_crud.generate_yolo_dataset(db, version_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate dataset: {e}")

    filename = os.path.basename(zip_path)

    def iterfile():
        with open(zip_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Version-Number": str(version.version_number),
            "X-Image-Count": str(version.image_count),
        },
    )


# ── Data Augmentation Config ───────────────────────────────

@router.post("/{dataset_id}/versions/{version_id}/augmentation")
async def save_augmentation_config(
    dataset_id: str,
    version_id: str,
    req: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save data augmentation configuration for a dataset version."""
    version = await dataset_version_crud.get(db, version_id)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")

    # Store augmentation config in the version's yaml_content or a dedicated field
    from sqlalchemy import update
    await db.execute(
        update(DatasetVersion)
        .where(DatasetVersion.id == version_id)
        .values(dataset_yaml_content=json.dumps(req))
    )
    await db.commit()
    return {"success": True, "message": "Augmentation config saved"}
