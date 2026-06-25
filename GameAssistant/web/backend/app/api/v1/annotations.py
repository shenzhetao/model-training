"""Annotations API — CRUD for annotations, classes, projects, and YOLO export."""
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.annotation import Annotation, AnnotationProject, AnnotationProjectImage, AnnotationReview
from app.security import get_current_user
from app.schemas.annotation import (
    AnnotationCreate, AnnotationUpdate, AnnotationResponse,
    BatchAnnotationCreate, BatchAnnotationResponse,
    ImageAnnotationsResponse,
    ClassCreate, ClassUpdate, ClassResponse,
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectAddImagesRequest, ProjectStatsResponse,
    YOLOExportRequest, YOLOExportResponse,
)
from app.crud.annotation import (
    annotation_crud, annotation_class_crud, annotation_project_crud,
)
from app.crud.image import image_crud
from app.config import settings

router = APIRouter(redirect_slashes=True)

# ── Class routes ────────────────────────────────────────────

@router.get("/classes", response_model=list[ClassResponse])
async def list_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all annotation classes ordered by sort_order."""
    return await annotation_class_crud.get_all_ordered(db)


@router.post("/classes", response_model=ClassResponse)
async def create_class(
    obj_in: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new annotation class."""
    existing = await annotation_class_crud.get_by_name(db, obj_in.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Class '{obj_in.name}' already exists")
    existing_yolo = await annotation_class_crud.get_by_yolo_id(db, obj_in.yolo_class_id)
    if existing_yolo:
        raise HTTPException(status_code=409, detail=f"YOLO class ID {obj_in.yolo_class_id} already assigned")
    obj = await annotation_class_crud.create(db, obj_in.model_dump())
    await db.commit()
    return obj


@router.put("/classes/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: str,
    obj_in: ClassUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an annotation class."""
    cls = await annotation_class_crud.get(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    updated = await annotation_class_crud.update(db, class_id, obj_in.model_dump(exclude_unset=True))
    await db.commit()
    return updated


@router.delete("/classes/{class_id}")
async def delete_class(
    class_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an annotation class (only if no annotations reference it)."""
    cls = await annotation_class_crud.get(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    await annotation_class_crud.delete(db, class_id)
    await db.commit()
    return {"success": True, "message": "Class deleted"}


# ── Annotation routes ───────────────────────────────────────

@router.get("/images/{image_id}", response_model=ImageAnnotationsResponse)
async def get_image_annotations(
    image_id: str,
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all annotations for a specific image with class names."""
    image = await image_crud.get(db, image_id)
    if not image or image.is_deleted:
        raise HTTPException(status_code=404, detail="Image not found")

    annotations = await annotation_crud.get_by_image(db, image_id, project_id)

    # Get class names
    class_ids = list({ann.class_id for ann in annotations})
    class_map: dict[str, str] = {}
    for cid in class_ids:
        cls = await annotation_class_crud.get(db, cid)
        if cls:
            class_map[cid] = cls.display_name

    response_anns = []
    for ann in annotations:
        response_anns.append(AnnotationResponse.model_validate(ann))

    return ImageAnnotationsResponse(
        image_id=image_id,
        image_width=image.width,
        image_height=image.height,
        annotations=response_anns,
        annotated_count=len(response_anns),
        class_names=[class_map.get(a.class_id, "") for a in annotations],
    )


@router.post("/", response_model=AnnotationResponse)
async def create_annotation(
    obj_in: AnnotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a single bounding-box annotation."""
    image = await image_crud.get(db, obj_in.image_id)
    if not image or image.is_deleted:
        raise HTTPException(status_code=404, detail="Image not found")

    cls = await annotation_class_crud.get(db, obj_in.class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    ann, is_new = await annotation_crud.upsert(
        db, obj_in.model_dump(), annotated_by=current_user.id
    )

    if is_new:
        project = await annotation_project_crud.get(db, obj_in.project_id)
        if project:
            # Update annotated_images count for the specific project
            from app.models.annotation import AnnotationProjectImage
            result = await db.execute(
                select(func.count(func.distinct(Annotation.image_id)))
                .where(Annotation.project_id == obj_in.project_id)
            )
            annotated_count = result.scalar() or 0
            await db.execute(
                update(AnnotationProject)
                .where(AnnotationProject.id == obj_in.project_id)
                .values(annotated_images=annotated_count)
            )

    await db.commit()
    return ann


@router.post("/batch", response_model=BatchAnnotationResponse)
async def batch_create_annotations(
    obj_in: BatchAnnotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update multiple annotations for one image in one request."""
    image = await image_crud.get(db, obj_in.image_id)
    if not image or image.is_deleted:
        raise HTTPException(status_code=404, detail="Image not found")

    created, updated = 0, 0
    for ann_in in obj_in.annotations:
        _, is_new = await annotation_crud.upsert(
            db, {**ann_in.model_dump(), "image_id": obj_in.image_id},
            annotated_by=current_user.id,
        )
        if is_new:
            created += 1
        else:
            updated += 1

    await db.commit()
    return BatchAnnotationResponse(
        success=True,
        message=f"Created {created}, updated {updated}",
        created=created,
        updated=updated,
    )


@router.put("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: str,
    obj_in: AnnotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing annotation's bbox or class."""
    ann = await annotation_crud.get(db, annotation_id)
    if not ann:
        raise HTTPException(status_code=404, detail="Annotation not found")
    updated = await annotation_crud.update(db, annotation_id, obj_in.model_dump(exclude_unset=True))
    await db.commit()
    return updated


@router.delete("/{annotation_id}")
async def delete_annotation(
    annotation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an annotation."""
    ann = await annotation_crud.get(db, annotation_id)
    if not ann:
        raise HTTPException(status_code=404, detail="Annotation not found")
    await annotation_crud.delete(db, annotation_id)
    await db.commit()
    return {"success": True, "message": "Annotation deleted"}


@router.delete("/by-image/{image_id}")
async def delete_image_annotations(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all annotations for an image."""
    count = await annotation_crud.delete_by_image(db, image_id)
    await db.commit()
    return {"success": True, "message": f"Deleted {count} annotations"}


# ── Project routes ──────────────────────────────────────────

@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: draft/in_progress/completed"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List annotation projects with pagination."""
    skip = (page - 1) * page_size
    projects, total = await annotation_project_crud.get_multi_paginated(
        db, skip=skip, limit=page_size, status=status,
    )
    # Return all items (pagination handled client-side via total)
    return projects


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    obj_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new annotation project."""
    obj = await annotation_project_crud.create(db, {
        **obj_in.model_dump(),
        "created_by": current_user.id,
        "status": "draft",
    })
    await db.commit()
    return obj


@router.get("/projects/review-queue")
async def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all projects pending review (for reviewers)."""
    skip = (page - 1) * page_size
    from sqlalchemy import select, func
    query = select(AnnotationProject).where(
        AnnotationProject.status.in_(["in_review", "rejected"])
    ).order_by(AnnotationProject.created_at.desc()).offset(skip).limit(page_size)
    result = await db.execute(query)
    projects = list(result.scalars().all())

    count_q = select(func.count(AnnotationProject.id)).where(
        AnnotationProject.status.in_(["in_review", "rejected"])
    )
    total_r = await db.execute(count_q)
    total = total_r.scalar() or 0

    return {"items": projects, "total": total}


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a project by ID."""
    project = await annotation_project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/images")
async def get_project_images(
    project_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(500, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get images in a project."""
    project = await annotation_project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    skip = (page - 1) * page_size
    images, total = await annotation_project_crud.get_project_images(db, project_id, skip, page_size)
    return {
        "items": [{"image_id": img.image_id, "added_at": img.assigned_at.isoformat() if img.assigned_at else None} for img in images],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    obj_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a project."""
    project = await annotation_project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = obj_in.model_dump(exclude_unset=True)
    if obj_in.status == "completed" and project.status != "completed":
        update_data["completed_at"] = datetime.utcnow()

    updated = await annotation_project_crud.update(db, project_id, update_data)
    await db.commit()
    return updated


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a project."""
    project = await annotation_project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await annotation_project_crud.delete(db, project_id)
    await db.commit()
    return {"success": True, "message": "Project deleted"}


@router.post("/projects/{project_id}/images")
async def add_project_images(
    project_id: str,
    req: ProjectAddImagesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add images to an annotation project."""
    project = await annotation_project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    added = await annotation_project_crud.add_images(db, project_id, req.image_ids)
    await db.commit()
    return {"success": True, "added": added}


@router.delete("/projects/{project_id}/images")
async def remove_project_images(
    project_id: str,
    image_ids: str = Query(..., description="Comma-separated image IDs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove images from an annotation project."""
    ids = [i.strip() for i in image_ids.split(",") if i.strip()]
    removed = await annotation_project_crud.remove_images(db, project_id, ids)
    await db.commit()
    return {"success": True, "removed": removed}


# ── YOLO Export ────────────────────────────────────────────

@router.get("/export/yolo")
async def export_yolo_get(
    project_id: Optional[str] = None,
    image_ids: Optional[str] = None,
    image_source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export annotations as a YOLO-format ZIP (GET version for browser download)."""
    ids = image_ids.split(",") if image_ids else None
    req = YOLOExportRequest(
        project_id=project_id,
        image_ids=ids,
        image_source=image_source,
    )
    return await _do_export_yolo(req, db)


async def _do_export_yolo(
    req: YOLOExportRequest,
    db: AsyncSession,
) -> StreamingResponse:
    """Internal function to perform YOLO export."""
    from app.config import settings

    if req.project_id:
        image_ids = await annotation_project_crud.get_project_image_ids(db, req.project_id)
    elif req.image_ids:
        image_ids = req.image_ids
    elif req.image_source:
        from sqlalchemy import select
        query = select(Image.id).where(Image.is_deleted == False)
        if req.image_source != "all":
            query = query.where(Image.source == req.image_source)
        result = await db.execute(query)
        image_ids = [row[0] for row in result.fetchall()]
    else:
        from sqlalchemy import select
        query = select(Image.id).where(Image.is_deleted == False)
        result = await db.execute(query)
        image_ids = [row[0] for row in result.fetchall()]

    zip_bytes = await annotation_crud.export_yolo_zip(db, image_ids)

    filename = f"yolo_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"

    async def iter_zip():
        yield zip_bytes

    return StreamingResponse(
        iter_zip(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Total-Images": str(len(image_ids)),
        },
    )


@router.post("/export/yolo")
async def export_yolo_post(
    req: YOLOExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export annotations as a YOLO-format ZIP (images + txt files)."""
    return await _do_export_yolo(req, db)


@router.get("/stats", response_model=ProjectStatsResponse)
async def get_annotation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get annotation statistics."""
    from sqlalchemy import select, func

    projects, _ = await annotation_project_crud.get_multi_paginated(db, limit=10000)
    draft = sum(1 for p in projects if p.status == "draft")
    in_progress = sum(1 for p in projects if p.status == "in_progress")
    completed = sum(1 for p in projects if p.status == "completed")
    reviewed = sum(1 for p in projects if p.status == "reviewed")

    ann_result = await db.execute(select(func.count(Annotation.id)))
    total_anns = ann_result.scalar() or 0

    auto_result = await db.execute(
        select(func.count(Annotation.id)).where(Annotation.is_auto_annotated == True)
    )
    auto_anns = auto_result.scalar() or 0

    return ProjectStatsResponse(
        total_projects=len(projects),
        draft=draft,
        in_progress=in_progress,
        completed=completed,
        reviewed=reviewed,
        total_annotations=total_anns,
        auto_annotations=auto_anns,
        manual_annotations=total_anns - auto_anns,
    )


@router.post("/projects/{project_id}/submit-review")
async def submit_for_review(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a project for review (annotator marks it done, sends to reviewer)."""
    project = await annotation_project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # All statuses are allowed so that the annotator can re-submit after fixes
    # (e.g., a project that was approved, rejected, or even previously completed
    # and needs more annotations). Status is forced to in_review here.
    update_data: dict = {"status": "in_review"}
    # Clear stale review feedback when re-submitting so the reviewer sees a clean slate
    if project.status in ("rejected", "completed"):
        update_data["review_feedback"] = ""
    updated = await annotation_project_crud.update(db, project_id, update_data)
    await db.commit()
    return updated


@router.post("/projects/{project_id}/images/{image_id}/review")
async def review_project_image(
    project_id: str,
    image_id: str,
    req: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Review a single image in a project (approve or request_changes)."""
    project = await annotation_project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in ("in_review", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot review project in status '{project.status}'")

    action = req.get("action", "approve")
    reason = req.get("reason", "")
    if action not in ("approve", "request_changes"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'request_changes'")

    # Verify image is in this project
    image_in = (await db.execute(
        select(AnnotationProjectImage)
        .where(
            and_(
                AnnotationProjectImage.annotation_project_id == project_id,
                AnnotationProjectImage.image_id == image_id,
            )
        )
    )).scalar_one_or_none()
    if not image_in:
        raise HTTPException(status_code=404, detail="Image not in this project")

    # Upsert review record
    existing = (await db.execute(
        select(AnnotationReview)
        .where(
            and_(
                AnnotationReview.annotation_project_id == project_id,
                AnnotationReview.image_id == image_id,
            )
        )
    )).scalar_one_or_none()

    if existing:
        existing.review_status = action
        existing.rejection_reason = reason if action == "request_changes" else ""
        existing.reviewer_id = current_user.id
        existing.reviewed_at = datetime.utcnow()
    else:
        db.add(AnnotationReview(
            annotation_project_id=project_id,
            image_id=image_id,
            review_status=action,
            reviewer_id=current_user.id,
            rejection_reason=reason if action == "request_changes" else "",
        ))

    # Recompute reviewed_images and possibly auto-complete the project
    await _recompute_project_review_status(db, project_id)
    await db.commit()
    return {"success": True, "action": action}


@router.get("/projects/{project_id}/image-reviews")
async def get_project_image_reviews(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get per-image review statuses for a project."""
    project = await annotation_project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    reviews_result = await db.execute(
        select(AnnotationReview).where(AnnotationReview.annotation_project_id == project_id)
    )
    reviews = {r.image_id: {
        "review_status": r.review_status,
        "rejection_reason": r.rejection_reason,
        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        "reviewer_id": r.reviewer_id,
    } for r in reviews_result.scalars().all()}

    return {"reviews": reviews}


async def _recompute_project_review_status(db: AsyncSession, project_id: str) -> None:
    """Recompute reviewed_images count and auto-complete project if all images approved."""
    from app.models.annotation import AnnotationProjectImage, AnnotationReview
    # Count images in the project
    total_result = await db.execute(
        select(func.count(AnnotationProjectImage.id))
        .where(AnnotationProjectImage.annotation_project_id == project_id)
    )
    total_images = total_result.scalar() or 0

    # Count approved reviews
    approved_result = await db.execute(
        select(func.count(AnnotationReview.id))
        .where(
            and_(
                AnnotationReview.annotation_project_id == project_id,
                AnnotationReview.review_status == "approve",
            )
        )
    )
    approved_count = approved_result.scalar() or 0

    # Count request_changes reviews
    rejected_result = await db.execute(
        select(func.count(AnnotationReview.id))
        .where(
            and_(
                AnnotationReview.annotation_project_id == project_id,
                AnnotationReview.review_status == "request_changes",
            )
        )
    )
    rejected_count = rejected_result.scalar() or 0

    reviewed_count = approved_count + rejected_count

    update_data = {"reviewed_images": reviewed_count}

    # Auto-complete only when: project is in_review AND every project image is approved
    project = await annotation_project_crud.get(db, project_id)
    if (
        project
        and project.status in ("in_review", "rejected")
        and total_images > 0
        and approved_count == total_images
    ):
        update_data["status"] = "completed"
        update_data["completed_at"] = datetime.utcnow()

    await db.execute(
        update(AnnotationProject)
        .where(AnnotationProject.id == project_id)
        .values(**update_data)
    )
    await db.flush()



@router.post("/projects/{project_id}/bulk-approve")
async def bulk_approve_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve all images in a project and complete the project."""
    project = await annotation_project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in ("in_review", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot approve project in status '{project.status}'")

    image_ids = (await db.execute(
        select(AnnotationProjectImage.image_id)
        .where(AnnotationProjectImage.annotation_project_id == project_id)
    )).scalars().all()

    if not image_ids:
        raise HTTPException(status_code=400, detail="Project has no images to approve")

    existing = (await db.execute(
        select(AnnotationReview).where(AnnotationReview.annotation_project_id == project_id)
    )).scalars().all()
    existing_by_image = {r.image_id: r for r in existing}

    for image_id in image_ids:
        if image_id in existing_by_image:
            rec = existing_by_image[image_id]
            rec.review_status = "approve"
            rec.rejection_reason = ""
            rec.reviewer_id = current_user.id
            rec.reviewed_at = datetime.utcnow()
        else:
            db.add(AnnotationReview(
                annotation_project_id=project_id,
                image_id=image_id,
                review_status="approve",
                reviewer_id=current_user.id,
            ))

    await _recompute_project_review_status(db, project_id)
    await db.commit()
    return {"success": True, "approved_count": len(image_ids), "status": "completed"}


@router.post("/projects/{project_id}/bulk-reject")
async def bulk_reject_project(
    project_id: str,
    req: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject all images in a project and return it to the annotator."""
    project = await annotation_project_crud.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in ("in_review", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot reject project in status '{project.status}'")

    reason = (req or {}).get("reason", "一键退回")

    image_ids = (await db.execute(
        select(AnnotationProjectImage.image_id)
        .where(AnnotationProjectImage.annotation_project_id == project_id)
    )).scalars().all()

    if not image_ids:
        raise HTTPException(status_code=400, detail="Project has no images to reject")

    existing = (await db.execute(
        select(AnnotationReview).where(AnnotationReview.annotation_project_id == project_id)
    )).scalars().all()
    existing_by_image = {r.image_id: r for r in existing}

    for image_id in image_ids:
        if image_id in existing_by_image:
            rec = existing_by_image[image_id]
            rec.review_status = "request_changes"
            rec.rejection_reason = reason
            rec.reviewer_id = current_user.id
            rec.reviewed_at = datetime.utcnow()
        else:
            db.add(AnnotationReview(
                annotation_project_id=project_id,
                image_id=image_id,
                review_status="request_changes",
                rejection_reason=reason,
                reviewer_id=current_user.id,
            ))

    # Mark project as rejected
    await db.execute(
        update(AnnotationProject)
        .where(AnnotationProject.id == project_id)
        .values(
            status="rejected",
            review_feedback=reason,
            reviewed_images=len(image_ids),
        )
    )
    await db.commit()
    return {"success": True, "rejected_count": len(image_ids), "status": "rejected"}


@router.post("/annotations/{annotation_id}/review")
async def review_annotation(
    annotation_id: str,
    req: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Review a single annotation (approve or request changes)."""
    ann = await annotation_crud.get(db, annotation_id)
    if not ann:
        raise HTTPException(status_code=404, detail="Annotation not found")
    action = req.get("action", "approve")
    comment = req.get("comment", "")
    if action not in ("approve", "request_changes"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'request_changes'")
    updated = await annotation_crud.update(db, annotation_id, {
        "review_status": action,
        "review_comment": comment,
        "reviewed_by": current_user.id,
        "reviewed_at": datetime.utcnow(),
    })
    await db.commit()
    return updated


@router.get("/stats/review-summary")
async def get_review_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get review statistics."""
    from sqlalchemy import select, func

    total_r = await db.execute(select(func.count(AnnotationProject.id)))
    total = total_r.scalar() or 0

    counts: dict[str, int] = {}
    for status in ["draft", "in_progress", "in_review", "rejected", "completed"]:
        r = await db.execute(
            select(func.count(AnnotationProject.id)).where(AnnotationProject.status == status)
        )
        counts[status] = r.scalar() or 0

    return {
        "total_projects": total,
        "pending_review": counts.get("in_review", 0),
        "needs_revision": counts.get("rejected", 0),
        "completed": counts.get("completed", 0),
        "in_progress": counts.get("in_progress", 0),
    }


# Import Image model at module level for the export route
from app.models.image import Image
