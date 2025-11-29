"""
Scene-based video rendering with ffmpeg optimization.

This module handles rendering individual scenes and concatenating them
using ffmpeg for better performance than building one large MoviePy timeline.
"""

import os
import logging
import subprocess
import tempfile
from typing import List, Dict, Callable, Optional, Tuple
from pathlib import Path
import time

from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, VideoClip
from moviepy.video.fx.all import fadein as vfx_fadein, fadeout as vfx_fadeout
from PIL import Image
import numpy as np

from app.services.rendering_presets import get_preset, RenderingPreset
# Import from video_service - handle circular import gracefully
def _import_video_service_functions():
    """Lazy import to avoid circular dependencies."""
    from app.services.video_service import (
        apply_image_animation,
        build_subtitle_clips,
        normalize_transition_type,
    )
    return {
        'apply_image_animation': apply_image_animation,
        'build_subtitle_clips': build_subtitle_clips,
        'normalize_transition_type': normalize_transition_type,
    }

# Lazy load these functions
_video_service_funcs = None

def _get_video_service_func(name: str):
    """Get a function from video_service module."""
    global _video_service_funcs
    if _video_service_funcs is None:
        _video_service_funcs = _import_video_service_functions()
    return _video_service_funcs.get(name)

logger = logging.getLogger(__name__)


def render_scene_clip(
    scene: Dict,
    scene_index: int,
    video_id: int,
    width: int,
    height: int,
    fps: int,
    upload_dir: str,
    font: Optional[str] = None,
    subtitle_style: Optional[Dict] = None,
    image_animation: Optional[str] = None,
    image_animation_intensity: float = 1.2,
    preset: RenderingPreset = None,
) -> Tuple[str, float]:
    """
    Render a single scene to a temporary video file.
    
    Args:
        scene: Scene dictionary with image_url, audio_url, text, duration
        scene_index: Zero-based index of the scene
        video_id: Video ID for file naming
        width: Video width
        height: Video height
        fps: Frames per second
        upload_dir: Directory to save temporary scene files
        font: Optional font path for subtitles
        subtitle_style: Subtitle styling options
        image_animation: Animation type to apply
        image_animation_intensity: Animation intensity
        preset: Rendering preset to use
        
    Returns:
        Tuple of (scene_video_path, duration)
        
    Raises:
        Exception: If scene rendering fails
    """
    start_time = time.time()
    logger.info(f"[VIDEO {video_id}] Starting scene {scene_index + 1} rendering")
    
    if preset is None:
        preset = get_preset("fast")
    
    # Get scene data
    image_url = scene.get("image_url")
    audio_url = scene.get("audio_url")
    scene_text = scene.get("text", "")
    duration = scene.get("duration", 3.0)
    
    if not image_url:
        raise ValueError(f"Scene {scene_index + 1} missing image_url")
    
    # Load image
    image_path = image_url.replace("/uploads/", "uploads/")
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Pre-process image to exact dimensions
    from PIL import Image as PILImage
    pil_img = PILImage.open(image_path)
    img_width, img_height = pil_img.size
    
    if img_width != width or img_height != height:
        target_aspect = width / height
        img_aspect = img_width / img_height
        
        if abs(img_aspect - target_aspect) > 0.01:
            if img_aspect > target_aspect:
                new_width = int(img_height * target_aspect)
                left = (img_width - new_width) // 2
                pil_img = pil_img.crop((left, 0, left + new_width, img_height))
            else:
                new_height = int(img_width / target_aspect)
                top = (img_height - new_height) // 2
                pil_img = pil_img.crop((0, top, img_width, top + new_height))
        
        pil_img = pil_img.resize((width, height), PILImage.Resampling.LANCZOS)
        temp_image_path = os.path.join(upload_dir, f"video_{video_id}_scene_{scene_index + 1}_resized.png")
        pil_img.save(temp_image_path, 'PNG')
        image_path = temp_image_path
    
    # Load audio to get actual duration
    audio_clip = None
    if audio_url:
        audio_path = audio_url.replace("/uploads/", "uploads/")
        if os.path.exists(audio_path):
            try:
                audio_clip = AudioFileClip(audio_path)
                duration = audio_clip.duration
            except Exception as e:
                logger.warning(f"Could not load audio for scene {scene_index + 1}: {e}")
    
    # Create image clip
    img_clip = ImageClip(image_path, duration=duration)
    img_clip = img_clip.set_fps(fps)
    
    # Apply animation
    if image_animation and image_animation != "none":
        apply_anim = _get_video_service_func('apply_image_animation')
        if apply_anim:
            img_clip = apply_anim(
                img_clip=img_clip,
                animation_type=image_animation,
                duration=duration,
                width=width,
                height=height,
                intensity=image_animation_intensity
            )
    
    # Add audio
    if audio_clip:
        img_clip = img_clip.set_audio(audio_clip)
    
    # Add subtitles
    subtitles_enabled = True
    if subtitle_style and isinstance(subtitle_style, dict):
        subtitles_enabled = subtitle_style.get("enabled", True)
    
    if scene_text and subtitle_style and subtitles_enabled:
        try:
            font_size = subtitle_style.get("font_size", 60)
            position = subtitle_style.get("position", "bottom")
            
            text_color_raw = subtitle_style.get("text_color", "#FFFFFF")
            if isinstance(text_color_raw, str):
                hex_color = text_color_raw.lstrip('#')
                text_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            elif isinstance(text_color_raw, (list, tuple)):
                text_color = tuple(text_color_raw)
            else:
                text_color = (255, 255, 255)
            
            bg_opacity = subtitle_style.get("bg_opacity", 180)
            outline_width = subtitle_style.get("outline_width", 3)
            
            font_path = None
            if font and os.path.exists(f"font/{font}"):
                font_path = f"font/{font}"
            
            build_subtitles = _get_video_service_func('build_subtitle_clips')
            if build_subtitles:
                subtitle_clips = build_subtitles(
                    text=scene_text,
                    width=width,
                    height=height,
                    duration=duration,
                    fps=fps,
                    font_path=font_path,
                    font_size=font_size,
                    position=position,
                    text_color=text_color,
                    bg_opacity=bg_opacity,
                    outline_width=outline_width
                )
            else:
                subtitle_clips = []
            
            if subtitle_clips:
                img_clip = CompositeVideoClip([img_clip, *subtitle_clips], size=(width, height))
        except Exception as e:
            logger.error(f"Error adding subtitles to scene {scene_index + 1}: {e}", exc_info=True)
    
    # Render scene to temporary file
    scene_filename = f"video_{video_id}_scene_{scene_index + 1}_clip.mp4"
    scene_path = os.path.join(upload_dir, scene_filename)
    
    # Use MoviePy to render the scene clip (small, fast)
    # For scene clips, we use faster settings since they're temporary
    cpu_threads = max(1, os.cpu_count() or 4)
    
    try:
        img_clip.write_videofile(
            scene_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac' if audio_clip else None,
            threads=cpu_threads,
            preset='veryfast',  # Fast for scene clips
            bitrate='4000k',  # Reasonable bitrate for scene clips
            verbose=False,
            logger=None
        )
        
        elapsed = time.time() - start_time
        logger.info(f"[VIDEO {video_id}] Scene {scene_index + 1} rendered in {elapsed:.2f}s ({duration:.2f}s duration)")
        
        return scene_path, duration
        
    finally:
        # Clean up
        img_clip.close()
        if audio_clip:
            audio_clip.close()


def concatenate_scenes_with_ffmpeg(
    scene_paths: List[str],
    output_path: str,
    transition_type: str = "none",
    transition_duration: float = 0.5,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    preset: Optional[RenderingPreset] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> None:
    """
    Concatenate scene clips using ffmpeg for optimal performance.
    
    For transitions, we handle them by:
    - crossfade: Use ffmpeg's xfade filter
    - fade_black: Use ffmpeg's fade filters
    - Other transitions: Pre-render transition clips and insert them
    
    Args:
        scene_paths: List of paths to scene video files
        output_path: Final output video path
        transition_type: Type of transition between scenes
        transition_duration: Duration of transitions
        width: Video width
        height: Video height
        fps: Frames per second
        preset: Rendering preset
        progress_callback: Optional callback for progress updates
        
    Raises:
        subprocess.CalledProcessError: If ffmpeg fails
    """
    if not scene_paths:
        raise ValueError("No scene paths provided")
    
    if preset is None:
        preset = get_preset("fast")
    
    start_time = time.time()
    logger.info(f"Concatenating {len(scene_paths)} scenes with ffmpeg")
    
    normalize_trans = _get_video_service_func('normalize_transition_type')
    if normalize_trans:
        transition_effect = normalize_trans(transition_type)
    else:
        transition_effect = transition_type.lower() if transition_type else "none"
    
    # For simple cases (no transitions or crossfade), use ffmpeg concat demuxer
    if transition_effect == "none" or (transition_effect == "crossfade" and transition_duration == 0):
        # Simple concatenation - fastest method
        concat_file = output_path.replace('.mp4', '_concat.txt')
        try:
            with open(concat_file, 'w') as f:
                for scene_path in scene_paths:
                    f.write(f"file '{os.path.abspath(scene_path)}'\n")
            
            # Use ffmpeg concat demuxer
            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',  # Stream copy - no re-encoding!
                output_path
            ]
            
            if progress_callback:
                progress_callback(10.0)
            
            logger.debug(f"Running ffmpeg concat: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,  # Don't auto-raise, check returncode manually
                stderr=subprocess.PIPE
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg concat failed (exit {result.returncode}): {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
            
            elapsed = time.time() - start_time
            logger.info(f"Scene concatenation completed in {elapsed:.2f}s (stream copy)")
            
            if progress_callback:
                progress_callback(100.0)
                
        finally:
            if os.path.exists(concat_file):
                os.remove(concat_file)
    
    else:
        # For transitions, we need to re-encode
        # Build complex filter or use MoviePy for transition clips
        # For now, use a simpler approach: concatenate with crossfade via ffmpeg filter
        logger.warning(f"Complex transitions ({transition_effect}) may require MoviePy - using simple concat")
        
        # Fallback to simple concat for now
        # TODO: Implement proper transition handling with ffmpeg filters
        concat_file = output_path.replace('.mp4', '_concat.txt')
        try:
            with open(concat_file, 'w') as f:
                for scene_path in scene_paths:
                    f.write(f"file '{os.path.abspath(scene_path)}'\n")
            
            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-preset', preset.preset,
                '-crf', str(preset.crf),
                '-c:a', 'aac',
                '-b:a', '192k',
                output_path
            ]
            
            if progress_callback:
                progress_callback(10.0)
            
            logger.debug(f"Running ffmpeg concat with re-encode: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                stderr=subprocess.PIPE
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg concat with transitions failed (exit {result.returncode}): {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
            
            elapsed = time.time() - start_time
            logger.info(f"Scene concatenation with transitions completed in {elapsed:.2f}s (re-encoded)")
            
            if progress_callback:
                progress_callback(100.0)
                
        finally:
            if os.path.exists(concat_file):
                os.remove(concat_file)

