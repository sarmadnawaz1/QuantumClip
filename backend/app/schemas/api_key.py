"""API key schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class APIKeyBase(BaseModel):
    """Base API key schema."""
    service_name: str = Field(..., description="Service name (openai, groq, etc.)")
    key_name: Optional[str] = Field(None, description="Friendly name for the key")


class APIKeyCreate(APIKeyBase):
    """API key creation schema."""
    api_key: str = Field(..., description="The actual API key (will be encrypted)")


class APIKeyUpdate(BaseModel):
    """API key update schema."""
    key_name: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None


class APIKeyResponse(APIKeyBase):
    """API key response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    # Note: We never return the actual API key

