"""
Rendering presets for video generation.

This module defines encoding presets that balance speed vs quality.
Fast preset prioritizes speed for quick previews and testing.
Quality preset prioritizes visual quality for final exports.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import os


@dataclass
class RenderingPreset:
    """Configuration for video rendering preset."""
    name: str
    description: str
    # FFmpeg encoding settings
    crf: int  # Constant Rate Factor (lower = higher quality, 18-28 typical range)
    preset: str  # FFmpeg preset: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    # Resolution limits (if user chooses higher, we still respect it but may warn)
    max_recommended_resolution: str = "1080p"
    # FPS defaults
    default_fps: int = 24
    # Additional ffmpeg args
    extra_args: List[str] = None
    
    def __post_init__(self):
        if self.extra_args is None:
            self.extra_args = []


# Define presets
PRESET_FAST = RenderingPreset(
    name="fast",
    description="Fast encoding for quick previews and testing",
    crf=26,  # Higher CRF = faster encoding, slightly lower quality
    preset="veryfast",  # Fastest reasonable preset
    max_recommended_resolution="1080p",
    default_fps=24,
    extra_args=[
        "-movflags", "+faststart",  # Enable fast start for web playback
        "-pix_fmt", "yuv420p",  # Ensure compatibility
    ]
)

PRESET_QUALITY = RenderingPreset(
    name="quality",
    description="High quality encoding for final exports",
    crf=20,  # Lower CRF = higher quality
    preset="medium",  # Balanced quality/speed
    max_recommended_resolution="4K",
    default_fps=30,
    extra_args=[
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",  # H.264 high profile
    ]
)

# Map of preset names to preset objects
PRESETS: Dict[str, RenderingPreset] = {
    "fast": PRESET_FAST,
    "quality": PRESET_QUALITY,
}

# Default preset (can be overridden via environment variable)
DEFAULT_PRESET = os.getenv("QUANTUMCLIP_DEFAULT_RENDERING_PRESET", "fast")


def get_preset(preset_name: Optional[str] = None) -> RenderingPreset:
    """
    Get rendering preset by name.
    
    Args:
        preset_name: Name of preset ('fast' or 'quality'). If None, uses default.
        
    Returns:
        RenderingPreset object
        
    Raises:
        ValueError: If preset_name is invalid
    """
    if preset_name is None:
        preset_name = DEFAULT_PRESET
    
    preset_name = preset_name.lower()
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    
    return PRESETS[preset_name]


def get_ffmpeg_args_for_preset(
    preset: RenderingPreset,
    width: int,
    height: int,
    fps: int,
    output_path: str,
    audio_path: Optional[str] = None
) -> List[str]:
    """
    Generate ffmpeg command arguments for a given preset.
    
    Args:
        preset: RenderingPreset to use
        width: Video width in pixels
        height: Video height in pixels
        fps: Frames per second
        output_path: Output video file path
        audio_path: Optional audio file to include
        
    Returns:
        List of ffmpeg arguments
    """
    args = [
        "-y",  # Overwrite output file
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",  # Read from stdin
    ]
    
    if audio_path and os.path.exists(audio_path):
        args.extend([
            "-i", audio_path,
        ])
    
    # Video encoding
    args.extend([
        "-c:v", "libx264",
        "-preset", preset.preset,
        "-crf", str(preset.crf),
        "-r", str(fps),
    ])
    
    # Audio encoding (if audio provided)
    if audio_path and os.path.exists(audio_path):
        args.extend([
            "-c:a", "aac",
            "-b:a", "192k",
        ])
    else:
        args.extend([
            "-an",  # No audio
        ])
    
    # Add preset-specific extra args
    args.extend(preset.extra_args)
    
    # Output
    args.append(output_path)
    
    return args

