"""Custom style schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CustomStyleBase(BaseModel):
    """Base custom style schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=10)


class CustomStyleCreate(CustomStyleBase):
    """Custom style creation schema."""
    is_public: bool = False


class CustomStyleUpdate(BaseModel):
    """Custom style update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None


class CustomStyleResponse(CustomStyleBase):
    """Custom style response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    normalized_name: str
    preview_url: Optional[str]
    is_public: bool
    is_active: bool
    usage_count: int
    created_at: datetime
    updated_at: datetime

