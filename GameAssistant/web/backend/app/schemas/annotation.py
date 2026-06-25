"""Pydantic schemas for annotations and related entities."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Class schemas ───────────────────────────────────────────

class ClassBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    color: str = "#3B82F6"
    short_key: Optional[str] = None
    sort_order: int = 0
    yolo_class_id: int


class ClassCreate(ClassBase):
    pass


class ClassUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    short_key: Optional[str] = None
    sort_order: Optional[int] = None


class ClassResponse(ClassBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Annotation schemas ─────────────────────────────────────

class AnnotationBase(BaseModel):
    image_id: str
    project_id: str
    class_id: str
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    conf: Optional[float] = None
    is_auto_annotated: bool = False


class AnnotationCreate(AnnotationBase):
    annotated_by: Optional[str] = None


class AnnotationUpdate(BaseModel):
    class_id: Optional[str] = None
    bbox_x: Optional[float] = None
    bbox_y: Optional[float] = None
    bbox_width: Optional[float] = None
    bbox_height: Optional[float] = None


class AnnotationResponse(AnnotationBase):
    id: str
    annotated_by: Optional[str] = None
    annotated_at: datetime
    updated_at: datetime
    review_status: Optional[str] = None
    review_comment: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ImageAnnotationsResponse(BaseModel):
    image_id: str
    image_width: int
    image_height: int
    annotations: list[AnnotationResponse]
    annotated_count: int = 0
    class_names: list[str] = []


# ── Batch annotation schemas ────────────────────────────────

class BatchAnnotationCreate(BaseModel):
    image_id: str
    annotations: list[AnnotationCreate]


class BatchAnnotationResponse(BaseModel):
    success: bool
    message: str
    created: int = 0
    updated: int = 0


# ── YOLO export schemas ───────────────────────────────────

class YOLOExportRequest(BaseModel):
    project_id: Optional[str] = None
    image_ids: Optional[list[str]] = None
    image_source: Optional[str] = Field(None, description="'all' | 'upload' | 'adb' | 'video'")


class YOLOExportResponse(BaseModel):
    success: bool
    message: str
    total_images: int
    total_annotations: int
    zip_path: Optional[str] = None


# ── Annotation project schemas ─────────────────────────────

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    class_ids: list[str] = []
    assigned_to: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    class_ids: Optional[list[str]] = None
    assigned_to: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: str
    status: str
    total_images: int
    annotated_images: int
    reviewed_images: int
    reviewed_by: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    review_feedback: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectAddImagesRequest(BaseModel):
    image_ids: list[str]


class ProjectStatsResponse(BaseModel):
    total_projects: int
    draft: int
    in_progress: int
    completed: int
    reviewed: int
    total_annotations: int
    auto_annotations: int
    manual_annotations: int
