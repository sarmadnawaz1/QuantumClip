"""Video generation Celery task."""

import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.models.video import Video, VideoStatus
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create sync engine for Celery tasks
sync_engine = create_engine(settings.database_url)


@celery_app.task(bind=True, name="generate_video")
def generate_video_task(self, video_id: int):
    """
    Generate video from script.
    
    This is the main task that orchestrates the entire video generation process:
    1. Generate image prompts from script
    2. Generate images from prompts
    3. Generate audio/TTS from script
    4. Combine everything into final video
    """
    logger.info(f"Starting video generation for video_id={video_id}")
    
    # Create database session
    with Session(sync_engine) as db:
        try:
            # Get video from database
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                logger.error(f"Video {video_id} not found")
                return
            
            # Update status to processing
            video.status = VideoStatus.PROCESSING
            video.progress = 0
            db.commit()
            
            # Step 1: Generate image prompts (20% of progress)
            logger.info(f"Generating prompts for video {video_id}")
            video.status = VideoStatus.GENERATING_PROMPTS
            db.commit()
            
            from app.services.prompt_service import generate_prompts_from_script
            scenes = generate_prompts_from_script(
                script=video.script,
                style=video.style,
                custom_instructions=video.custom_instructions,
                ai_provider=video.ai_provider,
                ai_model=video.ai_model,
            )
            
            video.scenes = scenes
            video.scene_count = len(scenes)
            video.progress = 20
            db.commit()
            
            # Step 2: Generate images (40% of progress)
            logger.info(f"Generating images for video {video_id}")
            video.status = VideoStatus.GENERATING_IMAGES
            db.commit()
            
            from app.services.image_service import generate_images_for_scenes
            scenes_with_images = generate_images_for_scenes(
                scenes=scenes,
                image_service=video.image_service,
                image_model=video.image_model,
                resolution=video.resolution,
                orientation=video.orientation,
                video_id=video_id,
                progress_callback=lambda p: update_progress(video_id, 20 + (p * 0.4))
            )
            
            video.scenes = scenes_with_images
            video.progress = 60
            db.commit()
            
            # Step 3: Generate audio (20% of progress)
            logger.info(f"Generating audio for video {video_id}")
            video.status = VideoStatus.GENERATING_AUDIO
            db.commit()
            
            from app.services.audio_service import generate_audio_for_scenes
            scenes_with_audio = generate_audio_for_scenes(
                scenes=scenes_with_images,
                tts_provider=video.tts_provider,
                tts_voice=video.tts_voice,
                tts_model=video.tts_model,
                video_id=video_id,
                progress_callback=lambda p: update_progress(video_id, 60 + (p * 0.2))
            )
            
            video.scenes = scenes_with_audio
            video.progress = 80
            db.commit()
            
            # Step 4: Render final video (20% of progress)
            logger.info(f"Rendering video {video_id}")
            video.status = VideoStatus.RENDERING
            db.commit()
            
            from app.services.video_service import render_video
            video_path, thumbnail_path, duration, file_size = render_video(
                scenes=scenes_with_audio,
                video_id=video_id,
                resolution=video.resolution,
                orientation=video.orientation,
                fps=video.fps,
                background_music=video.background_music,
                video_overlay=video.video_overlay,
                font=video.font,
                subtitle_style=video.subtitle_style,
                progress_callback=lambda p: update_progress(video_id, 80 + (p * 0.2))
            )
            
            # Update video with final details
            video.video_url = video_path
            video.thumbnail_url = thumbnail_path
            video.duration = duration
            video.file_size = file_size
            video.status = VideoStatus.COMPLETED
            video.progress = 100
            video.completed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Video generation completed for video_id={video_id}")
            
            # Update user statistics
            from app.models.user import User
            user = db.query(User).filter(User.id == video.user_id).first()
            if user:
                user.videos_generated += 1
                user.total_video_duration += duration
                db.commit()
            
            return {"status": "completed", "video_id": video_id}
            
        except Exception as e:
            logger.error(f"Error generating video {video_id}: {e}", exc_info=True)
            
            # Update video status to failed
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = VideoStatus.FAILED
                video.error_message = str(e)
                db.commit()
            
            # Re-raise for Celery to mark task as failed
            raise


def update_progress(video_id: int, progress: float):
    """Update video generation progress."""
    with Session(sync_engine) as db:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.progress = min(progress, 100)
            db.commit()

