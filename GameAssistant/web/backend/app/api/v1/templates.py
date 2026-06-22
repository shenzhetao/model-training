"""Template management API — upload, list, test template matching."""
import os
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.security import get_current_user
from app.schemas.template import (
    TemplateClassCreate, TemplateClassUpdate, TemplateClassResponse,
    TemplateCreate, TemplateUpdate, TemplateResponse,
    TemplateTestRequest, TemplateTestResponse, TemplateTestResult,
)
from app.crud.template import template_crud, template_class_crud, TemplateUploadHelper
from app.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ── Template Class routes ────────────────────────────────────

@router.get("/classes", response_model=list[TemplateClassResponse])
async def list_template_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all template classes ordered by sort_order."""
    return await template_class_crud.get_all_ordered(db)


@router.post("/classes", response_model=TemplateClassResponse)
async def create_template_class(
    obj_in: TemplateClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new template class."""
    existing = await template_class_crud.get_multi(db, name=obj_in.class_name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Class '{obj_in.class_name}' already exists")
    obj = await template_class_crud.create(db, obj_in.model_dump())
    await db.commit()
    return obj


@router.put("/classes/{class_id}", response_model=TemplateClassResponse)
async def update_template_class(
    class_id: str,
    obj_in: TemplateClassUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a template class."""
    cls = await template_class_crud.get(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    updated = await template_class_crud.update(db, class_id, obj_in.model_dump(exclude_unset=True))
    await db.commit()
    return updated


@router.delete("/classes/{class_id}")
async def delete_template_class(
    class_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a template class (only if no templates reference it)."""
    cls = await template_class_crud.get(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    await template_class_crud.delete(db, class_id)
    await db.commit()
    return {"success": True, "message": "Class deleted"}


# ── Template routes ─────────────────────────────────────────

@router.get("/", response_model=list[TemplateResponse])
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    class_name: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List templates with optional class filter."""
    skip = (page - 1) * page_size
    templates, total = await template_crud.get_multi_paginated(
        db, skip=skip, limit=page_size, class_name=class_name, is_active=is_active,
    )
    return templates


@router.post("/", response_model=TemplateResponse)
async def upload_template(
    file: UploadFile = File(...),
    class_name: str = Query(..., description="Template class name, e.g. btn_attack"),
    name: str = Query(..., description="Template display name"),
    class_id: Optional[str] = Query(None),
    match_threshold: float = Query(0.8, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a template image (PNG/JPG) for template matching."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB")

    try:
        file_path, width, height = TemplateUploadHelper.save_template_file(
            content, class_name, file.filename or f"{name}.png"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save template: {e}")

    data = {
        "class_id": class_id,
        "class_name": class_name,
        "name": name,
        "file_path": file_path,
        "file_size": len(content),
        "width": width,
        "height": height,
        "match_threshold": match_threshold,
        "uploaded_by": current_user.id,
    }
    obj = await template_crud.create(db, data)
    await db.commit()
    return obj


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get template details."""
    t = await template_crud.get(db, template_id)
    if not t or t.is_deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    obj_in: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update template metadata."""
    t = await template_crud.get(db, template_id)
    if not t or t.is_deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    updated = await template_crud.update(db, template_id, obj_in.model_dump(exclude_unset=True))
    await db.commit()
    return updated


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a template."""
    t = await template_crud.get(db, template_id)
    if not t or t.is_deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    await template_crud.soft_delete(db, template_id)
    await db.commit()
    return {"success": True, "message": "Template deleted"}


@router.get("/{template_id}/serve")
async def serve_template_image(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream template image file."""
    t = await template_crud.get(db, template_id)
    if not t or t.is_deleted:
        raise HTTPException(status_code=404, detail="Template not found")

    full_path = os.path.join(settings.TEMPLATE_DIR, t.file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Template file not found")

    ext = os.path.splitext(t.file_path)[1].lower()
    content_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".bmp": "image/bmp", ".webp": "image/webp",
    }

    def iterfile():
        with open(full_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type=content_types.get(ext, "application/octet-stream"),
        headers={"Content-Disposition": f'inline; filename="{t.name}"'},
    )


# ── Template Matching Test ──────────────────────────────────

@router.post("/test", response_model=TemplateTestResponse)
async def test_template_matching(
    req: TemplateTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test template matching on an image using specified templates."""
    import cv2
    import numpy as np

    results: list[TemplateTestResult] = []
    screen: Optional[np.ndarray] = None

    if req.image_id:
        from app.crud.image import image_crud
        img = await image_crud.get(db, req.image_id)
        if not img or img.is_deleted:
            raise HTTPException(status_code=404, detail="Image not found")
        full = os.path.join(settings.UPLOAD_DIR, img.file_path)
        screen = cv2.imread(full)
    elif req.image_url:
        import urllib.request
        arr = np.asarray(bytearray(urllib.request.urlopen(req.image_url, timeout=10).read()), dtype=np.uint8)
        screen = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if screen is None:
        raise HTTPException(status_code=400, detail="Could not load image")

    templates_to_test = req.template_ids or []
    if templates_to_test:
        templates = [await template_crud.get(db, tid) for tid in templates_to_test]
    else:
        # Use all active templates if none specified
        all_templates, _ = await template_crud.get_multi_paginated(db, limit=500, is_active=True)
        templates = all_templates

    for t in templates:
        if not t or t.is_deleted or not t.is_active:
            continue

        full_path = os.path.join(settings.TEMPLATE_DIR, t.file_path)
        if not os.path.exists(full_path):
            continue

        tmpl = cv2.imread(full_path)
        if tmpl is None:
            continue

        if tmpl.shape[0] > screen.shape[0] or tmpl.shape[1] > screen.shape[1]:
            continue

        res = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= (req.threshold or t.match_threshold):
            h, w = tmpl.shape[:2]
            results.append(TemplateTestResult(
                template_id=t.id,
                template_name=t.name,
                matched=True,
                x=int(max_loc[0]),
                y=int(max_loc[1]),
                w=int(w),
                h=int(h),
                conf=float(max_val),
            ))

    return TemplateTestResponse(
        success=True,
        results=results,
        message=f"Tested {len(templates)} templates, {len(results)} matched",
    )
