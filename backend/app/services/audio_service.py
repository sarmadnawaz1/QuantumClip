"""Service for generating audio/TTS from text."""

import os
import logging
import time
from typing import List, Dict, Callable, Optional

logger = logging.getLogger(__name__)


def generate_audio_for_scenes(
    scenes: List[Dict],
    tts_provider: str = "edge",
    tts_voice: Optional[str] = None,
    tts_model: Optional[str] = None,
    video_id: int = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> List[Dict]:
    """
    Generate audio for all scenes using TTS.
    
    Args:
        scenes: List of scene dictionaries
        tts_provider: TTS provider (edge, elevenlabs, fish)
        tts_voice: Voice to use
        tts_model: Model to use (if applicable)
        video_id: Video ID for file naming
        progress_callback: Callback for progress updates
        
    Returns:
        List of scenes with audio URLs and durations
    """
    total_scenes = len(scenes)
    logger.info(f"[VIDEO {video_id}] Starting audio generation for {total_scenes} scenes using {tts_provider}")
    
    for idx, scene in enumerate(scenes):
        scene_num = scene.get('scene_number', idx + 1)
        scene_text = scene.get("text", "")
        
        if not scene_text or not scene_text.strip():
            logger.warning(f"[VIDEO {video_id}] Scene {scene_num} has empty text, skipping audio generation")
            scene["audio_url"] = None
            scene["duration"] = 2.0  # Default 2 seconds
            continue
        
        try:
            logger.info(f"[VIDEO {video_id}] Generating audio for scene {scene_num} ({idx + 1}/{total_scenes})")
            logger.debug(f"[VIDEO {video_id}] Scene {scene_num} text length: {len(scene_text)} chars")
            
            # Generate TTS audio with timeout handling
            start_time = time.time()
            
            if tts_provider == "edge":
                audio_path, duration = generate_edge_tts(
                    text=scene_text,
                    voice=tts_voice or "en-US-GuyNeural",
                    video_id=video_id,
                    scene_number=scene_num
                )
            elif tts_provider == "elevenlabs":
                audio_path, duration = generate_elevenlabs_tts(
                    text=scene_text,
                    voice=tts_voice,
                    model=tts_model,
                    video_id=video_id,
                    scene_number=scene_num
                )
            elif tts_provider == "fish":
                audio_path, duration = generate_fish_tts(
                    text=scene_text,
                    voice=tts_voice,
                    model=tts_model,
                    video_id=video_id,
                    scene_number=scene_num
                )
            else:
                raise ValueError(f"Unknown TTS provider: {tts_provider}")
            
            elapsed = time.time() - start_time
            scene["audio_url"] = audio_path
            scene["duration"] = duration
            logger.info(f"[VIDEO {video_id}] Audio generated for scene {scene_num}: {audio_path} ({duration}s) in {elapsed:.2f}s")
            
            # Update progress
            if progress_callback:
                progress = ((idx + 1) / total_scenes) * 100
                progress_callback(progress)
                
        except TimeoutError as e:
            logger.error(f"[VIDEO {video_id}] Timeout generating audio for scene {scene_num}: {e}")
            # Set default audio and duration if audio generation times out
            scene["audio_url"] = None
            scene["duration"] = len(scene_text) / 12.5  # Rough estimate: 12.5 chars per second
            logger.warning(f"[VIDEO {video_id}] Scene {scene_num} will render without audio due to timeout")
        except Exception as e:
            logger.error(f"[VIDEO {video_id}] Error generating audio for scene {scene_num}: {e}", exc_info=True)
            # Clean up any empty audio files that might have been created
            audio_filename = f"video_{video_id}_scene_{scene_num}.mp3"
            audio_path = os.path.join("uploads", audio_filename)
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                if file_size == 0:
                    try:
                        os.remove(audio_path)
                        logger.info(f"[VIDEO {video_id}] Removed empty audio file: {audio_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"[VIDEO {video_id}] Could not remove empty audio file: {cleanup_error}")
            # Set default audio and duration if audio generation fails
            scene["audio_url"] = None
            scene["duration"] = len(scene_text) / 12.5  # Rough estimate: 12.5 chars per second
            logger.warning(f"[VIDEO {video_id}] Scene {scene_num} will render without audio due to generation failure")
    
    logger.info(f"[VIDEO {video_id}] Completed audio generation for {total_scenes} scenes")
    
    return scenes


def generate_edge_tts(text: str, voice: str, video_id: int, scene_number: int) -> tuple:
    """Generate audio using Edge TTS with timeout."""
    import edge_tts
    import asyncio
    from pydub import AudioSegment
    import concurrent.futures
    import threading
    import signal
    
    if not text or not text.strip():
        raise ValueError(f"Empty text provided for scene {scene_number}")
    
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    audio_filename = f"video_{video_id}_scene_{scene_number}.mp3"
    audio_path = os.path.join(upload_dir, audio_filename)
    
    # Remove existing file if it exists (in case of previous failed attempt)
    if os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except Exception as e:
            logger.warning(f"Could not remove existing audio file: {e}")
    
    # Generate TTS with timeout
    async def _generate():
        try:
            logger.info(f"[VIDEO {video_id}] Starting Edge TTS for scene {scene_number} (voice: {voice}, text length: {len(text)})")
            communicate = edge_tts.Communicate(text, voice)
            await asyncio.wait_for(communicate.save(audio_path), timeout=60.0)  # 60 second timeout
            logger.info(f"[VIDEO {video_id}] Edge TTS completed for scene {scene_number}")
        except asyncio.TimeoutError:
            logger.error(f"[VIDEO {video_id}] Edge TTS timeout for scene {scene_number} after 60 seconds")
            # Remove empty file if it was created
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass
            raise TimeoutError(f"Edge TTS generation timed out after 60 seconds for scene {scene_number}")
        except Exception as e:
            logger.error(f"[VIDEO {video_id}] Edge TTS generation failed for scene {scene_number}: {e}", exc_info=True)
            # Remove empty file if it was created
            if os.path.exists(audio_path) and os.path.getsize(audio_path) == 0:
                try:
                    os.remove(audio_path)
                except:
                    pass
            raise
    
    # Check if we're already in an event loop
    try:
        loop = asyncio.get_running_loop()
        # We're in an event loop, run in a separate thread to avoid conflicts
        logger.info(f"[VIDEO {video_id}] Running Edge TTS in separate thread for scene {scene_number}")
        
        def run_in_thread():
            # Create a new event loop in this thread
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(_generate())
            finally:
                new_loop.close()
        
        # Use ThreadPoolExecutor with timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_thread)
            try:
                # Wait for completion with timeout (70 seconds total - 60 for TTS + 10 buffer)
                future.result(timeout=70.0)
            except concurrent.futures.TimeoutError:
                logger.error(f"[VIDEO {video_id}] Thread execution timeout for scene {scene_number}")
                # Try to clean up
                if os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except:
                        pass
                raise TimeoutError(f"Audio generation thread timed out for scene {scene_number}")
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        logger.info(f"[VIDEO {video_id}] Running Edge TTS with asyncio.run() for scene {scene_number}")
        try:
            asyncio.run(_generate())
        except Exception as e:
            logger.error(f"[VIDEO {video_id}] Failed to generate Edge TTS audio: {e}", exc_info=True)
            # Clean up empty file if it exists
            if os.path.exists(audio_path) and os.path.getsize(audio_path) == 0:
                try:
                    os.remove(audio_path)
                except:
                    pass
            raise
    except Exception as e:
        logger.error(f"[VIDEO {video_id}] Failed to generate Edge TTS audio: {e}", exc_info=True)
        # Clean up empty file if it exists
        if os.path.exists(audio_path) and os.path.getsize(audio_path) == 0:
            try:
                os.remove(audio_path)
            except:
                pass
        raise
    
    # Verify file was created and has content
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file was not created: {audio_path}")
    
    file_size = os.path.getsize(audio_path)
    if file_size == 0:
        os.remove(audio_path)
        raise ValueError(f"Audio file is empty (0 bytes): {audio_path}")
    
    logger.info(f"Audio file created: {audio_path} ({file_size} bytes)")
    
    # Get duration - use simple estimation if ffprobe is not available
    try:
        audio = AudioSegment.from_mp3(audio_path)
        duration = len(audio) / 1000.0  # Convert to seconds
        if duration <= 0:
            raise ValueError(f"Invalid audio duration: {duration}")
    except Exception as e:
        logger.warning(f"Could not get exact duration: {e}")
        # Estimate duration: ~150 words per minute, ~5 chars per word = 750 chars/min = 12.5 chars/sec
        duration = max(len(text) / 12.5, 2.0)  # Minimum 2 seconds
        logger.info(f"Using estimated duration: {duration}s for {len(text)} chars")
    
    return f"/uploads/{audio_filename}", duration


def generate_elevenlabs_tts(text: str, voice: Optional[str], model: Optional[str], 
                            video_id: int, scene_number: int) -> tuple:
    """Generate audio using ElevenLabs."""
    from elevenlabs.client import ElevenLabs
    from elevenlabs import save
    from pydub import AudioSegment
    from app.core.config import settings
    
    client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    audio_filename = f"video_{video_id}_scene_{scene_number}.mp3"
    audio_path = os.path.join(upload_dir, audio_filename)
    
    # Generate TTS
    audio = client.generate(
        text=text,
        voice=voice or "Rachel",
        model=model or "eleven_turbo_v2_5"
    )
    
    save(audio, audio_path)
    
    # Get duration
    audio_segment = AudioSegment.from_mp3(audio_path)
    duration = len(audio_segment) / 1000.0
    
    return f"/uploads/{audio_filename}", duration


def generate_fish_tts(text: str, voice: Optional[str], model: Optional[str],
                     video_id: int, scene_number: int) -> tuple:
    """Generate audio using Fish Audio."""
    from fish_audio_sdk import Session, TTSRequest
    from pydub import AudioSegment
    from app.core.config import settings
    
    session = Session(settings.fish_audio_api_key)
    
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    audio_filename = f"video_{video_id}_scene_{scene_number}.mp3"
    audio_path = os.path.join(upload_dir, audio_filename)
    
    # Generate TTS
    request = TTSRequest(
        text=text,
        reference_id=voice or "default",
        model=model or "speech-1.6"
    )
    
    with open(audio_path, 'wb') as f:
        for chunk in session.tts(request):
            f.write(chunk)
    
    # Get duration
    audio_segment = AudioSegment.from_file(audio_path)
    duration = len(audio_segment) / 1000.0
    
    return f"/uploads/{audio_filename}", duration

