"""ORM models for inference history and results."""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, BigInteger, Text, JSON, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class InferenceResult(Base):
    """A single inference result (from image/video/device screenshot)."""
    __tablename__ = "inference_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(256), nullable=True)
    source_type = Column(String(32), nullable=False, default="device")
    source_file = Column(String(512), nullable=True)
    model_id = Column(String(36), nullable=True, index=True)
    inference_mode = Column(String(32), nullable=False, default="hybrid")
    confidence_threshold = Column(Float, nullable=False, default=0.25)
    total_detections = Column(Integer, nullable=False, default=0)
    detections_json = Column(JSON, nullable=False, default=list)
    inference_time_ms = Column(Integer, nullable=True)
    image_path = Column(String(512), nullable=True)
    annotated_image_path = Column(String(512), nullable=True)
    video_frame_index = Column(Integer, nullable=True)
    device_id = Column(String(128), nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_inference_results_model_id", "model_id"),
        Index("idx_inference_results_source_type", "source_type"),
        Index("idx_inference_results_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<InferenceResult({self.source_type}, {self.total_detections} detections)>"
