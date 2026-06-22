"""Pydantic schemas for model management."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ModelBase(BaseModel):
    name: str
    description: Optional[str] = None
    architecture: str = "yolov8n"
    task_type: str = "detect"


class ModelCreate(ModelBase):
    dataset_version_id: Optional[str] = None
    class_ids: list[str] = []
    yolo_class_names: list[str] = []
    epochs: Optional[int] = None
    batch_size: Optional[int] = None
    img_size: Optional[int] = None
    map50: Optional[float] = None
    map50_95: Optional[float] = None
    train_loss: Optional[float] = None
    val_loss: Optional[float] = None


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None


class ModelResponse(ModelBase):
    id: str
    file_path: str
    file_size: int
    format: str
    dataset_version_id: Optional[str] = None
    class_ids: list[str]
    yolo_class_names: list[str]
    epochs: Optional[int] = None
    batch_size: Optional[int] = None
    img_size: Optional[int] = None
    map50: Optional[float] = None
    map50_95: Optional[float] = None
    train_loss: Optional[float] = None
    val_loss: Optional[float] = None
    trained_at: Optional[datetime] = None
    training_job_id: Optional[str] = None
    tags: Optional[list[str]] = None
    is_active: bool
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelStatsResponse(BaseModel):
    total_models: int
    active_models: int
    total_size_mb: float
    by_architecture: dict[str, int]
