from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ImageQueryParams(BaseModel):
    """Query parameters for image list."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    source: Optional[str] = Field(default=None, description="Filter by source: upload/adb/video")


class ImageBase(BaseModel):
    """Base image schema."""
    original_filename: str
    width: int
    height: int
    source: str = "upload"


class ImageCreate(ImageBase):
    """Schema for creating an image record."""
    filename: str
    file_path: str
    file_size: int
    md5_hash: str
    phash: Optional[str] = None
    source_video_id: Optional[str] = None
    source_video_timestamp: Optional[float] = None
    uploaded_by: Optional[str] = None


class ImageUpdate(BaseModel):
    """Schema for updating an image."""
    is_deleted: Optional[bool] = None


class ImageResponse(ImageBase):
    """Schema for image response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_path: str
    file_size: int
    md5_hash: str
    phash: Optional[str] = None
    source_video_id: Optional[str] = None
    source_video_timestamp: Optional[float] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    updated_at: datetime
    is_deleted: bool


class ImageUploadResponse(BaseModel):
    """Response for single image upload."""
    success: bool
    message: str
    image: Optional[ImageResponse] = None
    is_duplicate: bool = False
    existing_image_id: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """Response for batch upload (ZIP)."""
    success: bool
    message: str
    total: int
    uploaded: int
    skipped: int
    failed: int
    duplicates: int
    images: list[ImageResponse]
    errors: list[str]


class ImageDeleteResponse(BaseModel):
    """Response for image deletion."""
    success: bool
    message: str
    deleted_count: int = 0


class ImageListResponse(BaseModel):
    """Schema for paginated image list."""
    items: list[ImageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
