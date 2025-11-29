"""User API keys model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserAPIKey(Base):
    """User API keys for AI services."""

    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Service info
    service_name = Column(String, nullable=False)  # openai, groq, elevenlabs, etc.
    encrypted_key = Column(String, nullable=False)
    
    # Metadata
    key_name = Column(String, nullable=True)  # User-friendly name
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<UserAPIKey {self.service_name} for user {self.user_id}>"

