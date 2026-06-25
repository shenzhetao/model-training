from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


class ExtractionStrategy(str, Enum):
    """Video extraction strategy types."""
    INTERVAL = "interval"  # Extract every N seconds
    COUNT = "count"  # Extract N frames evenly distributed
    SCENE_CHANGE = "scene_change"  # Extract frames on scene changes


class ExtractionStatus(str, Enum):
    """Video extraction task status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SourceVideoBase(BaseModel):
    """Base source video schema."""
    original_filename: str
    duration: float
    width: int
    height: int
    fps: float


class SourceVideoCreate(SourceVideoBase):
    """Schema for creating a source video record."""
    filename: str
    file_path: str
    file_size: int
    uploaded_by: Optional[str] = None


class SourceVideoResponse(SourceVideoBase):
    """Schema for source video response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_path: str
    file_size: int
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    is_deleted: bool


class VideoUploadResponse(BaseModel):
    """Response for video upload."""
    success: bool
    message: str
    video: Optional[SourceVideoResponse] = None


class ExtractionTaskBase(BaseModel):
    """Base extraction task schema."""
    strategy: ExtractionStrategy
    interval_seconds: Optional[float] = None
    frame_count: Optional[int] = None
    scene_threshold: Optional[float] = None


class ExtractionTaskCreate(ExtractionTaskBase):
    """Schema for creating an extraction task."""
    pass


class ExtractionTaskResponse(ExtractionTaskBase):
    """Schema for extraction task response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    status: str
    total_frames: Optional[int] = None
    extracted_frames: Optional[int] = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime
    error_message: Optional[str] = None


class ExtractionTaskCreateResponse(BaseModel):
    """Response for extraction task creation."""
    success: bool
    message: str
    task: Optional[ExtractionTaskResponse] = None


class SourceVideoListResponse(BaseModel):
    """Response for paginated source video list."""
    items: list[SourceVideoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ExtractionTaskListResponse(BaseModel):
    """Response for extraction task list."""
    items: list[ExtractionTaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
