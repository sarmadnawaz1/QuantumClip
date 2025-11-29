"""Service for rendering final video."""

import os
import logging
import re
import random
from typing import List, Dict, Callable, Optional, Tuple, Any
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip, 
    CompositeAudioClip, VideoFileClip, concatenate_videoclips,
    ColorClip
)
from moviepy.video.VideoClip import TextClip, VideoClip
from moviepy.video.fx.all import fadein as vfx_fadein, fadeout as vfx_fadeout
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

logger = logging.getLogger(__name__)

SUPPORTED_TRANSITIONS = {
    "none",
    "crossfade",
    "fade_black",
    "fade_white",
    "flash",
    "slide_left",
    "slide_right",
    "slide_up",
    "slide_down",
    "wipe_left",
    "wipe_right",
    "wipe_up",
    "wipe_down",
    "zoom_in",
    "zoom_out",
    "zoom_cross",
    "pixelate",
    "random",
    "mix"
}

TRANSITION_ALIASES = {
    "dissolve": "crossfade",
    "dreamy_dissolve": "crossfade",
    "smooth_dissolve": "crossfade",
    "soft_dissolve": "crossfade",
    "gentle_dissolve": "crossfade",
    "cinematic_crossfade": "crossfade",
    "cinematic_blackout": "fade_black",
    "dip_to_black": "fade_black",
    "dramatic_blackout": "fade_black",
    "fade_to_black": "fade_black",
    "dip_to_white": "fade_white",
    "fade_to_white": "fade_white",
    "flash_white": "flash",
    "flash_light": "flash",
    "slide_push_left": "slide_left",
    "push_left": "slide_left",
    "parallax_left": "slide_left",
    "slide_push_right": "slide_right",
    "push_right": "slide_right",
    "parallax_right": "slide_right",
    "slide_push_up": "slide_up",
    "push_up": "slide_up",
    "slide_push_down": "slide_down",
    "push_down": "slide_down",
    "wipe_soft_left": "wipe_left",
    "wipe_soft_right": "wipe_right",
    "wipe_soft_up": "wipe_up",
    "wipe_soft_down": "wipe_down",
    "pan_left": "wipe_left",
    "pan_right": "wipe_right",
    "pan_up": "wipe_up",
    "pan_down": "wipe_down",
    "zoom_in_slow": "zoom_in",
    "zoom_in_fast": "zoom_in",
    "zoom_out_slow": "zoom_out",
    "zoom_out_fast": "zoom_out",
    "cross_zoom": "zoom_cross",
    "zoom_blur": "zoom_cross",
    "pixelate_in": "pixelate",
    "pixelate_out": "pixelate",
    "random_mix": "random",
    "mix": "random",
    "shuffle": "random",
    "all": "random"
}

def normalize_transition_type(value: Optional[str]) -> str:
    if not value:
        return "none"
    key = value.lower()
    mapped = TRANSITION_ALIASES.get(key, key)
    return mapped if mapped in SUPPORTED_TRANSITIONS else "none"


def create_subtitle_image(
    text: str,
    width: int,
    height: int,
    font_path: Optional[str] = None,
    font_size: int = 60,
    position: str = "bottom",
    text_color: tuple = (255, 255, 255),
    bg_color: tuple = (0, 0, 0),
    bg_opacity: int = 180,
    outline_width: int = 3,
    outline_color: tuple = (0, 0, 0),
    padding: int = 20,
    force_single_line: bool = False
) -> np.ndarray:
    """
    Create a subtitle image overlay using PIL.
    
    Args:
        text: Subtitle text
        width: Image width
        height: Image height
        font_path: Path to TTF font file
        font_size: Font size
        position: "top", "center", or "bottom"
        text_color: RGB color tuple for text
        bg_color: RGB color tuple for background
        bg_opacity: Background opacity (0-255)
        outline_width: Width of text outline/stroke
        outline_color: RGB color tuple for outline
        padding: Padding around text
        
    Returns:
        NumPy array of RGBA image
    """
    # Create transparent image
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Load font
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            # Try default fonts
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                except:
                    font = ImageFont.load_default()
    except Exception as e:
        logger.warning(f"Could not load font: {e}, using default")
        font = ImageFont.load_default()
    
    cleaned_text = text.strip()
    lines: List[str] = []
    
    if not cleaned_text:
        return np.array(img)
    
    if force_single_line:
        lines = [cleaned_text]
    else:
        words = cleaned_text.split()
        current_line: List[str] = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
            
            if line_width > width - (padding * 4):
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
    
    # Calculate text dimensions
    line_heights = []
    max_width = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        line_heights.append(line_height)
        max_width = max(max_width, line_width)
    
    total_text_height = sum(line_heights) + (len(lines) - 1) * 10
    
    # Calculate vertical position
    if position == "top":
        y_start = padding * 2
    elif position == "center":
        y_start = (height - total_text_height) // 2
    else:  # bottom
        y_start = height - total_text_height - (padding * 3)
    
    # Draw background rectangle
    bg_height = total_text_height + (padding * 2)
    bg_y_start = y_start - padding
    
    # Create semi-transparent background
    bg_img = Image.new('RGBA', (width, bg_height), (*bg_color, bg_opacity))
    img.paste(bg_img, (0, bg_y_start), bg_img)
    
    # Draw text with outline
    y = y_start
    for line, line_height in zip(lines, line_heights):
        # Calculate x position for centered text
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2
        
        # Draw outline (stroke)
        if outline_width > 0:
            for adj_x in range(-outline_width, outline_width + 1):
                for adj_y in range(-outline_width, outline_width + 1):
                    if adj_x != 0 or adj_y != 0:
                        draw.text((x + adj_x, y + adj_y), line, font=font, fill=outline_color)
        
        # Draw main text
        draw.text((x, y), line, font=font, fill=text_color)
        
        y += line_height + 10
    
    # Convert to numpy array
    return np.array(img)


def split_subtitle_text(text: str, max_chars: int = 60) -> List[str]:
    """Split subtitle text into single-line chunks."""
    if not text:
        return []
    
    sentences = re.split(r"(?<=[.!?\u3002\uFF01\uFF1F])\s+", text.strip())
    chunks: List[str] = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        if len(sentence) <= max_chars:
            chunks.append(sentence)
            continue
        
        words = sentence.split()
        current: List[str] = []
        for word in words:
            tentative = ' '.join(current + [word]) if current else word
            if len(tentative) > max_chars and current:
                chunks.append(' '.join(current))
                current = [word]
            else:
                current.append(word)
        
        if current:
            chunks.append(' '.join(current))
    
    return chunks or [text.strip()]


def build_subtitle_clips(
    text: str,
    width: int,
    height: int,
    duration: float,
    fps: int,
    font_path: Optional[str],
    font_size: int,
    position: str,
    text_color: tuple,
    bg_opacity: int,
    outline_width: int
) -> List[ImageClip]:
    """Create sequential subtitle clips so only one line shows at a time."""
    segments = split_subtitle_text(text)
    if not segments:
        return []
    
    total_words = sum(len(segment.split()) for segment in segments) or 1
    elapsed = 0.0
    clips: List[ImageClip] = []
    
    for index, segment in enumerate(segments):
        word_count = max(len(segment.split()), 1)
        segment_duration = duration * word_count / total_words
        if index == len(segments) - 1:
            remaining = duration - elapsed
            if remaining > 0:
                segment_duration = remaining
        if segment_duration <= 0:
            continue
        
        subtitle_img = create_subtitle_image(
            text=segment,
            width=width,
            height=height,
            font_path=font_path,
            font_size=font_size,
            position=position,
            text_color=text_color,
            bg_opacity=bg_opacity,
            outline_width=outline_width,
            force_single_line=True
        )
        
        clip = ImageClip(subtitle_img).set_start(elapsed).set_duration(segment_duration).set_fps(fps)
        clips.append(clip)
        elapsed += segment_duration
    
    return clips


def _zoom_image_array(image_array: np.ndarray, scale: float, width: int, height: int) -> np.ndarray:
    scale = max(0.1, scale)
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    resized = Image.fromarray(image_array).resize((new_width, new_height), Image.Resampling.LANCZOS)
    resized_array = np.array(resized)

    if new_width >= width and new_height >= height:
        x0 = (new_width - width) // 2
        y0 = (new_height - height) // 2
        return resized_array[y0:y0 + height, x0:x0 + width]

    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    x0 = (width - new_width) // 2
    y0 = (height - new_height) // 2
    canvas[y0:y0 + new_height, x0:x0 + new_width] = resized_array
    return canvas


def apply_image_animation(
    img_clip: ImageClip,
    animation_type: str,
    duration: float,
    width: int,
    height: int,
    intensity: float = 1.2
) -> VideoClip:
    """
    Apply animation effect to a static image clip (Ken Burns effect and more).
    
    Args:
        img_clip: The ImageClip to animate
        animation_type: Type of animation (zoom_in, zoom_out, pan_left, pan_right, pan_up, pan_down, ken_burns, none)
        duration: Clip duration
        width: Video width
        height: Video height
        intensity: Animation intensity (1.0 = no zoom, 2.0 = 2x zoom)
        
    Returns:
        Animated VideoClip
    """
    if not animation_type or animation_type == "none":
        return img_clip
    
    animation_type = animation_type.lower()
    
    # Get base frame from the image clip
    base_frame = img_clip.get_frame(0)
    
    # Zoom In: Gradually zoom into the image
    if animation_type == "zoom_in":
        def make_frame(t):
            progress = min(t / duration, 1.0)
            scale = 1.0 + (intensity - 1.0) * progress
            return _zoom_image_array(base_frame, scale, width, height)
        return VideoClip(make_frame, duration=duration).set_fps(img_clip.fps)
    
    # Zoom Out: Start zoomed in, zoom out
    elif animation_type == "zoom_out":
        def make_frame(t):
            progress = min(t / duration, 1.0)
            scale = intensity - (intensity - 1.0) * progress
            return _zoom_image_array(base_frame, scale, width, height)
        return VideoClip(make_frame, duration=duration).set_fps(img_clip.fps)
    
    # Pan Left: Move image from right to left (show left side of image)
    elif animation_type == "pan_left":
        def make_frame(t):
            progress = min(t / duration, 1.0)
            # Scale image up slightly to allow panning
            scale = 1.0 + 0.1 * (intensity - 1.0)
            scaled = _zoom_image_array(base_frame, scale, width, height)
            h, w = scaled.shape[:2]
            # Pan from right edge to left edge
            pan_range = max(0, w - width)
            x_start = int(pan_range * (1 - progress))
            return scaled[:, x_start:x_start + width]
        return VideoClip(make_frame, duration=duration).set_fps(img_clip.fps)
    
    # Pan Right: Move image from left to right (show right side of image)
    elif animation_type == "pan_right":
        def make_frame(t):
            progress = min(t / duration, 1.0)
            scale = 1.0 + 0.1 * (intensity - 1.0)
            scaled = _zoom_image_array(base_frame, scale, width, height)
            h, w = scaled.shape[:2]
            # Pan from left edge to right edge
            pan_range = max(0, w - width)
            x_start = int(pan_range * progress)
            return scaled[:, x_start:x_start + width]
        return VideoClip(make_frame, duration=duration).set_fps(img_clip.fps)
    
    # Pan Up: Move image from bottom to top (show top of image)
    elif animation_type == "pan_up":
        def make_frame(t):
            progress = min(t / duration, 1.0)
            scale = 1.0 + 0.1 * (intensity - 1.0)
            scaled = _zoom_image_array(base_frame, scale, width, height)
            h, w = scaled.shape[:2]
            # Pan from bottom edge to top edge
            pan_range = max(0, h - height)
            y_start = int(pan_range * (1 - progress))
            return scaled[y_start:y_start + height, :]
        return VideoClip(make_frame, duration=duration).set_fps(img_clip.fps)
    
    # Pan Down: Move image from top to bottom (show bottom of image)
    elif animation_type == "pan_down":
        def make_frame(t):
            progress = min(t / duration, 1.0)
            scale = 1.0 + 0.1 * (intensity - 1.0)
            scaled = _zoom_image_array(base_frame, scale, width, height)
            h, w = scaled.shape[:2]
            # Pan from top edge to bottom edge
            pan_range = max(0, h - height)
            y_start = int(pan_range * progress)
            return scaled[y_start:y_start + height, :]
        return VideoClip(make_frame, duration=duration).set_fps(img_clip.fps)
    
    # Ken Burns: Classic zoom + pan combination
    elif animation_type == "ken_burns":
        def make_frame(t):
            progress = min(t / duration, 1.0)
            # Subtle zoom from 1.0 to 1.15
            zoom_scale = 1.0 + 0.15 * progress
            # Pan diagonally (top-left to bottom-right)
            x_offset = int((width * 0.1) * progress)
            y_offset = int((height * 0.1) * progress)
            
            # Apply zoom
            zoomed = _zoom_image_array(base_frame, zoom_scale, width, height)
            # Apply pan by cropping
            if x_offset > 0 or y_offset > 0:
                h, w = zoomed.shape[:2]
                x_start = max(0, min(x_offset, w - width))
                y_start = max(0, min(y_offset, h - height))
                return zoomed[y_start:y_start + height, x_start:x_start + width]
            return zoomed
        return VideoClip(make_frame, duration=duration).set_fps(img_clip.fps)
    
    # Default: no animation
    return img_clip


def build_transition_audio(prev_entry: Dict[str, Any], next_entry: Dict[str, Any], duration: float) -> Optional[CompositeAudioClip]:
    prev_audio = prev_entry.get("audio_clip")
    next_audio = next_entry.get("audio_clip")
    segments = []

    if prev_audio and prev_entry.get("duration", 0) > 0 and duration > 0:
        start = max(prev_entry["duration"] - duration, 0)
        try:
            prev_segment = prev_audio.subclip(start, prev_entry["duration"]).audio_fadeout(duration)
            segments.append(prev_segment)
        except Exception as exc:
            logger.warning(f"Failed to prepare previous audio transition: {exc}")

    if next_audio and next_entry.get("duration", 0) > 0 and duration > 0:
        end = min(duration, next_entry["duration"])
        try:
            next_segment = next_audio.subclip(0, end).audio_fadein(duration)
            segments.append(next_segment)
        except Exception as exc:
            logger.warning(f"Failed to prepare next audio transition: {exc}")

    if not segments:
        return None

    try:
        return CompositeAudioClip(segments)
    except Exception as exc:
        logger.warning(f"Falling back to single audio segment for transition: {exc}")
        return segments[0]


def create_transition_clip(
    prev_entry: Dict[str, Any],
    next_entry: Dict[str, Any],
    transition_type: str,
    duration: float,
    width: int,
    height: int,
    fps: int
) -> Optional[VideoClip]:
    if duration <= 0:
        return None

    prev_path = prev_entry.get("image_path")
    next_path = next_entry.get("image_path")

    if not prev_path or not next_path or not os.path.exists(prev_path) or not os.path.exists(next_path):
        return None

    prev_image = Image.open(prev_path).convert("RGB")
    next_image = Image.open(next_path).convert("RGB")

    prev_frame = np.array(prev_image)
    next_frame = np.array(next_image)

    prev_clip = ImageClip(prev_frame, duration=duration).set_fps(fps).add_mask()
    next_clip = ImageClip(next_frame, duration=duration).set_fps(fps).add_mask()

    def transition_audio():
        audio = build_transition_audio(prev_entry, next_entry, duration)
        return audio

    if transition_type == "slide_left":
        prev_anim = prev_clip.set_position(lambda t: (-width * (t / duration), 0))
        next_anim = next_clip.set_position(lambda t: (width - width * (t / duration), 0))
        video = CompositeVideoClip([next_anim, prev_anim], size=(width, height))
    elif transition_type == "slide_right":
        prev_anim = prev_clip.set_position(lambda t: (width * (t / duration), 0))
        next_anim = next_clip.set_position(lambda t: (-width + width * (t / duration), 0))
        video = CompositeVideoClip([next_anim, prev_anim], size=(width, height))
    elif transition_type == "slide_up":
        prev_anim = prev_clip.set_position(lambda t: (0, -height * (t / duration)))
        next_anim = next_clip.set_position(lambda t: (0, height - height * (t / duration)))
        video = CompositeVideoClip([next_anim, prev_anim], size=(width, height))
    elif transition_type == "slide_down":
        prev_anim = prev_clip.set_position(lambda t: (0, height * (t / duration)))
        next_anim = next_clip.set_position(lambda t: (0, -height + height * (t / duration)))
        video = CompositeVideoClip([next_anim, prev_anim], size=(width, height))
    elif transition_type == "zoom_in":
        def make_frame(t: float):
            progress = np.clip(t / duration, 0, 1)
            prev_zoom = _zoom_image_array(prev_frame, 1.0 + 0.35 * progress, width, height)
            next_zoom = _zoom_image_array(next_frame, 0.65 + 0.35 * progress, width, height)
            blended = (prev_zoom * (1 - progress) + next_zoom * progress).astype(np.uint8)
            return blended
        video = VideoClip(make_frame, duration=duration).set_fps(fps)
    elif transition_type == "zoom_out":
        def make_frame(t: float):
            progress = np.clip(t / duration, 0, 1)
            prev_zoom = _zoom_image_array(prev_frame, 1.15 - 0.35 * progress, width, height)
            next_zoom = _zoom_image_array(next_frame, 0.85 + 0.15 * progress, width, height)
            blended = (prev_zoom * (1 - progress) + next_zoom * progress).astype(np.uint8)
            return blended
        video = VideoClip(make_frame, duration=duration).set_fps(fps)
    elif transition_type == "zoom_cross":
        def make_frame(t: float):
            progress = np.clip(t / duration, 0, 1)
            prev_zoom = _zoom_image_array(prev_frame, 1 + 0.4 * progress, width, height)
            next_zoom = _zoom_image_array(next_frame, 0.6 + 0.4 * progress, width, height)
            blended = (prev_zoom * (1 - progress) + next_zoom * progress).astype(np.uint8)
            return blended
        video = VideoClip(make_frame, duration=duration).set_fps(fps)
    elif transition_type == "flash":
        def make_frame(t: float):
            progress = np.clip(t / duration, 0, 1)
            base = (prev_frame * (1 - progress) + next_frame * progress).astype(np.uint8)
            intensity = max(0.0, 1.0 - abs((progress * 2) - 1))
            white_overlay = np.full_like(base, 255)
            blended = (base * (1 - intensity) + white_overlay * intensity).astype(np.uint8)
            return blended
        video = VideoClip(make_frame, duration=duration).set_fps(fps)
    elif transition_type == "fade_white":
        def make_frame(t: float):
            progress = np.clip(t / duration, 0, 1)
            base = (prev_frame * (1 - progress) + next_frame * progress).astype(np.uint8)
            white_overlay = np.full_like(base, 255)
            blended = (base * (1 - progress) + white_overlay * progress).astype(np.uint8)
            return blended
        video = VideoClip(make_frame, duration=duration).set_fps(fps)
    elif transition_type == "wipe_left":
        def make_frame(t: float):
            progress = np.clip(t / duration, 0, 1)
            split = int(width * progress)
            frame = prev_frame.copy()
            frame[:, width - split:] = next_frame[:, width - split:]
            return frame
        video = VideoClip(make_frame, duration=duration).set_fps(fps)
    elif transition_type == "wipe_right":
        def make_frame(t: float):
            progress = np.clip(t / duration, 0, 1)
            split = int(width * progress)
            frame = prev_frame.copy()
            frame[:, :split] = next_frame[:, :split]
            return frame
        video = VideoClip(make_frame, duration=duration).set_fps(fps)
    elif transition_type == "wipe_up":
        def make_frame(t: float):
            progress = np.clip(t / duration, 0, 1)
            split = int(height * progress)
            frame = prev_frame.copy()
            frame[height - split:, :] = next_frame[height - split:, :]
            return frame
        video = VideoClip(make_frame, duration=duration).set_fps(fps)
    elif transition_type == "wipe_down":
        def make_frame(t: float):
            progress = np.clip(t / duration, 0, 1)
            split = int(height * progress)
            frame = prev_frame.copy()
            frame[:split, :] = next_frame[:split, :]
            return frame
        video = VideoClip(make_frame, duration=duration).set_fps(fps)
    elif transition_type == "pixelate":
        def make_frame(t: float):
            progress = np.clip(t / duration, 0, 1)
            strength = max(1, int(20 * (1 - progress)))
            small = Image.fromarray(next_frame).resize((max(1, width // strength), max(1, height // strength)), Image.NEAREST)
            pixelated = small.resize((width, height), Image.NEAREST)
            blended = (prev_frame * (1 - progress) + np.array(pixelated) * progress).astype(np.uint8)
            return blended
        video = VideoClip(make_frame, duration=duration).set_fps(fps)
    else:
        return None

    audio = transition_audio()
    if audio:
        video = video.set_audio(audio)
    return video


RANDOM_TRANSITION_POOL = [
    'crossfade', 'fade_black', 'fade_white', 'flash',
    'slide_left', 'slide_right', 'slide_up', 'slide_down',
    'wipe_left', 'wipe_right', 'wipe_up', 'wipe_down',
    'zoom_in', 'zoom_out', 'zoom_cross', 'pixelate'
]


def render_video(
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
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Tuple[str, str, int, int]:
    """
    Render final video from scenes (LEGACY - uses MoviePy for entire timeline).
    
    NOTE: This is the original rendering function. For better performance,
    use render_video_optimized() which uses scene-based rendering with ffmpeg concat.
    
    This function is kept for backward compatibility and fallback scenarios.
    
    Args:
        scenes: List of scene dictionaries with images and audio
        video_id: Video ID for file naming
        resolution: Video resolution
        orientation: Video orientation
        fps: Frames per second
        background_music: Background music file
        video_overlay: Video overlay file
        font: Font for subtitles
        subtitle_style: Subtitle styling options
        transition_type: Transition type between clips (none, crossfade, fade_black)
        transition_duration: Transition duration in seconds
        progress_callback: Callback for progress updates
        
    Returns:
        Tuple of (video_path, thumbnail_path, duration_seconds, file_size_bytes)
    """
    import time
    render_start = time.time()
    logger.info(f"[VIDEO {video_id}] Starting LEGACY rendering (consider using optimized renderer)")
    
    # Get dimensions
    resolution_map = {
        "720p": {"portrait": (720, 1280), "landscape": (1280, 720)},
        "1080p": {"portrait": (1080, 1920), "landscape": (1920, 1080)},
        "2K": {"portrait": (1440, 2560), "landscape": (2560, 1440)},
        "4K": {"portrait": (2160, 3840), "landscape": (3840, 2160)},
    }
    
    width, height = resolution_map.get(resolution, {}).get(orientation, (1080, 1920))
    
    # Create clips for each scene
    scene_entries: List[Dict[str, Any]] = []
    min_clip_duration: Optional[float] = None
    
    for idx, scene in enumerate(scenes):
        try:
            # Get image URL and path
            image_url = scene.get("image_url")
            if not image_url:
                logger.error(f"Scene {idx + 1} has no image_url, skipping")
                continue
            
            image_path = image_url.replace("/uploads/", "uploads/")
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                continue
            
            # Load audio first to get the correct duration
            audio_url = scene.get("audio_url")
            audio_clip = None
            duration = scene.get("duration", 3.0)  # Default fallback
            
            if audio_url:
                audio_path = audio_url.replace("/uploads/", "uploads/")
                if os.path.exists(audio_path):
                    try:
                        audio_clip = AudioFileClip(audio_path)
                        # Use audio duration as the clip duration (no pauses!)
                        duration = audio_clip.duration
                        logger.info(f"Scene {idx + 1}: Audio loaded ({duration}s)")
                    except Exception as audio_error:
                        logger.warning(f"Could not load audio for scene {idx + 1}: {audio_error}")
                else:
                    logger.warning(f"Audio file not found: {audio_path}")
            else:
                logger.warning(f"Scene {idx + 1} has no audio, using default duration")
            
            # CRITICAL: Pre-process image to ensure exact dimensions BEFORE MoviePy
            from PIL import Image as PILImage
            pil_img = PILImage.open(image_path)
            img_width, img_height = pil_img.size
            
            logger.info(f"Scene {idx + 1}: Image dimensions {img_width}x{img_height}, Target: {width}x{height}")
            
            # If dimensions don't match, resize with PIL before giving to MoviePy
            if img_width != width or img_height != height:
                # Calculate aspect ratios
                target_aspect = width / height
                img_aspect = img_width / img_height
                
                # Crop to target aspect ratio if needed
                if abs(img_aspect - target_aspect) > 0.01:
                    if img_aspect > target_aspect:
                        # Image is too wide, crop width
                        new_width = int(img_height * target_aspect)
                        left = (img_width - new_width) // 2
                        pil_img = pil_img.crop((left, 0, left + new_width, img_height))
                    else:
                        # Image is too tall, crop height
                        new_height = int(img_width / target_aspect)
                        top = (img_height - new_height) // 2
                        pil_img = pil_img.crop((0, top, img_width, top + new_height))
                
                # Resize to exact target dimensions
                pil_img = pil_img.resize((width, height), PILImage.Resampling.LANCZOS)
                
                # Save the properly sized image temporarily
                temp_image_path = image_path.replace('.png', '_resized.png')
                pil_img.save(temp_image_path, 'PNG')
                logger.info(f"Scene {idx + 1}: Resized to {width}x{height}, saved to {temp_image_path}")
                image_path = temp_image_path
            
            # Create image clip with exact audio duration (no extra pauses!)
            img_clip = ImageClip(image_path, duration=duration)
            # NO RESIZE - image is already exact dimensions!
            img_clip = img_clip.set_fps(fps)  # Set consistent FPS for all clips
            
            # Apply image animation if specified
            if image_animation and image_animation != "none":
                img_clip = apply_image_animation(
                    img_clip=img_clip,
                    animation_type=image_animation,
                    duration=duration,
                    width=width,
                    height=height,
                    intensity=image_animation_intensity
                )
                logger.info(f"Scene {idx + 1}: Applied {image_animation} animation")
            
            # Attach audio to image clip
            if audio_clip:
                img_clip = img_clip.set_audio(audio_clip)
                logger.info(f"Scene {idx + 1}: Image and audio synced perfectly ({duration}s)")
            
            # Add subtitles using PIL (no ImageMagick needed!)
            scene_text = scene.get("text", "")
            subtitles_enabled = True  # Default to enabled
            if subtitle_style and isinstance(subtitle_style, dict):
                # Check if explicitly disabled
                if subtitle_style.get("enabled") is False:
                    subtitles_enabled = False
                else:
                    subtitles_enabled = True
            if scene.get("subtitle_enabled") is not None:
                subtitles_enabled = bool(scene.get("subtitle_enabled"))

            if scene_text and subtitle_style and subtitles_enabled:
                try:
                    # Get subtitle settings
                    font_size = subtitle_style.get("font_size", 60)
                    position = subtitle_style.get("position", "bottom")
                    
                    # Parse text_color - can be hex string or tuple
                    text_color_raw = subtitle_style.get("text_color", "#FFFFFF")
                    if isinstance(text_color_raw, str):
                        # Parse hex color
                        hex_color = text_color_raw.lstrip('#')
                        text_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    elif isinstance(text_color_raw, (list, tuple)):
                        text_color = tuple(text_color_raw)
                    else:
                        text_color = (255, 255, 255)
                    
                    bg_opacity = subtitle_style.get("bg_opacity", 180)
                    outline_width = subtitle_style.get("outline_width", 3)
                    
                    # Get font path if specified
                    font_path = None
                    if font and os.path.exists(f"font/{font}"):
                        font_path = f"font/{font}"
                    
                    subtitle_clips = build_subtitle_clips(
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
                    
                    if subtitle_clips:
                        img_clip = CompositeVideoClip([img_clip, *subtitle_clips], size=(width, height))
                        logger.info(f"Scene {idx + 1}: Added {len(subtitle_clips)} subtitle segments.")
                    
                except Exception as subtitle_error:
                    logger.warning(f"Could not add subtitles for scene {idx + 1}: {subtitle_error}")
            
            scene_entries.append({
                "clip": img_clip,
                "audio_clip": audio_clip,
                "image_path": image_path,
                "duration": duration
            })
            if min_clip_duration is None or duration < min_clip_duration:
                min_clip_duration = duration
            
            # Update progress
            if progress_callback:
                progress = ((idx + 1) / len(scenes)) * 100
                progress_callback(progress)
                
        except Exception as e:
            logger.error(f"Error creating clip for scene {idx + 1}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if not scene_entries:
        raise Exception("No clips generated")

    transition_effect = normalize_transition_type(transition_type)
    random_transition_pool = [
        t for t in RANDOM_TRANSITION_POOL
        if t in SUPPORTED_TRANSITIONS
    ]

    clips = [entry["clip"] for entry in scene_entries]
    effective_transition = 0.0
    if transition_effect != "none":
        effective_transition = max(0.0, min(transition_duration, max(min_clip_duration / 2, 0)))
    transition_clips_created: List[VideoClip] = []

    if transition_effect == "crossfade" and effective_transition > 0 and len(clips) > 1:
        logger.info(f"Applying crossfade transitions ({effective_transition}s)")
        final_video = concatenate_videoclips(clips, method="compose", transition=effective_transition)
        sequence_clips = clips
    else:
        sequence_clips: List[VideoClip] = []
        for idx, entry in enumerate(scene_entries):
            clip = entry["clip"]

            if transition_effect == "fade_black" and effective_transition > 0 and len(scene_entries) > 1:
                new_clip = clip
                if idx > 0:
                    new_clip = new_clip.fx(vfx_fadein, effective_transition)
                    if new_clip.audio:
                        new_clip = new_clip.audio_fadein(effective_transition)
                if idx < len(scene_entries) - 1:
                    new_clip = new_clip.fx(vfx_fadeout, effective_transition)
                    if new_clip.audio:
                        new_clip = new_clip.audio_fadeout(effective_transition)
                clip = new_clip

            sequence_clips.append(clip)

            if idx < len(scene_entries) - 1:
                selected_transition = transition_effect
                if transition_effect == "random" or transition_effect == "mix":
                    selected_transition = random.choice(random_transition_pool) if random_transition_pool else 'crossfade'
                    logger.debug(f"{'Random' if transition_effect == 'random' else 'Mix'} transition between scene {idx + 1} and {idx + 2}: {selected_transition}")
                if selected_transition not in ("none", "fade_black", "crossfade") and effective_transition > 0:
                    transition_clip = create_transition_clip(
                        scene_entries[idx],
                        scene_entries[idx + 1],
                        selected_transition,
                        effective_transition,
                        width,
                        height,
                        fps
                    )
                    if transition_clip:
                        sequence_clips.append(transition_clip.without_audio())
                        transition_clips_created.append(transition_clip)

        if len(sequence_clips) == 1:
            final_video = sequence_clips[0]
        else:
            final_video = concatenate_videoclips(sequence_clips, method="compose")
    logger.info(f"Concatenated {len(sequence_clips)} clips into final video")
    
    # Add background music if specified
    if background_music and os.path.exists(f"music/{background_music}"):
        try:
            bg_music = AudioFileClip(f"music/{background_music}")
            bg_music = bg_music.volumex(0.3)  # Lower volume
            
            # Loop music if video is longer
            if bg_music.duration < final_video.duration:
                bg_music = bg_music.audio_loop(duration=final_video.duration)
            else:
                bg_music = bg_music.subclip(0, final_video.duration)
            
            # Mix audio
            if final_video.audio:
                final_audio = CompositeAudioClip([final_video.audio, bg_music])
                final_video = final_video.set_audio(final_audio)
            else:
                final_video = final_video.set_audio(bg_music)
                
        except Exception as e:
            logger.error(f"Error adding background music: {e}")
    
    # Add video overlay if specified
    if video_overlay and os.path.exists(f"overlays/{video_overlay}"):
        try:
            overlay = VideoFileClip(f"overlays/{video_overlay}")
            overlay = overlay.resize((width, height))
            
            # Loop overlay if needed
            if overlay.duration < final_video.duration:
                overlay = overlay.loop(duration=final_video.duration)
            else:
                overlay = overlay.subclip(0, final_video.duration)
            
            overlay = overlay.set_opacity(0.5)
            final_video = CompositeVideoClip([final_video, overlay])
            
        except Exception as e:
            logger.error(f"Error adding video overlay: {e}")
    
    # Save video
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    video_filename = f"video_{video_id}_final.mp4"
    video_path = os.path.join(upload_dir, video_filename)
    temp_video_path = os.path.join(upload_dir, f"video_{video_id}_final.tmp.mp4")
    
    total_duration = final_video.duration
    # Use more CPU cores and a faster preset to reduce render time while keeping good quality
    cpu_threads = max(1, os.cpu_count() or 4)
    # Prefer a faster preset for shorter projects and fall back to 'medium' for longer high-quality exports
    fast_preset = 'fast' if total_duration and total_duration <= 300 else 'medium'
    if total_duration and total_duration <= 120:
        fast_preset = 'faster'

    if width >= 3840:
        target_bitrate = '12000k'
    elif width >= 2560:
        target_bitrate = '9000k'
    elif width >= 1920:
        target_bitrate = '6000k'
    elif width >= 1280:
        target_bitrate = '4500k'
    else:
        target_bitrate = '3000k'

    logger.info(
        "Writing video with preset=%s using %s threads (duration: %.2fs, bitrate=%s)",
        fast_preset,
        cpu_threads,
        total_duration or 0.0,
        target_bitrate
    )
    try:
        final_video.write_videofile(
            temp_video_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            threads=cpu_threads,
            preset=fast_preset,
            bitrate=target_bitrate
        )
        # Rename temp file to final file
        if os.path.exists(temp_video_path):
            try:
                # Remove final file if it exists (shouldn't happen, but just in case)
                if os.path.exists(video_path):
                    os.remove(video_path)
                os.rename(temp_video_path, video_path)
                logger.info(f"Successfully renamed {temp_video_path} to {video_path}")
            except OSError as e:
                logger.error(f"Failed to rename temp video file: {e}")
                # If rename fails, try to copy instead
                import shutil
                try:
                    shutil.copy2(temp_video_path, video_path)
                    os.remove(temp_video_path)
                    logger.info(f"Copied temp file to final location: {video_path}")
                except Exception as copy_error:
                    logger.error(f"Failed to copy temp video file: {copy_error}")
                    raise
    finally:
        # Clean up temp file if it still exists
        if os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except OSError:
                pass
    
    # Generate thumbnail
    thumbnail_filename = f"video_{video_id}_thumb.jpg"
    thumbnail_path = os.path.join(upload_dir, thumbnail_filename)
    
    frame = final_video.get_frame(0)
    Image.fromarray(frame).save(thumbnail_path, quality=85)
    
    # Get file size
    file_size = os.path.getsize(video_path)
    
    # Clean up
    final_video.close()
    for entry in scene_entries:
        entry["clip"].close()
        if entry.get("audio_clip"):
            try:
                entry["audio_clip"].close()
            except Exception:
                pass
    for clip in transition_clips_created:
        try:
            clip.close()
        except Exception:
            pass
    
    render_elapsed = time.time() - render_start
    logger.info(f"[VIDEO {video_id}] LEGACY rendering completed in {render_elapsed:.2f}s")
    logger.info(f"Video rendered successfully: {video_path}")
    
    return (
        f"/uploads/{video_filename}",
        f"/uploads/{thumbnail_filename}",
        int(total_duration),
        file_size
    )

