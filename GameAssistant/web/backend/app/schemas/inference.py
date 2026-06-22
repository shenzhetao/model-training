"""Pydantic schemas for inference history."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DetectionItemSchema(BaseModel):
    cls: str
    x: float
    y: float
    w: float
    h: float
    conf: float
    source: str


class InferenceResultBase(BaseModel):
    name: Optional[str] = None
    source_type: str = "device"
    source_file: Optional[str] = None
    model_id: Optional[str] = None
    inference_mode: str = "hybrid"
    confidence_threshold: float = 0.25


class InferenceResultCreate(InferenceResultBase):
    total_detections: int = 0
    detections_json: list[DetectionItemSchema] = []
    inference_time_ms: Optional[int] = None
    image_path: Optional[str] = None
    annotated_image_path: Optional[str] = None
    video_frame_index: Optional[int] = None
    device_id: Optional[str] = None


class InferenceResultResponse(InferenceResultBase):
    id: str
    total_detections: int
    detections_json: list[DetectionItemSchema]
    inference_time_ms: Optional[int] = None
    image_path: Optional[str] = None
    annotated_image_path: Optional[str] = None
    video_frame_index: Optional[int] = None
    device_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
