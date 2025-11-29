"""Utility functions for the backend - based on desktop app utils."""

import json
import os
from PIL import Image
import io
from typing import Dict, Any


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    First tries the path as-is, then tries parent directories.
    """
    # Try multiple locations
    possible_paths = [
        config_path,
        os.path.join(os.path.dirname(__file__), config_path),
        os.path.join(os.path.dirname(__file__), "..", config_path),
        os.path.join(os.path.dirname(__file__), "..", "..", config_path),
        "/Users/sarmadnawaz/Downloads/ShaziVideoGen3.9.1/config.json",  # Desktop app config
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    # Return default config if not found
    return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Get default configuration if config file not found."""
    return {
        "story_generation": {
            "char_limit_min": 600,
            "char_limit_max": 700
        },
        "storyboard": {
            "max_scenes": 14
        },
        "openai": {
            "model": "llama-3.1-8b-instant",
            "temperature": 0.9
        },
        "groq": {
            "model": "llama-3.1-8b-instant",
            "temperature": 0.9
        },
        "gemini": {
            "model": "gemini-1.5-flash",
            "temperature": 0.9
        },
        "video_resolutions": {
            "720p": {"portrait": {"width": 720, "height": 1280}, "landscape": {"width": 1280, "height": 720}},
            "1080p": {"portrait": {"width": 1080, "height": 1920}, "landscape": {"width": 1920, "height": 1080}},
            "2K": {"portrait": {"width": 1440, "height": 2560}, "landscape": {"width": 2560, "height": 1440}},
            "4K": {"portrait": {"width": 2160, "height": 3840}, "landscape": {"width": 3840, "height": 2160}}
        },
        "tts": {
            "speech_rate": 0.989795918367347
        }
    }


def normalize_image_bytes_to_size(image_bytes: bytes, target_width: int, target_height: int) -> bytes:
    """
    Normalize image bytes to a specific size while maintaining aspect ratio.
    
    Args:
        image_bytes: Original image as bytes
        target_width: Target width in pixels
        target_height: Target height in pixels
        
    Returns:
        Resized image as bytes
    """
    try:
        # Load image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Resize maintaining aspect ratio
        image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Create new image with exact target dimensions and paste the resized image centered
        new_image = Image.new('RGB', (target_width, target_height), (0, 0, 0))
        
        # Calculate position to center the image
        x = (target_width - image.width) // 2
        y = (target_height - image.height) // 2
        
        new_image.paste(image, (x, y))
        
        # Convert back to bytes
        output_buffer = io.BytesIO()
        new_image.save(output_buffer, format='PNG', quality=95)
        return output_buffer.getvalue()
        
    except Exception as e:
        print(f"Error normalizing image: {e}")
        return image_bytes  # Return original if resizing fails


def get_custom_styles() -> Dict[str, Dict]:
    """Get custom styles from config."""
    config = load_config()
    return config.get("custom_styles", {})


def get_config_value(key_path: str, default=None):
    """
    Get a configuration value using dot notation.
    Example: get_config_value('openai.model') returns 'llama-3.1-8b-instant'
    """
    config = load_config()
    keys = key_path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value

