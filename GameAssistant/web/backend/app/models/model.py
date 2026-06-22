"""ORM model for trained models."""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, BigInteger, Text, JSON, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Model(Base):
    """A trained model (YOLO .pt file)."""
    __tablename__ = "models"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    architecture = Column(String(32), nullable=False, default="yolov8n")
    task_type = Column(String(32), nullable=False, default="detect")
    file_path = Column(String(512), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)
    format = Column(String(16), nullable=False, default="pt")
    dataset_version_id = Column(String(36), nullable=True, index=True)
    class_ids = Column(JSON, nullable=False, default=list)
    yolo_class_names = Column(JSON, nullable=False, default=list)
    epochs = Column(Integer, nullable=True)
    batch_size = Column(Integer, nullable=True)
    img_size = Column(Integer, nullable=True)
    map50 = Column(Float, nullable=True)
    map50_95 = Column(Float, nullable=True)
    train_loss = Column(Float, nullable=True)
    val_loss = Column(Float, nullable=True)
    trained_at = Column(DateTime, nullable=True)
    training_job_id = Column(String(36), nullable=True)
    tags = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    uploaded_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_models_architecture", "architecture"),
        Index("idx_models_dataset_version_id", "dataset_version_id"),
    )

    def __repr__(self):
        return f"<Model({self.name}, {self.architecture}, {self.format})>"
