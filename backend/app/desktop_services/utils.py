"""Utility functions from desktop app."""

import json
import os
from PIL import Image
from io import BytesIO


def load_config():
    """Load configuration from config.json."""
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def get_custom_styles():
    """Get custom styles from config."""
    config = load_config()
    return config.get("custom_styles", {})


def normalize_image_bytes_to_size(image_bytes, target_width, target_height):
    """
    Normalize image bytes to a specific size.
    
    Args:
        image_bytes: Raw image bytes
        target_width: Target width
        target_height: Target height
        
    Returns:
        Normalized image bytes
    """
    try:
        # Open image from bytes
        img = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize to target dimensions
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Save back to bytes
        output = BytesIO()
        img.save(output, format='PNG', quality=95)
        return output.getvalue()
        
    except Exception as e:
        print(f"Error normalizing image: {e}")
        return image_bytes

