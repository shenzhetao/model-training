"""Pydantic schemas for dataset management."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DatasetResponse(DatasetBase):
    id: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True


class DatasetVersionBase(BaseModel):
    version_name: str
    train_ratio: float = 0.9
    val_ratio: float = 0.1
    test_ratio: float = 0.0
    random_seed: int = 42
    class_ids: list[str] = Field(default_factory=list)


class DatasetVersionCreate(DatasetVersionBase):
    # dataset_id is taken from URL path, not request body
    pass


class DatasetVersionUpdate(BaseModel):
    version_name: Optional[str] = None
    status: Optional[str] = None


class DatasetVersionResponse(DatasetVersionBase):
    id: str
    dataset_id: str
    version_number: int
    image_count: int
    annotated_count: int
    yolo_dataset_path: Optional[str] = None
    dataset_yaml_content: Optional[str] = None
    status: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DatasetAddImagesRequest(BaseModel):
    image_ids: list[str]
    split: str = "train"


class DatasetVersionStatsResponse(BaseModel):
    total: int
    train: int
    val: int
    test: int
    annotated: int
    unannotated: int
