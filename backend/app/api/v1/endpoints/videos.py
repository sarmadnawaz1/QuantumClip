"""Video generation endpoints."""

from typing import Optional, Iterable
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pathlib import Path
import shutil
from starlette.background import BackgroundTask

from app.core import get_db, get_current_user
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.video import Video, VideoStatus
from app.models.user import User
from app.models.api_key import UserAPIKey
from app.schemas.video import (
    VideoCreate, VideoResponse, VideoUpdate, 
    VideoStatusResponse, VideoListResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parents[4] / "uploads"


def _normalize_upload_path(raw_path: Optional[str]) -> Optional[Path]:
    """Convert a stored URL/path into an absolute path inside the uploads directory."""
    if not raw_path:
        return None
    normalized = raw_path.replace("\\", "/")
    if normalized.startswith("/"):
        normalized = normalized[1:]
    if normalized.startswith("uploads/"):
        normalized = normalized[len("uploads/") :]
    target = UPLOAD_DIR / normalized
    try:
        target.resolve().relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        # Path escapes uploads directory; do not delete
        return None
    return target


def _delete_paths(paths: Iterable[Optional[str]]):
    """Remove files/directories associated with old videos."""
    for raw in paths:
        path = _normalize_upload_path(raw) if isinstance(raw, str) else None
        if not path:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                path.unlink(missing_ok=True)
            except IsADirectoryError:
                shutil.rmtree(path, ignore_errors=True)


def _collect_scene_media(scene: dict) -> Iterable[Optional[str]]:
    media_keys = (
        "image_url",
        "image_path",
        "audio_url",
        "audio_path",
        "music_url",
        "music_path",
        "subtitle_url",
        "subtitle_path",
        "background_url",
        "background_path",
    )
    for key in media_keys:
        value = scene.get(key)
        if isinstance(value, str):
            yield value


async def cleanup_existing_videos(user_id: int, db: AsyncSession, only_completed: bool = True) -> None:
    """
    Remove previously generated videos and associated media for the user.
    
    Preserves:
    - All PENDING videos (in case user wants to retry)
    - The most recent COMPLETED video
    - The most recent FAILED video
    
    Deletes all other videos (older completed/failed, and all processing videos except pending).
    
    Args:
        user_id: User ID
        db: Database session
        only_completed: If True, only delete completed videos (old behavior). If False, use smart cleanup.
    """
    if only_completed:
        # Old behavior: Delete only COMPLETED videos (for backward compatibility)
        query = select(Video).where(
            Video.user_id == user_id,
            Video.status == VideoStatus.COMPLETED
        )
        result = await db.execute(query)
        videos = result.scalars().all()
    else:
        # Smart cleanup: Keep most recent completed and failed, delete all others except PENDING
        # Get all videos except PENDING
        all_videos_query = select(Video).where(
            Video.user_id == user_id,
            Video.status != VideoStatus.PENDING
        ).order_by(desc(Video.created_at))
        
        result = await db.execute(all_videos_query)
        all_videos = result.scalars().all()
        
        if not all_videos:
            return
        
        # Find most recent completed and failed videos
        most_recent_completed = None
        most_recent_failed = None
        
        for video in all_videos:
            if video.status == VideoStatus.COMPLETED and most_recent_completed is None:
                most_recent_completed = video
            elif video.status == VideoStatus.FAILED and most_recent_failed is None:
                most_recent_failed = video
            # Stop once we found both
            if most_recent_completed and most_recent_failed:
                break
        
        # Videos to delete: all except the most recent completed/failed
        videos_to_delete = []
        for video in all_videos:
            if video.status == VideoStatus.PROCESSING or \
               video.status in [VideoStatus.GENERATING_PROMPTS, VideoStatus.GENERATING_IMAGES, 
                                VideoStatus.GENERATING_AUDIO, VideoStatus.RENDERING]:
                # Always delete processing videos (except PENDING which we already filtered)
                videos_to_delete.append(video)
            elif video.status == VideoStatus.COMPLETED:
                # Keep only the most recent completed
                if video.id != (most_recent_completed.id if most_recent_completed else None):
                    videos_to_delete.append(video)
            elif video.status == VideoStatus.FAILED:
                # Keep only the most recent failed
                if video.id != (most_recent_failed.id if most_recent_failed else None):
                    videos_to_delete.append(video)
        
        videos = videos_to_delete
    
    if not videos:
        return

    for video in videos:
        # Remove video-level files
        paths_to_delete = [video.video_url, video.thumbnail_url]

        # Remove scene-level assets
        if isinstance(video.scenes, list):
            for scene in video.scenes:
                if isinstance(scene, dict):
                    paths_to_delete.extend(list(_collect_scene_media(scene)))

        _delete_paths(paths_to_delete)
        db.delete(video)

    await db.commit()


async def _delete_video_record(video: Video, db: AsyncSession) -> None:
    """Delete a single video record and associated files."""
    paths_to_delete = [video.video_url, video.thumbnail_url]
    if isinstance(video.scenes, list):
        for scene in video.scenes:
            if isinstance(scene, dict):
                paths_to_delete.extend(list(_collect_scene_media(scene)))

    _delete_paths(paths_to_delete)
    db.delete(video)
    await db.commit()


async def _delete_video_after_download(video_id: int) -> None:
    """Background cleanup after a download response completes."""
    import asyncio
    await asyncio.sleep(5)  # brief delay to ensure download stream finishes
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).where(Video.id == video_id))
        video = result.scalar_one_or_none()
        if not video:
            return
        await _delete_video_record(video, session)


def _schedule_video_cleanup(video_id: int) -> None:
    """Schedule async cleanup task from background context."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        loop.create_task(_delete_video_after_download(video_id))
    else:
        asyncio.run(_delete_video_after_download(video_id))


async def generate_video_background_real(video_id: int, user_id: int):
    """
    Generate video in the background using REAL desktop app services.
    
    Status Flow:
    - Video is created with status PENDING (in create_video endpoint)
    - When this function starts: status → PROCESSING
    - During generation: status → GENERATING_PROMPTS → GENERATING_IMAGES → GENERATING_AUDIO → RENDERING
    - On success: status → COMPLETED
    - On failure: status → FAILED
    
    All statuses are normalized to user-facing values in API responses:
    - PENDING, PROCESSING, GENERATING_* → "in_progress"
    - COMPLETED → "completed"
    - FAILED, CANCELLED → "failed"
    """
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.config import settings
    from app.core.security import decrypt_api_key
    import os
    
    # Create sync engine for background task
    sync_engine = create_engine(settings.database_url)
    
    with Session(sync_engine) as db:
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                return
            
            # Get user's API keys
            user_api_keys = db.query(UserAPIKey).filter(
                UserAPIKey.user_id == user_id,
                UserAPIKey.is_active == True
            ).all()
            
            # Set environment variables for API keys
            for key in user_api_keys:
                decrypted_key = decrypt_api_key(key.encrypted_key)
                service_name_upper = key.service_name.upper().replace('_', '_')
                
                # Map service names to environment variable names
                env_var_map = {
                    'groq': 'GROQ_API_KEY',
                    'openai': 'OPENAI_API_KEY',
                    'google': 'GOOGLE_API_KEY',
                    'replicate': 'REPLICATE_API_KEY',
                    'together': 'TOGETHER_API_KEY',
                    'fal': 'FAL_KEY',
                    'runware': 'RUNWARE_API_KEY',
                    'elevenlabs': 'ELEVENLABS_API_KEY',
                    'fish_audio': 'FISH_AUDIO_API_KEY'
                }
                
                env_var = env_var_map.get(key.service_name)
                if env_var:
                    os.environ[env_var] = decrypted_key
                    print(f"✅ Set {env_var} from user's API keys")
            
            # Import WebSocket manager for real-time updates
            from app.services.websocket_manager import websocket_manager
            import asyncio
            
            # Update status: PENDING → PROCESSING (when generation actually starts)
            video.status = VideoStatus.PROCESSING
            video.progress = 10
            db.commit()
            
            # Emit WebSocket update
            asyncio.create_task(websocket_manager.broadcast_progress(
                video_id=video_id,
                status=video.status,
                progress=video.progress,
                current_step="Starting video generation..."
            ))
            
            # Step 1: Generate image prompts (with timing)
            import time
            import logging
            logger = logging.getLogger(__name__)
            
            prompt_start_time = time.time()
            logger.info(f"[VIDEO {video_id}] === Stage: Generating image prompts ===")
            print(f"🎨 Generating prompts for video {video_id}...")
            video.status = VideoStatus.GENERATING_PROMPTS
            video.progress = 10
            db.commit()
            
            from app.services.prompt_service import generate_prompts_from_script
            scenes = generate_prompts_from_script(
                script=video.script,
                style=video.style,
                custom_instructions=video.custom_instructions,
                ai_provider=video.ai_provider,
                ai_model=video.ai_model,
                target_scene_count=video.target_scene_count,
            )
            
            video.scenes = [scene for scene in scenes]  # Convert to list for JSON storage
            video.scene_count = len(scenes)
            video.progress = 20
            db.commit()
            
            prompt_elapsed = time.time() - prompt_start_time
            logger.info(f"[VIDEO {video_id}] Generated {len(scenes)} scene prompts in {prompt_elapsed:.2f}s")
            print(f"✅ Generated {len(scenes)} scene prompts in {prompt_elapsed:.2f}s")
            
            # Step 2: Generate images (with timing)
            image_start_time = time.time()
            logger.info(f"[VIDEO {video_id}] === Stage: Generating images ===")
            print(f"🖼️ Generating images for video {video_id}...")
            video.status = VideoStatus.GENERATING_IMAGES
            video.progress = 20
            db.commit()
            
            from app.services.image_service import generate_images_for_scenes
            
            def image_progress_callback(progress: float):
                """Update progress for image generation (20-60% overall)."""
                overall_progress = 20.0 + (progress * 0.4)
                video.progress = min(overall_progress, 60.0)
                db.commit()
                logger.debug(f"[VIDEO {video_id}] Image generation: {progress:.1f}%")
            
            scenes_with_images = generate_images_for_scenes(
                scenes=scenes,
                image_service=video.image_service,
                image_model=video.image_model,
                resolution=video.resolution,
                orientation=video.orientation,
                video_id=video_id,
                progress_callback=image_progress_callback
            )
            
            video.scenes = [scene for scene in scenes_with_images]
            video.progress = 60
            db.commit()
            
            image_elapsed = time.time() - image_start_time
            logger.info(f"[VIDEO {video_id}] Generated images for {len(scenes_with_images)} scenes in {image_elapsed:.2f}s")
            print(f"✅ Generated images for {len(scenes_with_images)} scenes in {image_elapsed:.2f}s")
            
            # Emit WebSocket update
            asyncio.create_task(websocket_manager.broadcast_progress(
                video_id=video_id,
                status=video.status,
                progress=video.progress,
                current_step=f"Generated images for {len(scenes_with_images)} scenes",
                scene_count=len(scenes_with_images)
            ))
            
            # Step 3: Generate audio (with timing)
            audio_start_time = time.time()
            logger.info(f"[VIDEO {video_id}] === Stage: Generating audio ===")
            print(f"🎤 Generating audio for video {video_id}...")
            video.status = VideoStatus.GENERATING_AUDIO
            video.progress = 60
            db.commit()
            
            from app.services.audio_service import generate_audio_for_scenes
            
            def audio_progress_callback(progress: float):
                """Update progress for audio generation (60-80% overall)."""
                overall_progress = 60.0 + (progress * 0.2)
                video.progress = min(overall_progress, 80.0)
                db.commit()
                logger.debug(f"[VIDEO {video_id}] Audio generation: {progress:.1f}%")
                
                # Emit WebSocket update
                asyncio.create_task(websocket_manager.broadcast_progress(
                    video_id=video_id,
                    status=video.status,
                    progress=overall_progress,
                    current_step=f"Generating audio... {progress:.0f}%",
                    scene_count=video.scene_count
                ))
            
            scenes_with_audio = generate_audio_for_scenes(
                scenes=scenes_with_images,
                tts_provider=video.tts_provider,
                tts_voice=video.tts_voice,
                tts_model=video.tts_model,
                video_id=video_id,
                progress_callback=audio_progress_callback
            )
            
            video.scenes = [scene for scene in scenes_with_audio]
            video.progress = 80
            db.commit()
            
            audio_elapsed = time.time() - audio_start_time
            logger.info(f"[VIDEO {video_id}] Generated audio for {len(scenes_with_audio)} scenes in {audio_elapsed:.2f}s")
            print(f"✅ Generated audio for {len(scenes_with_audio)} scenes in {audio_elapsed:.2f}s")
            
            # Emit WebSocket update
            asyncio.create_task(websocket_manager.broadcast_progress(
                video_id=video_id,
                status=video.status,
                progress=video.progress,
                current_step=f"Generated audio for {len(scenes_with_audio)} scenes",
                scene_count=len(scenes_with_audio)
            ))
            
            # Step 4: Render video (with timing and optimized pipeline)
            import time
            import logging
            render_start_time = time.time()
            logger = logging.getLogger(__name__)
            
            logger.info(f"[VIDEO {video_id}] === Starting video rendering ===")
            print(f"🎬 Rendering final video {video_id}...")
            video.status = VideoStatus.RENDERING
            db.commit()
            
            # Use optimized renderer with scene-based approach
            from app.services.video_service_optimized import render_video_optimized
            import os
            
            # Get rendering preset (default to 'fast' if not set)
            rendering_preset = getattr(video, 'rendering_preset', 'fast') or 'fast'
            
            def progress_callback(progress: float, stage: str):
                """Update progress with stage information."""
                # Map to overall progress (80-100% for rendering)
                overall_progress = 80.0 + (progress * 0.2)
                video.progress = min(overall_progress, 100.0)
                video.error_message = None  # Clear any previous errors
                db.commit()
                logger.info(f"[VIDEO {video_id}] Progress: {overall_progress:.1f}% - {stage}")
                print(f"Render progress: {overall_progress:.1f}% - {stage}")
                
                # Emit WebSocket update
                asyncio.create_task(websocket_manager.broadcast_progress(
                    video_id=video_id,
                    status=video.status,
                    progress=overall_progress,
                    current_step=stage,
                    scene_count=video.scene_count
                ))
            
            video_path, thumbnail_path, duration, file_size = render_video_optimized(
                scenes=scenes_with_audio,
                video_id=video_id,
                resolution=video.resolution,
                orientation=video.orientation,
                fps=video.fps,
                background_music=video.background_music,
                video_overlay=video.video_overlay,
                font=video.font,
                subtitle_style=video.subtitle_style,
                transition_type=video.transition_type,
                transition_duration=video.transition_duration,
                image_animation=video.image_animation,
                image_animation_intensity=video.image_animation_intensity or 1.2,
                rendering_preset=rendering_preset,
                progress_callback=progress_callback
            )
            
            render_elapsed = time.time() - render_start_time
            logger.info(f"[VIDEO {video_id}] === Video rendering completed in {render_elapsed:.2f}s ===")
            
            # Verify files exist before marking as completed
            video_file_path = video_path.replace("/uploads/", "uploads/")
            thumbnail_file_path = thumbnail_path.replace("/uploads/", "uploads/")
            
            if not os.path.exists(video_file_path):
                raise FileNotFoundError(f"Video file not found after rendering: {video_file_path}")
            if not os.path.exists(thumbnail_file_path):
                print(f"Warning: Thumbnail file not found: {thumbnail_file_path}")
            
            # Mark video as completed
            video.video_url = video_path
            video.thumbnail_url = thumbnail_path
            video.duration = duration
            video.file_size = file_size
            video.status = VideoStatus.COMPLETED  # Will be normalized to "completed" in API response
            video.progress = 100
            db.commit()
            
            print(f"🎉 Video generation completed for video_id={video_id}")
            print(f"📹 Video saved at: {video_path}")
            
            # Emit final WebSocket update
            asyncio.create_task(websocket_manager.broadcast_progress(
                video_id=video_id,
                status=VideoStatus.COMPLETED,
                progress=100.0,
                current_step="Video generation completed!",
                scene_count=video.scene_count
            ))
            
        except Exception as e:
            print(f"❌ Error generating video {video_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Mark video as failed on exception
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = VideoStatus.FAILED  # Will be normalized to "failed" in API response
                video.error_message = str(e)
                db.commit()
                
                # Emit WebSocket error update
                asyncio.create_task(websocket_manager.broadcast_progress(
                    video_id=video_id,
                    status=VideoStatus.FAILED,
                    progress=video.progress,
                    current_step="Video generation failed",
                    error_message=str(e),
                    scene_count=video.scene_count
                ))


@router.post("/", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(
    video_data: VideoCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new video generation job.
    
    Status Flow:
    - Video is created with status PENDING
    - Background task (generate_video_background_real) will update status as generation progresses
    - Status will be normalized to "in_progress" in API response until completed/failed
    
    Returns:
        VideoResponse with normalized status: "in_progress" (for PENDING), "completed", or "failed"
    """
    try:
        logger.info(f"[CREATE_VIDEO] Creating video for user {current_user['id']}: {video_data.title}")
        
        # Remove all videos except PENDING ones to conserve storage
        # Only PENDING videos are preserved (in case user wants to retry)
        # All other statuses (COMPLETED, FAILED, PROCESSING, etc.) are deleted
        await cleanup_existing_videos(current_user["id"], db, only_completed=False)

        # Create video record with PENDING status
        # This will be normalized to "in_progress" in the VideoResponse
        new_video = Video(
            user_id=current_user["id"],
            title=video_data.title,
            description=video_data.description,
            script=video_data.script,
            ai_provider=video_data.ai_provider,
            ai_model=video_data.ai_model,
            image_service=video_data.image_service,
            image_model=video_data.image_model,
            style=video_data.style,
            custom_instructions=video_data.custom_instructions,
            tts_provider=video_data.tts_provider,
            tts_voice=video_data.tts_voice,
            tts_model=video_data.tts_model,
            resolution=video_data.resolution,
            orientation=video_data.orientation,
            fps=video_data.fps,
            background_music=video_data.background_music,
            video_overlay=video_data.video_overlay,
            font=video_data.font,
            subtitle_style=video_data.subtitle_style,
            transition_type=video_data.transition_type,
            transition_duration=video_data.transition_duration,
            image_animation=video_data.image_animation,
            image_animation_intensity=video_data.image_animation_intensity or 1.2,
            rendering_preset=video_data.rendering_preset or "fast",
            target_scene_count=video_data.target_scene_count,
            status=VideoStatus.PENDING,  # Initial status - will be normalized to "in_progress" in response
        )
        
        db.add(new_video)
        await db.commit()
        await db.refresh(new_video)
        
        logger.info(f"[CREATE_VIDEO] Video created successfully: ID={new_video.id}, title={new_video.title}")
        
        # Queue the REAL video generation as background task
        background_tasks.add_task(generate_video_background_real, new_video.id, current_user["id"])
        logger.info(f"[CREATE_VIDEO] Background task queued for video {new_video.id}")
        
        # Return the video object - FastAPI will automatically serialize using VideoResponse
        # The response_model=VideoResponse decorator handles conversion and status normalization
        return new_video
            
    except HTTPException:
        # Re-raise HTTP exceptions (they're intentional)
        raise
    except Exception as e:
        # Log full error details for debugging
        logger.error(f"[CREATE_VIDEO] Unexpected error creating video for user {current_user.get('id', 'unknown')}: {e}", exc_info=True)
        # Return user-friendly error message
        error_detail = str(e)
        # Don't expose internal errors in production
        if not settings.debug:
            error_detail = "Failed to create video. Please try again."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get("/", response_model=VideoListResponse)
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[VideoStatus] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's videos."""
    # Build query
    query = select(Video).where(Video.user_id == current_user["id"])
    
    if status:
        query = query.where(Video.status == status)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar()
    
    # Get paginated results
    query = query.order_by(desc(Video.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    videos = result.scalars().all()
    
    # Convert to response models for proper serialization
    # FastAPI will automatically serialize SQLAlchemy models if response_model is set,
    # but we'll convert them explicitly for better control
    try:
        video_responses = [VideoResponse.model_validate(video) for video in videos]
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error serializing videos: {e}", exc_info=True)
        # Fallback: return videos as-is (FastAPI will handle serialization via response_model)
        video_responses = videos
    
    return VideoListResponse(
        videos=video_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get video by ID."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Check ownership
    if video.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this video"
        )
    
    return video


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get video generation status."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Check ownership
    if video.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this video"
        )
    
    # Get current step based on status with detailed messages
    current_step = None
    if video.status == VideoStatus.PENDING:
        current_step = "Video queued, starting generation..."
    elif video.status == VideoStatus.PROCESSING:
        current_step = "Processing video..."
    elif video.status == VideoStatus.GENERATING_PROMPTS:
        current_step = f"Generating scene prompts using AI... ({video.scene_count or 'calculating'} scenes)"
    elif video.status == VideoStatus.GENERATING_IMAGES:
        current_step = f"Generating images for {video.scene_count or 'N/A'} scenes..."
    elif video.status == VideoStatus.GENERATING_AUDIO:
        current_step = f"Generating audio narration for {video.scene_count or 'N/A'} scenes..."
    elif video.status == VideoStatus.RENDERING:
        current_step = "Rendering final video with FFmpeg..."
    
    # Normalize status to user-facing value
    from app.schemas.video import normalize_video_status
    normalized_status = normalize_video_status(video.status)
    
    return {
        "id": video.id,
        "status": normalized_status,  # Return normalized status: "in_progress", "completed", or "failed"
        "progress": video.progress,
        "error_message": video.error_message,
        "video_url": video.video_url,
        "current_step": current_step,
        "estimated_time_remaining": None,
        "scene_count": video.scene_count,
        "current_scene": None,
    }


@router.put("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: int,
    video_update: VideoUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update video metadata."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Check ownership
    if video.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this video"
        )
    
    # Update fields
    update_data = video_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(video, field, value)
    
    await db.commit()
    await db.refresh(video)
    
    return video


@router.delete("/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_videos(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete all videos for the current user, including all associated files."""
    try:
        logger.info(f"[DELETE_ALL] Starting deletion of all videos for user {current_user['id']}")
        
        # Get all videos for the user
        query = select(Video).where(Video.user_id == current_user["id"])
        result = await db.execute(query)
        videos = result.scalars().all()
        
        if not videos:
            logger.info(f"[DELETE_ALL] No videos found for user {current_user['id']}")
            return
        
        logger.info(f"[DELETE_ALL] Found {len(videos)} videos to delete for user {current_user['id']}")
        
        # Delete all videos and their files
        deleted_count = 0
        for video in videos:
            try:
                # Collect all file paths to delete
                paths_to_delete = []
                
                # Add video and thumbnail URLs
                if video.video_url:
                    paths_to_delete.append(video.video_url)
                if video.thumbnail_url:
                    paths_to_delete.append(video.thumbnail_url)
                
                # Add scene-level assets
                if isinstance(video.scenes, list):
                    for scene in video.scenes:
                        if isinstance(scene, dict):
                            paths_to_delete.extend(list(_collect_scene_media(scene)))
                
                # Delete all associated files
                if paths_to_delete:
                    _delete_paths(paths_to_delete)
                    logger.debug(f"[DELETE_ALL] Deleted files for video {video.id}: {paths_to_delete}")
                
                # Delete the database record
                await db.delete(video)
                deleted_count += 1
                
            except Exception as video_error:
                logger.error(f"[DELETE_ALL] Error deleting video {video.id}: {video_error}", exc_info=True)
                # Continue with other videos even if one fails
                continue
        
        # Commit all deletions
        await db.commit()
        logger.info(f"[DELETE_ALL] Successfully deleted {deleted_count} videos and their files for user {current_user['id']}")
        
    except Exception as e:
        logger.error(f"[DELETE_ALL] Error deleting all videos for user {current_user.get('id', 'unknown')}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete all videos: {str(e)}"
        )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a video."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Check ownership
    if video.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this video"
        )
    
    db.delete(video)
    await db.commit()
    
    return None


@router.post("/{video_id}/cancel", response_model=VideoResponse)
async def cancel_video(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a video generation job."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Check ownership
    if video.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this video"
        )
    
    # Can only cancel pending or processing videos
    if video.status not in [VideoStatus.PENDING, VideoStatus.PROCESSING, 
                           VideoStatus.GENERATING_PROMPTS, VideoStatus.GENERATING_IMAGES,
                           VideoStatus.GENERATING_AUDIO, VideoStatus.RENDERING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel video in current status"
        )
    
    video.status = VideoStatus.CANCELLED
    await db.commit()
    await db.refresh(video)
    
    return video


@router.get("/{video_id}/download")
async def download_video(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Download a completed video."""
    from fastapi.responses import FileResponse
    from app.core.config import settings
    import os
    
    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Check ownership
    if video.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to download this video"
        )
    
    # Check if video is completed
    if video.status != VideoStatus.COMPLETED or not video.video_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is not ready for download yet"
        )
    
    # Get file path - video_url is stored as "/uploads/filename.mp4"
    # Convert to absolute path
    filename_from_url = video.video_url.replace("/uploads/", "").lstrip("/")
    
    # Get backend directory (app/api/v1/endpoints/videos.py -> backend/)
    current_file = os.path.abspath(__file__)
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
    upload_dir = os.path.join(backend_dir, "uploads")
    file_path = os.path.join(upload_dir, filename_from_url)
    
    # Normalize path
    file_path = os.path.normpath(file_path)
    
    if not os.path.exists(file_path):
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Video file not found: {file_path}")
        logger.error(f"Video URL from DB: {video.video_url}")
        logger.error(f"Filename extracted: {filename_from_url}")
        logger.error(f"Backend dir: {backend_dir}")
        logger.error(f"Upload dir: {upload_dir}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file not found on server"
        )
    
    # Return file with proper download headers
    safe_filename = f"{video.title.replace(' ', '_').replace('/', '_')}.mp4"
    background_task = BackgroundTask(_schedule_video_cleanup, video.id)
    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=safe_filename,
        headers={
            "Content-Disposition": f"attachment; filename={safe_filename}"
        },
        background=background_task
    )
