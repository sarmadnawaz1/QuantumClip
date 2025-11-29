"""Video schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, computed_field, model_validator

from app.models.video import VideoStatus


# User-facing status values that the frontend expects
USER_FACING_STATUSES = {
    "in_progress": "in_progress",
    "completed": "completed", 
    "failed": "failed"
}


def normalize_video_status(status: VideoStatus) -> str:
    """
    Normalize internal video status to user-facing status.
    
    Maps internal statuses to user-facing ones:
    - PENDING, PROCESSING, GENERATING_PROMPTS, GENERATING_IMAGES, GENERATING_AUDIO, RENDERING → "in_progress"
    - COMPLETED → "completed"
    - FAILED, CANCELLED → "failed"
    
    Args:
        status: Internal VideoStatus enum value
        
    Returns:
        User-facing status string: "in_progress", "completed", or "failed"
    """
    status_str = status.value if isinstance(status, VideoStatus) else str(status)
    status_lower = status_str.lower()
    
    # Map all processing states to "in_progress"
    if status_lower in ["pending", "processing", "generating_prompts", 
                        "generating_images", "generating_audio", "rendering"]:
        return "in_progress"
    
    # Map completed state
    if status_lower == "completed":
        return "completed"
    
    # Map failed/cancelled states
    if status_lower in ["failed", "cancelled"]:
        return "failed"
    
    # Default fallback for unknown statuses
    return "in_progress"


class SceneGeneration(BaseModel):
    """Scene generation data."""
    scene_number: int
    text: str
    image_prompt: str
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[float] = None


class VideoBase(BaseModel):
    """Base video schema."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    script: str = Field(..., min_length=10)


class VideoCreate(VideoBase):
    """Video creation schema."""
    # AI settings
    ai_provider: str = "groq"
    ai_model: Optional[str] = None
    image_service: str = "pollination"
    image_model: Optional[str] = None
    style: str = "cinematic"
    custom_instructions: Optional[str] = None
    target_scene_count: Optional[int] = Field(None, ge=1, le=50, description="Target number of scenes (1-50)")
    
    # TTS settings
    tts_provider: str = "edge"
    tts_voice: Optional[str] = None
    tts_model: Optional[str] = None
    
    # Video settings
    resolution: str = "1080p"
    orientation: str = "portrait"
    fps: int = 30
    
    # Optional settings
    background_music: Optional[str] = None
    video_overlay: Optional[str] = None
    font: Optional[str] = None
    subtitle_style: Optional[Dict[str, Any]] = None
    transition_type: str = "none"
    transition_duration: float = 0.5
    image_animation: Optional[str] = Field(None, description="Image animation: none, zoom_in, zoom_out, pan_left, pan_right, pan_up, pan_down, ken_burns")
    image_animation_intensity: float = Field(1.2, ge=1.0, le=2.0, description="Animation intensity (1.0-2.0)")
    rendering_preset: str = Field("fast", description="Rendering preset: fast (quick previews) or quality (final exports)")


class VideoUpdate(BaseModel):
    """Video update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[VideoStatus] = None


class VideoResponse(VideoBase):
    """Video response schema with normalized status for frontend."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    
    # Generation settings
    ai_provider: str
    ai_model: Optional[str]
    image_service: str
    image_model: Optional[str]
    style: str
    custom_instructions: Optional[str]
    target_scene_count: Optional[int]
    
    # TTS settings
    tts_provider: str
    tts_voice: Optional[str]
    tts_model: Optional[str]
    
    # Video settings
    resolution: str
    orientation: str
    fps: int
    
    # Optional settings
    background_music: Optional[str]
    video_overlay: Optional[str]
    font: Optional[str]
    subtitle_style: Optional[Dict[str, Any]]
    transition_type: str
    transition_duration: float
    image_animation: Optional[str]
    image_animation_intensity: float
    rendering_preset: str
    
    # Generation data
    scenes: Optional[List[Dict[str, Any]]]
    status: Union[VideoStatus, str]  # Can be VideoStatus enum (from DB) or string - will be normalized
    progress: float
    error_message: Optional[str]
    
    @model_validator(mode='after')
    def normalize_status_field(self) -> 'VideoResponse':
        """
        Normalize status field after model construction to user-facing value.
        
        This validator runs after Pydantic creates the model from the database object.
        It ensures the status is always one of: "in_progress", "completed", or "failed"
        """
        # Normalize status to user-facing value: "in_progress", "completed", or "failed"
        try:
            if isinstance(self.status, VideoStatus):
                # Status is a VideoStatus enum - normalize it
                normalized = normalize_video_status(self.status)
                object.__setattr__(self, 'status', normalized)  # Use object.__setattr__ for Pydantic v2
            elif isinstance(self.status, str):
                # Status is a string - check if it needs normalization
                if self.status in ["in_progress", "completed", "failed"]:
                    # Already normalized, keep it
                    pass
                else:
                    # Try to normalize if it's an internal status value
                    try:
                        status_enum = VideoStatus(self.status)
                        normalized = normalize_video_status(status_enum)
                        object.__setattr__(self, 'status', normalized)
                    except (ValueError, AttributeError, TypeError):
                        # Unknown status string, default to in_progress
                        object.__setattr__(self, 'status', "in_progress")
            else:
                # Status is None or unexpected type, default to in_progress
                object.__setattr__(self, 'status', "in_progress")
        except Exception as e:
            # If normalization fails for any reason, default to in_progress to prevent serialization errors
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to normalize status {self.status} (type: {type(self.status)}): {e}")
            try:
                object.__setattr__(self, 'status', "in_progress")
            except:
                pass  # If even setting fails, let Pydantic handle it
        
        return self
    
    # File paths
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    
    # Metadata
    duration: Optional[int]
    file_size: Optional[int]
    scene_count: Optional[int]
    task_id: Optional[str]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class VideoStatusResponse(BaseModel):
    """Video status response with granular progress information."""
    id: int
    status: str  # Normalized to user-facing status: "in_progress", "completed", "failed"
    progress: float
    error_message: Optional[str] = None
    video_url: Optional[str] = None
    current_step: Optional[str] = None
    estimated_time_remaining: Optional[int] = None  # in seconds
    scene_count: Optional[int] = None  # Total number of scenes
    current_scene: Optional[int] = None  # Current scene being processed (if applicable)


class VideoListResponse(BaseModel):
    """Video list response."""
    videos: List[VideoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

