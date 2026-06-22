"""Pydantic schemas for template management."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TemplateClassBase(BaseModel):
    class_name: str
    display_name: str
    description: Optional[str] = None
    default_threshold: float = 0.8
    icon: Optional[str] = None
    sort_order: int = 0


class TemplateClassCreate(TemplateClassBase):
    pass


class TemplateClassUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    default_threshold: Optional[float] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None


class TemplateClassResponse(TemplateClassBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateBase(BaseModel):
    class_name: str
    name: str
    match_threshold: float = 0.8
    roi_x: Optional[int] = None
    roi_y: Optional[int] = None
    roi_width: Optional[int] = None
    roi_height: Optional[int] = None


class TemplateCreate(TemplateBase):
    class_id: Optional[str] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    match_threshold: Optional[float] = None
    roi_x: Optional[int] = None
    roi_y: Optional[int] = None
    roi_width: Optional[int] = None
    roi_height: Optional[int] = None
    is_active: Optional[bool] = None


class TemplateResponse(TemplateBase):
    id: str
    class_id: Optional[str] = None
    file_path: str
    file_size: int
    width: int
    height: int
    is_active: bool
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateTestRequest(BaseModel):
    image_id: Optional[str] = None
    image_url: Optional[str] = None
    template_ids: list[str] = []
    threshold: float = 0.8


class TemplateTestResult(BaseModel):
    template_id: str
    template_name: str
    matched: bool
    x: int
    y: int
    w: int
    h: int
    conf: float


class TemplateTestResponse(BaseModel):
    success: bool
    results: list[TemplateTestResult]
    message: str
