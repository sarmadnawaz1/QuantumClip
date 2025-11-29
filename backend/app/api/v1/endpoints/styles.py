"""Style endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core import get_db, get_current_user
from app.models.style import CustomStyle
from app.schemas.style import CustomStyleCreate, CustomStyleResponse
import json
import os

router = APIRouter()


@router.get("/builtin", response_model=List[dict])
async def list_builtin_styles():
    """List all built-in styles."""
    # Load style metadata from file
    style_file = "style_previews/style_metadata.json"
    if os.path.exists(style_file):
        with open(style_file, 'r') as f:
            data = json.load(f)
            styles = []
            for name, info in data.get("styles", {}).items():
                styles.append({
                    "name": name,
                    "normalized_name": info.get("normalized_name"),
                    "preview_url": f"/static/style_previews/{info.get('filename')}",
                    "description": info.get("prompt", ""),
                    "is_builtin": True
                })
            return styles
    
    return []


@router.get("/custom", response_model=List[CustomStyleResponse])
async def list_custom_styles(
    include_public: bool = Query(True),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List custom styles (user's own and public styles)."""
    query = select(CustomStyle).where(CustomStyle.is_active == True)
    
    if include_public:
        query = query.where(
            or_(
                CustomStyle.user_id == current_user["id"],
                CustomStyle.is_public == True
            )
        )
    else:
        query = query.where(CustomStyle.user_id == current_user["id"])
    
    result = await db.execute(query)
    styles = result.scalars().all()
    
    return styles


@router.post("/custom", response_model=CustomStyleResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_style(
    style_data: CustomStyleCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new custom style."""
    # Normalize name
    normalized_name = style_data.name.lower().replace(" ", "_").replace("-", "_")
    
    # Check if style name already exists for this user
    result = await db.execute(
        select(CustomStyle).where(
            CustomStyle.user_id == current_user["id"],
            CustomStyle.normalized_name == normalized_name
        )
    )
    existing_style = result.scalar_one_or_none()
    
    if existing_style:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A style with this name already exists"
        )
    
    # Create new style
    new_style = CustomStyle(
        user_id=current_user["id"],
        name=style_data.name,
        description=style_data.description,
        normalized_name=normalized_name,
        is_public=style_data.is_public,
    )
    
    db.add(new_style)
    await db.commit()
    await db.refresh(new_style)
    
    return new_style


@router.get("/custom/{style_id}", response_model=CustomStyleResponse)
async def get_custom_style(
    style_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get custom style by ID."""
    result = await db.execute(select(CustomStyle).where(CustomStyle.id == style_id))
    style = result.scalar_one_or_none()
    
    if not style:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style not found"
        )
    
    # Check access (owner or public style)
    if style.user_id != current_user["id"] and not style.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this style"
        )
    
    return style


@router.delete("/custom/{style_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_style(
    style_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a custom style."""
    result = await db.execute(select(CustomStyle).where(CustomStyle.id == style_id))
    style = result.scalar_one_or_none()
    
    if not style:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style not found"
        )
    
    # Check ownership
    if style.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this style"
        )
    
    await db.delete(style)
    await db.commit()
    
    return None

