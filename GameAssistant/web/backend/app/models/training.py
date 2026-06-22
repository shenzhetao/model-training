"""ORM models for training jobs and epoch logs."""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, JSON, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class TrainingJob(Base):
    """A training run for a YOLO model."""
    __tablename__ = "training_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    dataset_version_id = Column(String(36), nullable=False, index=True)
    base_model_architecture = Column(String(32), nullable=False, default="yolov8n")
    status = Column(String(32), nullable=False, default="pending")
    epochs = Column(Integer, nullable=False, default=50)
    batch_size = Column(Integer, nullable=False, default=8)
    img_size = Column(Integer, nullable=False, default=640)
    lr0 = Column(Float, nullable=False, default=0.01)
    lrf = Column(Float, nullable=False, default=0.01)
    weight_decay = Column(Float, nullable=False, default=0.0005)
    momentum = Column(Float, nullable=False, default=0.937)
    patience = Column(Integer, nullable=False, default=15)
    mosaic = Column(Float, nullable=False, default=1.0)
    mixup = Column(Float, nullable=False, default=0.0)
    hsv_h = Column(Float, nullable=False, default=0.015)
    hsv_s = Column(Float, nullable=False, default=0.7)
    hsv_v = Column(Float, nullable=False, default=0.4)
    flip_lr = Column(Float, nullable=False, default=0.5)
    resume_from = Column(String(36), nullable=True)
    best_model_id = Column(String(36), nullable=True)
    process_id = Column(Integer, nullable=True)
    log_output = Column(Text, nullable=True)
    log_summary = Column(JSON, nullable=True)
    current_epoch = Column(Integer, nullable=True)
    gpu_device = Column(String(16), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_training_jobs_dataset_version_id", "dataset_version_id"),
        Index("idx_training_jobs_status", "status"),
        Index("idx_training_jobs_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<TrainingJob({self.name}, status={self.status})>"


class TrainingLog(Base):
    """Per-epoch metrics logged during a training run."""
    __tablename__ = "training_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    training_job_id = Column(String(36), nullable=False, index=True)
    epoch = Column(Integer, nullable=False)
    train_box_loss = Column(Float, nullable=True)
    train_cls_loss = Column(Float, nullable=True)
    train_dfl_loss = Column(Float, nullable=True)
    val_box_loss = Column(Float, nullable=True)
    val_cls_loss = Column(Float, nullable=True)
    val_dfl_loss = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    map50 = Column(Float, nullable=True)
    map50_95 = Column(Float, nullable=True)
    lr = Column(Float, nullable=True)
    gpu_memory_mb = Column(Integer, nullable=True)
    epoch_duration_sec = Column(Integer, nullable=True)
    logged_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_training_logs_job_id", "training_job_id"),
    )

    def __repr__(self):
        return f"<TrainingLog(job={self.training_job_id}, epoch={self.epoch})>"
