"""Custom style model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class CustomStyle(Base):
    """Custom style model for user-defined visual styles."""

    __tablename__ = "custom_styles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Style info
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    normalized_name = Column(String, nullable=False)  # lowercase, no spaces
    
    # Preview
    preview_url = Column(String, nullable=True)
    
    # Visibility
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Usage stats
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="custom_styles")

    def __repr__(self):
        return f"<CustomStyle {self.name}>"

