from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class Token(BaseModel):
    """JWT Token response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[str] = None


class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=64)
    email: Optional[str] = Field(None, max_length=128)


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str = Field(..., min_length=6)
    role: str = Field(default="annotator")


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str
    password: str
