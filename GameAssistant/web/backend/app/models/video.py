from sqlalchemy import Column, String, DateTime, Boolean, Integer, BigInteger, Float, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class SourceVideo(Base):
    """Source video model for storing uploaded video files."""
    __tablename__ = "source_videos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(256), nullable=False)
    original_filename = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)
    duration = Column(Float, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    fps = Column(Float, nullable=False)
    uploaded_by = Column(String(36), nullable=True)
    uploaded_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    is_deleted = Column(Boolean, nullable=False, default=False)

    extraction_tasks = relationship("VideoExtractionTask", back_populates="video")

    def __repr__(self):
        return f"<SourceVideo(id={self.id}, filename={self.filename}, duration={self.duration}s)>"


class VideoExtractionTask(Base):
    """Video extraction task model for tracking frame extraction jobs."""
    __tablename__ = "video_extraction_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey("source_videos.id"), nullable=False)
    strategy = Column(String(32), nullable=False)  # interval/count/scene_change
    interval_seconds = Column(Float, nullable=True)
    frame_count = Column(Integer, nullable=True)
    scene_threshold = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending/running/completed/failed
    total_frames = Column(Integer, nullable=True)
    extracted_frames = Column(Integer, nullable=True, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    error_message = Column(Text, nullable=True)

    video = relationship("SourceVideo", back_populates="extraction_tasks")

    __table_args__ = (
        Index("idx_video_extraction_video_id", "video_id"),
        Index("idx_video_extraction_status", "status"),
    )

    def __repr__(self):
        return f"<VideoExtractionTask(id={self.id}, strategy={self.strategy}, status={self.status})>"
