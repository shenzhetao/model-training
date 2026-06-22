"""ORM models for datasets and dataset versions."""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, JSON, BigInteger, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Dataset(Base):
    """A dataset that contains multiple annotated images for training."""
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_datasets_name", "name"),
    )

    def __repr__(self):
        return f"<Dataset({self.name})>"


class DatasetVersion(Base):
    """A frozen snapshot/version of a dataset with train/val/test splits."""
    __tablename__ = "dataset_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), nullable=False, index=True)
    version_name = Column(String(128), nullable=False)
    version_number = Column(Integer, nullable=False)
    train_ratio = Column(Float, nullable=False, default=0.9)
    val_ratio = Column(Float, nullable=False, default=0.1)
    test_ratio = Column(Float, nullable=False, default=0.0)
    random_seed = Column(Integer, nullable=False, default=42)
    image_count = Column(Integer, nullable=False, default=0)
    annotated_count = Column(Integer, nullable=False, default=0)
    class_ids = Column(JSON, nullable=False, default=list)
    yolo_dataset_path = Column(String(512), nullable=True)
    dataset_yaml_content = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="preparing")
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_dataset_versions_dataset_id", "dataset_id"),
        Index("idx_dataset_versions_status", "status"),
    )

    def __repr__(self):
        return f"<DatasetVersion({self.dataset_id}/v{self.version_number}, {self.version_name})>"


class DatasetVersionImage(Base):
    """Many-to-many link between dataset versions and images."""
    __tablename__ = "dataset_version_images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_version_id = Column(String(36), nullable=False, index=True)
    image_id = Column(String(36), nullable=False, index=True)
    split = Column(String(16), nullable=False)
    added_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_dataset_version_images_version_id", "dataset_version_id"),
        Index("idx_dataset_version_images_split", "split"),
    )
