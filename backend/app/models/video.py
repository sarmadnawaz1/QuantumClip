"""Video model."""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    ForeignKey, JSON, Float, Enum as SQLEnum
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class VideoStatus(str, Enum):
    """Video generation status."""
    PENDING = "pending"
    PROCESSING = "processing"
    GENERATING_PROMPTS = "generating_prompts"
    GENERATING_IMAGES = "generating_images"
    GENERATING_AUDIO = "generating_audio"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Video(Base):
    """Video model for storing video generation projects."""

    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Basic info
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    script = Column(Text, nullable=False)
    
    # Generation settings
    ai_provider = Column(String, default="groq")  # groq, openai, gemini
    ai_model = Column(String, nullable=True)
    image_service = Column(String, default="pollination")  # replicate, together, fal, runware, pollination
    image_model = Column(String, nullable=True)
    style = Column(String, default="cinematic")
    custom_instructions = Column(Text, nullable=True)
    target_scene_count = Column(Integer, nullable=True)  # User-specified number of scenes
    
    # TTS settings
    tts_provider = Column(String, default="edge")  # edge, elevenlabs, fish
    tts_voice = Column(String, nullable=True)
    tts_model = Column(String, nullable=True)
    
    # Video settings
    resolution = Column(String, default="1080p")  # 720p, 1080p, 2K, 4K
    orientation = Column(String, default="portrait")  # portrait, landscape
    fps = Column(Integer, default=30)
    
    # Optional settings
    background_music = Column(String, nullable=True)
    video_overlay = Column(String, nullable=True)
    font = Column(String, nullable=True)
    subtitle_style = Column(JSON, nullable=True)
    transition_type = Column(String, default="none")
    transition_duration = Column(Float, default=0.5)
    image_animation = Column(String, nullable=True)  # none, zoom_in, zoom_out, pan_left, pan_right, pan_up, pan_down, ken_burns
    image_animation_intensity = Column(Float, default=1.2)
    rendering_preset = Column(String, default="fast")  # fast, quality
    
    # Generation data
    scenes = Column(JSON, nullable=True)  # Generated scenes with prompts
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.PENDING)
    progress = Column(Float, default=0.0)  # 0-100
    error_message = Column(Text, nullable=True)
    
    # File paths
    video_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    
    # Metadata
    duration = Column(Integer, nullable=True)  # in seconds
    file_size = Column(Integer, nullable=True)  # in bytes
    scene_count = Column(Integer, nullable=True)
    
    # Celery task
    task_id = Column(String, unique=True, index=True, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="videos")

    def __repr__(self):
        return f"<Video {self.title} ({self.status})>"

