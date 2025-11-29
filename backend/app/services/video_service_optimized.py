"""
Optimized video rendering service with scene-based rendering and ffmpeg concat.

This module provides an optimized rendering pipeline that:
1. Renders each scene separately to temporary files
2. Uses ffmpeg concat for fast final video assembly
3. Includes comprehensive timing and logging
4. Supports rendering presets (Fast/Quality)
"""

import os
import logging
import time
import subprocess
from typing import List, Dict, Callable, Optional, Tuple
from pathlib import Path

from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
from PIL import Image

from app.services.rendering_presets import get_preset, RenderingPreset
from app.services.scene_renderer import render_scene_clip, concatenate_scenes_with_ffmpeg

logger = logging.getLogger(__name__)


def render_video_optimized(
    scenes: List[Dict],
    video_id: int,
    resolution: str = "1080p",
    orientation: str = "portrait",
    fps: int = 30,
    background_music: Optional[str] = None,
    video_overlay: Optional[str] = None,
    font: Optional[str] = None,
    subtitle_style: Optional[Dict] = None,
    transition_type: str = "none",
    transition_duration: float = 0.5,
    image_animation: Optional[str] = None,
    image_animation_intensity: float = 1.2,
    rendering_preset: str = "fast",
    progress_callback: Optional[Callable[[float, str], None]] = None,
    use_legacy_renderer: bool = False,
) -> Tuple[str, str, int, int]:
    """
    Optimized video rendering using scene-based approach and ffmpeg concat.
    
    This function:
    1. Renders each scene to a temporary video file
    2. Concatenates scenes using ffmpeg (much faster than MoviePy)
    3. Adds background music and overlays if specified
    4. Generates thumbnail
    
    Args:
        scenes: List of scene dictionaries with images and audio
        video_id: Video ID for file naming
        resolution: Video resolution (720p, 1080p, 2K, 4K)
        orientation: Video orientation (portrait, landscape)
        fps: Frames per second
        background_music: Background music file name
        video_overlay: Video overlay file name
        font: Font for subtitles
        subtitle_style: Subtitle styling options
        transition_type: Transition type between scenes
        transition_duration: Transition duration in seconds
        image_animation: Animation type to apply to images
        image_animation_intensity: Animation intensity
        rendering_preset: Rendering preset ('fast' or 'quality')
        progress_callback: Callback for progress updates (progress: float, stage: str)
        
    Returns:
        Tuple of (video_path, thumbnail_path, duration_seconds, file_size_bytes)
    """
    # Check if ffmpeg is available (required for optimized rendering)
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning(f"[VIDEO {video_id}] FFmpeg not available, falling back to legacy renderer")
        use_legacy_renderer = True
    
    if use_legacy_renderer:
        # Fallback to original renderer if ffmpeg is not available
        logger.info(f"[VIDEO {video_id}] Using legacy renderer (ffmpeg not available)")
        from app.services.video_service import render_video
        return render_video(
            scenes=scenes,
            video_id=video_id,
            resolution=resolution,
            orientation=orientation,
            fps=fps,
            background_music=background_music,
            video_overlay=video_overlay,
            font=font,
            subtitle_style=subtitle_style,
            transition_type=transition_type,
            transition_duration=transition_duration,
            image_animation=image_animation,
            image_animation_intensity=image_animation_intensity,
            progress_callback=lambda p: progress_callback(p * 0.2, "Rendering") if progress_callback else None,
        )
    
    pipeline_start_time = time.time()
    logger.info(f"[VIDEO {video_id}] ===== Starting optimized video rendering =====")
    logger.info(f"[VIDEO {video_id}] Scenes: {len(scenes)}, Resolution: {resolution}, Orientation: {orientation}, FPS: {fps}")
    logger.info(f"[VIDEO {video_id}] Rendering preset: {rendering_preset}")
    
    # Get rendering preset
    preset = get_preset(rendering_preset)
    logger.info(f"[VIDEO {video_id}] Using preset: {preset.name} (CRF={preset.crf}, preset={preset.preset})")
    
    # Get dimensions
    resolution_map = {
        "720p": {"portrait": (720, 1280), "landscape": (1280, 720)},
        "1080p": {"portrait": (1080, 1920), "landscape": (1920, 1080)},
        "2K": {"portrait": (1440, 2560), "landscape": (2560, 1440)},
        "4K": {"portrait": (2160, 3840), "landscape": (3840, 2160)},
    }
    
    width, height = resolution_map.get(resolution, {}).get(orientation, (1080, 1920))
    logger.info(f"[VIDEO {video_id}] Target dimensions: {width}x{height}")
    
    # Setup directories
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Stage 1: Render individual scenes (0-70% of progress)
    scene_start_time = time.time()
    logger.info(f"[VIDEO {video_id}] === Stage 1: Rendering {len(scenes)} scenes ===")
    
    if progress_callback:
        progress_callback(0.0, "Rendering scenes")
    
    scene_paths: List[str] = []
    scene_durations: List[float] = []
    
    for idx, scene in enumerate(scenes):
        scene_render_start = time.time()
        
        try:
            scene_path, duration = render_scene_clip(
                scene=scene,
                scene_index=idx,
                video_id=video_id,
                width=width,
                height=height,
                fps=fps,
                upload_dir=upload_dir,
                font=font,
                subtitle_style=subtitle_style,
                image_animation=image_animation,
                image_animation_intensity=image_animation_intensity,
                preset=preset,
            )
            
            scene_paths.append(scene_path)
            scene_durations.append(duration)
            
            scene_render_elapsed = time.time() - scene_render_start
            logger.info(f"[VIDEO {video_id}] Scene {idx + 1}/{len(scenes)}: {scene_render_elapsed:.2f}s")
            
            # Update progress (0-70% for scene rendering)
            if progress_callback:
                scene_progress = ((idx + 1) / len(scenes)) * 70.0
                progress_callback(scene_progress, f"Rendering scene {idx + 1}/{len(scenes)}")
                
        except Exception as e:
            logger.error(f"[VIDEO {video_id}] Failed to render scene {idx + 1}: {e}", exc_info=True)
            raise
    
    scene_elapsed = time.time() - scene_start_time
    total_scene_duration = sum(scene_durations)
    logger.info(f"[VIDEO {video_id}] === Stage 1 complete: {len(scene_paths)} scenes in {scene_elapsed:.2f}s (total duration: {total_scene_duration:.2f}s) ===")
    
    if not scene_paths:
        raise ValueError("No scenes were successfully rendered")
    
    # Stage 2: Concatenate scenes with ffmpeg (70-85% of progress)
    concat_start_time = time.time()
    logger.info(f"[VIDEO {video_id}] === Stage 2: Concatenating scenes with ffmpeg ===")
    
    if progress_callback:
        progress_callback(70.0, "Merging scenes")
    
    # Temporary concatenated video (before music/overlay)
    temp_concat_path = os.path.join(upload_dir, f"video_{video_id}_concat_temp.mp4")
    
    concatenate_scenes_with_ffmpeg(
        scene_paths=scene_paths,
        output_path=temp_concat_path,
        transition_type=transition_type,
        transition_duration=transition_duration,
        width=width,
        height=height,
        fps=fps,
        preset=preset,
        progress_callback=lambda p: progress_callback(70.0 + (p * 0.15), "Merging scenes") if progress_callback else None,
    )
    
    concat_elapsed = time.time() - concat_start_time
    logger.info(f"[VIDEO {video_id}] === Stage 2 complete: Concatenation in {concat_elapsed:.2f}s ===")
    
    # Stage 3: Add background music and overlays using ffmpeg (85-95% of progress)
    # This is MUCH faster than using MoviePy for re-encoding
    postprocess_start_time = time.time()
    logger.info(f"[VIDEO {video_id}] === Stage 3: Adding background music and overlays with ffmpeg ===")
    
    if progress_callback:
        progress_callback(85.0, "Adding audio and effects")
    
    final_video_path = os.path.join(upload_dir, f"video_{video_id}_final.mp4")
    
    # Use ffmpeg directly for post-processing - 10-100x faster than MoviePy
    try:
        # Get video duration first (needed for music looping)
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            temp_concat_path
        ]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
        video_duration = float(duration_result.stdout.strip())
        logger.info(f"[VIDEO {video_id}] Video duration: {video_duration:.2f}s")
        
        # Build ffmpeg command - handle cases separately for simplicity
        ffmpeg_cmd = ['ffmpeg', '-y', '-i', temp_concat_path]
        
        bg_music_path = None
        overlay_path = None
        
        # Check for background music
        if background_music and os.path.exists(f"music/{background_music}"):
            bg_music_path = f"music/{background_music}"
            ffmpeg_cmd.extend(['-stream_loop', '-1', '-i', bg_music_path])
            logger.info(f"[VIDEO {video_id}] Adding background music: {bg_music_path}")
        
        # Check for video overlay
        if video_overlay and os.path.exists(f"overlays/{video_overlay}"):
            overlay_path = f"overlays/{video_overlay}"
            ffmpeg_cmd.extend(['-stream_loop', '-1', '-i', overlay_path])
            logger.info(f"[VIDEO {video_id}] Adding video overlay: {overlay_path}")
        
        # Build filter_complex
        filter_parts = []
        
        # Video processing
        if overlay_path:
            # Scale overlay and composite with main video
            overlay_idx = 1 if not bg_music_path else 2
            filter_parts.append(f"[{overlay_idx}:v]scale={width}:{height}[ov]")
            filter_parts.append("[0:v][ov]overlay=0:0:format=auto[v]")
        else:
            filter_parts.append("[0:v]copy[v]")
        
        # Audio processing
        if bg_music_path:
            music_idx = 1
            # Reduce volume and mix with original
            filter_parts.append(f"[{music_idx}:a]volume=0.3[bg]")
            filter_parts.append("[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]")
        else:
            filter_parts.append("[0:a]copy[a]")
        
        # Apply filter_complex
        if filter_parts:
            ffmpeg_cmd.extend(['-filter_complex', ';'.join(filter_parts)])
            ffmpeg_cmd.extend(['-map', '[v]', '-map', '[a]'])
        else:
            # No filters needed, just copy streams
            ffmpeg_cmd.extend(['-c', 'copy'])
        
        # Encoding settings (only if we're not using stream copy)
        if filter_parts:
            ffmpeg_cmd.extend([
                '-c:v', 'libx264',
                '-preset', preset.preset,
                '-crf', str(preset.crf),
                '-r', str(fps),
                '-c:a', 'aac',
                '-b:a', '192k',
                '-movflags', '+faststart',
                '-pix_fmt', 'yuv420p',
            ])
            # Add preset extra args
            ffmpeg_cmd.extend(preset.extra_args)
        
        # Output
        ffmpeg_cmd.append(final_video_path)
        
        if progress_callback:
            progress_callback(90.0, "Encoding final video")
        
        encode_start = time.time()
        logger.debug(f"[VIDEO {video_id}] Running ffmpeg post-processing")
        
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            check=False,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            logger.error(f"[VIDEO {video_id}] FFmpeg post-processing failed (exit {result.returncode})")
            logger.error(f"[VIDEO {video_id}] Command: {' '.join(ffmpeg_cmd)}")
            logger.error(f"[VIDEO {video_id}] Error: {result.stderr[-1000:]}")  # Last 1000 chars
            raise subprocess.CalledProcessError(result.returncode, ffmpeg_cmd, result.stdout, result.stderr)
        
        encode_elapsed = time.time() - encode_start
        logger.info(f"[VIDEO {video_id}] Final encoding completed in {encode_elapsed:.2f}s (ffmpeg)")
        
    except Exception as e:
        logger.error(f"[VIDEO {video_id}] Error in ffmpeg post-processing: {e}", exc_info=True)
        # Fallback: if ffmpeg fails, try MoviePy (slower but more compatible)
        logger.warning(f"[VIDEO {video_id}] Falling back to MoviePy for post-processing...")
        working_video = VideoFileClip(temp_concat_path)
        try:
            # Add background music
            if background_music and os.path.exists(f"music/{background_music}"):
                bg_music = AudioFileClip(f"music/{background_music}")
                bg_music = bg_music.volumex(0.3)
                if bg_music.duration < working_video.duration:
                    bg_music = bg_music.audio_loop(duration=working_video.duration)
                else:
                    bg_music = bg_music.subclip(0, working_video.duration)
                if working_video.audio:
                    final_audio = CompositeAudioClip([working_video.audio, bg_music])
                    working_video = working_video.set_audio(final_audio)
                else:
                    working_video = working_video.set_audio(bg_music)
            
            # Add video overlay
            if video_overlay and os.path.exists(f"overlays/{video_overlay}"):
                from moviepy.editor import VideoFileClip as OverlayClip, CompositeVideoClip
                overlay = OverlayClip(f"overlays/{video_overlay}")
                overlay = overlay.resize((width, height))
                if overlay.duration < working_video.duration:
                    overlay = overlay.loop(duration=working_video.duration)
                else:
                    overlay = overlay.subclip(0, working_video.duration)
                overlay = overlay.set_opacity(0.5)
                working_video = CompositeVideoClip([working_video, overlay])
            
            # Write with MoviePy (fallback)
            working_video.write_videofile(
                final_video_path,
                fps=fps,
                codec='libx264',
                audio_codec='aac',
                threads=max(1, os.cpu_count() or 4),
                preset=preset.preset,
                verbose=False,
                logger=None
            )
        finally:
            working_video.close()
    
    finally:
        # Clean up temp concat file
        if os.path.exists(temp_concat_path):
            try:
                os.remove(temp_concat_path)
            except Exception as e:
                logger.warning(f"[VIDEO {video_id}] Could not remove temp concat file: {e}")
    
    postprocess_elapsed = time.time() - postprocess_start_time
    logger.info(f"[VIDEO {video_id}] === Stage 3 complete: Post-processing in {postprocess_elapsed:.2f}s ===")
    
    # Stage 4: Generate thumbnail (95-100% of progress)
    thumbnail_start_time = time.time()
    logger.info(f"[VIDEO {video_id}] === Stage 4: Generating thumbnail ===")
    
    if progress_callback:
        progress_callback(95.0, "Generating thumbnail")
    
    thumbnail_filename = f"video_{video_id}_thumb.jpg"
    thumbnail_path = os.path.join(upload_dir, thumbnail_filename)
    
    try:
        thumb_video = VideoFileClip(final_video_path)
        frame = thumb_video.get_frame(0)
        Image.fromarray(frame).save(thumbnail_path, quality=85)
        thumb_video.close()
    except Exception as e:
        logger.error(f"[VIDEO {video_id}] Error generating thumbnail: {e}", exc_info=True)
        thumbnail_path = None
    
    thumbnail_elapsed = time.time() - thumbnail_start_time
    logger.info(f"[VIDEO {video_id}] === Stage 4 complete: Thumbnail in {thumbnail_elapsed:.2f}s ===")
    
    # Get final video stats
    file_size = os.path.getsize(final_video_path)
    total_duration = int(sum(scene_durations))
    
    # Clean up scene clip files
    for scene_path in scene_paths:
        try:
            if os.path.exists(scene_path):
                os.remove(scene_path)
        except Exception as e:
            logger.warning(f"[VIDEO {video_id}] Could not remove scene file {scene_path}: {e}")
    
    # Final summary
    pipeline_elapsed = time.time() - pipeline_start_time
    logger.info(f"[VIDEO {video_id}] ===== Rendering complete =====")
    logger.info(f"[VIDEO {video_id}] Total time: {pipeline_elapsed:.2f}s")
    logger.info(f"[VIDEO {video_id}] Breakdown:")
    logger.info(f"[VIDEO {video_id}]   - Scene rendering: {scene_elapsed:.2f}s ({scene_elapsed/pipeline_elapsed*100:.1f}%)")
    logger.info(f"[VIDEO {video_id}]   - Concatenation: {concat_elapsed:.2f}s ({concat_elapsed/pipeline_elapsed*100:.1f}%)")
    logger.info(f"[VIDEO {video_id}]   - Post-processing: {postprocess_elapsed:.2f}s ({postprocess_elapsed/pipeline_elapsed*100:.1f}%)")
    logger.info(f"[VIDEO {video_id}]   - Thumbnail: {thumbnail_elapsed:.2f}s ({thumbnail_elapsed/pipeline_elapsed*100:.1f}%)")
    logger.info(f"[VIDEO {video_id}] Output: {final_video_path} ({file_size / 1024 / 1024:.2f} MB, {total_duration}s)")
    
    video_url = f"/uploads/{os.path.basename(final_video_path)}"
    thumbnail_url = f"/uploads/{thumbnail_filename}" if thumbnail_path else None
    
    return video_url, thumbnail_url, total_duration, file_size

