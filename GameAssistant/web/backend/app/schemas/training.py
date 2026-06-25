"""Pydantic schemas for training management."""
from datetime import datetime
from typing import Optional
from pydantic import Field, ConfigDict

from app.schemas._base import NoProtectedNamespaceModel


class TrainingJobBase(NoProtectedNamespaceModel):
    name: str
    dataset_version_id: str
    base_model_architecture: str = "yolov8n"
    epochs: int = 50
    batch_size: int = 8
    img_size: int = 640
    lr0: float = 0.01
    lrf: float = 0.01
    weight_decay: float = 0.0005
    momentum: float = 0.937
    patience: int = 15
    mosaic: float = 1.0
    mixup: float = 0.0
    hsv_h: float = 0.015
    hsv_s: float = 0.7
    hsv_v: float = 0.4
    flip_lr: float = 0.5


class TrainingJobCreate(TrainingJobBase):
    resume_from: Optional[str] = None


class TrainingJobUpdate(NoProtectedNamespaceModel):
    name: Optional[str] = None
    status: Optional[str] = None
    current_epoch: Optional[int] = None
    best_model_id: Optional[str] = None
    error_message: Optional[str] = None


class TrainingJobResponse(TrainingJobBase):
    id: str
    status: str
    resume_from: Optional[str] = None
    best_model_id: Optional[str] = None
    process_id: Optional[int] = None
    log_output: Optional[str] = None
    log_summary: Optional[dict] = None
    current_epoch: Optional[int] = None
    gpu_device: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class TrainingLogResponse(NoProtectedNamespaceModel):
    id: str
    training_job_id: str
    epoch: int
    train_box_loss: Optional[float] = None
    train_cls_loss: Optional[float] = None
    train_dfl_loss: Optional[float] = None
    val_box_loss: Optional[float] = None
    val_cls_loss: Optional[float] = None
    val_dfl_loss: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    map50: Optional[float] = None
    map50_95: Optional[float] = None
    lr: Optional[float] = None
    gpu_memory_mb: Optional[int] = None
    epoch_duration_sec: Optional[int] = None
    logged_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class TrainingProgressResponse(NoProtectedNamespaceModel):
    job_id: str
    status: str
    current_epoch: int
    total_epochs: int
    best_model_id: Optional[str] = None
    current_map50: Optional[float] = None
    current_map: Optional[float] = None
    latest_metrics: Optional[TrainingLogResponse] = None
