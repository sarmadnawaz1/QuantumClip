"""Application configuration."""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Application
    app_name: str = "QuantumClip"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Database
    database_url: str = Field(
        default="sqlite:///./app.db"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = Field(default="change-this-secret-key")
    jwt_secret_key: str = Field(default="change-this-jwt-secret")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: List[str] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    # AI Providers
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    # Image Generation Services
    replicate_api_key: Optional[str] = None
    together_api_key: Optional[str] = None
    fal_key: Optional[str] = None
    runware_api_key: Optional[str] = None

    # Text-to-Speech Services
    elevenlabs_api_key: Optional[str] = None
    fish_audio_api_key: Optional[str] = None
    
    # Email Configuration
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = "muhammadsarmadnawaz@gmail.com"
    smtp_password: Optional[str] = None  # App password for Gmail
    email_from: str = "muhammadsarmadnawaz@gmail.com"
    email_from_name: str = "QuantumClip"
    
    # OAuth Configuration
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: Optional[str] = None

    # Storage
    storage_type: str = "local"  # 'local' or 's3'
    upload_dir: str = "./uploads"
    max_upload_size: int = 104857600  # 100MB

    # S3 Configuration
    s3_bucket: Optional[str] = None
    s3_region: str = "us-east-1"
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_endpoint_url: Optional[str] = None

    # Video Generation
    max_scenes: int = 14
    default_resolution: str = "1080p"
    default_orientation: str = "portrait"
    render_workers: int = 5
    render_mode: str = "parallel"

    # TTS
    default_tts_provider: str = "edge"
    edge_tts_pitch_percent: int = -3
    edge_tts_volume_percent: int = 100

    # Timeouts
    individual_image_timeout: int = 80
    individual_audio_timeout: int = 120

    # Task Queue
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_time_limit: int = 3600  # 1 hour

    # Logging
    log_level: str = "INFO"

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60

    # Monitoring
    sentry_dsn: Optional[str] = None

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"

    @property
    def database_url_async(self) -> str:
        """Get async database URL."""
        if "sqlite" in self.database_url:
            return self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")


# Global settings instance
settings = Settings()

