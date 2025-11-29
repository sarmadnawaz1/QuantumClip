"""User model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Profile fields
    avatar_url = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    
    # Usage tracking
    videos_generated = Column(Integer, default=0)
    total_video_duration = Column(Integer, default=0)  # in seconds
    
    # User preferences (JSON stored as text)
    favorite_voices = Column(Text, nullable=True)  # JSON array of favorite TTS voices
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verification_code = Column(String, nullable=True)
    email_verification_code_expires = Column(DateTime, nullable=True)
    
    # Password reset
    password_reset_code = Column(String, nullable=True)
    password_reset_code_expires = Column(DateTime, nullable=True)
    
    # OAuth
    google_id = Column(String, nullable=True, unique=True, index=True)
    oauth_provider = Column(String, nullable=True)  # 'google', etc.
    
    # Relationships
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    custom_styles = relationship("CustomStyle", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("UserAPIKey", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

