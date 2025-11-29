"""Service for generating images from prompts - using desktop app's actual services."""

import os
import logging
from typing import List, Dict, Callable, Optional
from PIL import Image
import io
from app.services.desktop_image_service import get_image_service
from app.utils import load_config
from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_images_for_scenes(
    scenes: List[Dict],
    image_service: str = "pollination",
    image_model: Optional[str] = None,
    resolution: str = "1080p",
    orientation: str = "portrait",
    video_id: int = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> List[Dict]:
    """
    Generate images for all scenes using desktop app's image services.
    
    Args:
        scenes: List of scene dictionaries with prompts
        image_service: Image service to use (replicate, together, fal, runware, pollination)
        image_model: Specific model to use (for services that support it)
        resolution: Video resolution
        orientation: Video orientation (portrait/landscape)
        video_id: Video ID for file naming
        progress_callback: Callback for progress updates
        
    Returns:
        List of scenes with image URLs
    """
    # Get dimensions based on resolution and orientation
    config = load_config()
    resolution_map = config.get("video_resolutions", {
        "720p": {"portrait": {"width": 720, "height": 1280}, "landscape": {"width": 1280, "height": 720}},
        "1080p": {"portrait": {"width": 1080, "height": 1920}, "landscape": {"width": 1920, "height": 1080}},
        "2K": {"portrait": {"width": 1440, "height": 2560}, "landscape": {"width": 2560, "height": 1440}},
        "4K": {"portrait": {"width": 2160, "height": 3840}, "landscape": {"width": 3840, "height": 2160}},
    })
    
    dims = resolution_map.get(resolution, {}).get(orientation, {"width": 1080, "height": 1920})
    width = dims["width"]
    height = dims["height"]
    
    # Get API key for the service
    api_key_map = {
        "replicate": settings.replicate_api_key or os.environ.get("REPLICATE_API_KEY"),
        "together": settings.together_api_key or os.environ.get("TOGETHER_API_KEY"),
        "fal": settings.fal_key or os.environ.get("FAL_KEY"),
        "runware": settings.runware_api_key or os.environ.get("RUNWARE_API_KEY"),
        "pollination": None,  # Free service
    }
    
    requested_service = image_service.lower()
    api_key = api_key_map.get(requested_service)
    if requested_service != "pollination" and not api_key:
        error_msg = f"{requested_service.title()} selected but no API key was provided. Please add your API key in Settings."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # Get desktop app's image service
    try:
        service = get_image_service(
            service_name=image_service,
            api_token=api_key,
            model_type=image_model
        )
    except Exception as e:
        error_msg = f"Failed to initialize {image_service} image service: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # Generate images for each scene
    total_scenes = len(scenes)
    for idx, scene in enumerate(scenes):
        try:
            logger.info(f"Generating image for scene {scene['scene_number']}/{total_scenes}")

            # Generate image using desktop app service
            try:
                image_bytes = service.generate_image(
                    prompt=scene["image_prompt"],
                    width=width,
                    height=height,
                    steps=25
                )
            except Exception as gen_error:
                error_msg = f"{image_service.title()} failed to generate image for scene {scene['scene_number']}: {gen_error}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            if image_bytes:
                # Resize image to exact dimensions to ensure correct aspect ratio
                try:
                    # Load image from bytes
                    img = Image.open(io.BytesIO(image_bytes))
                    original_size = img.size
                    logger.info(f"Original image size: {original_size[0]}x{original_size[1]}, Target: {width}x{height}")
                    
                    # CRITICAL FIX: Detect and remove ONLY black borders (AI padding)
                    import numpy as np
                    img_array = np.array(img)
                    
                    # Find the bounding box of non-black content
                    # Consider pixels with RGB > 30 as non-black
                    mask = np.any(img_array > 30, axis=2)
                    
                    # Find rows and columns that contain non-black pixels
                    rows = np.any(mask, axis=1)
                    cols = np.any(mask, axis=0)
                    
                    if np.any(rows) and np.any(cols):
                        # Find the boundaries of actual content
                        row_min, row_max = np.where(rows)[0][[0, -1]]
                        col_min, col_max = np.where(cols)[0][[0, -1]]
                        
                        # Crop out ONLY black borders (AI padding)
                        img_cropped = img.crop((col_min, row_min, col_max + 1, row_max + 1))
                        
                        if img_cropped.size != img.size:
                            logger.info(f"✅ Removed AI black borders: {original_size} -> {img_cropped.size}")
                            img = img_cropped
                        else:
                            logger.info(f"✅ No black borders detected, using original")
                    
                    # NOW: Stretch the content (after removing black borders) to fit target dimensions
                    # This preserves ALL content - no cropping!
                    logger.info(f"Content size after border removal: {img.size[0]}x{img.size[1]}")
                    logger.info(f"Stretching to target dimensions: {width}x{height}")
                    
                    # High-quality resize with LANCZOS (best quality for upscaling)
                    img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
                    
                    # Apply sharpening to compensate for any stretching blur
                    from PIL import ImageEnhance, ImageFilter
                    
                    # Sharpen the image to improve clarity
                    sharpener = ImageEnhance.Sharpness(img_resized)
                    img_resized = sharpener.enhance(1.3)  # 30% sharpening boost
                    
                    # Optional: Apply a subtle unsharp mask for extra crispness
                    img_resized = img_resized.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
                    
                    logger.info(f"✅ Fitted to screen with sharpening: {img_resized.size[0]}x{img_resized.size[1]} (content preserved, enhanced quality)")
                    
                    # Verify dimensions are correct
                    if img_resized.size != (width, height):
                        logger.error(f"❌ DIMENSION MISMATCH! Expected {width}x{height}, got {img_resized.size[0]}x{img_resized.size[1]}")
                        # Force it one more time
                        img_resized = img_resized.resize((width, height), Image.Resampling.LANCZOS)
                    
                    # Save image to file
                    upload_dir = "uploads"
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    image_filename = f"video_{video_id}_scene_{scene['scene_number']}.png"
                    image_path = os.path.join(upload_dir, image_filename)
                    
                    img_resized.save(image_path, 'PNG', optimize=True)
                    
                    scene["image_url"] = f"/uploads/{image_filename}"
                    logger.info(f"✅ Image saved with VERIFIED dimensions: {image_path} ({width}x{height})")
                except Exception as resize_error:
                    logger.error(f"Error resizing image: {resize_error}")
                    # Fallback: save original image
                    upload_dir = "uploads"
                    os.makedirs(upload_dir, exist_ok=True)
                    image_filename = f"video_{video_id}_scene_{scene['scene_number']}.png"
                    image_path = os.path.join(upload_dir, image_filename)
                    with open(image_path, 'wb') as f:
                        f.write(image_bytes)
                    scene["image_url"] = f"/uploads/{image_filename}"
                    logger.warning(f"⚠️ Saved original image without resizing: {image_path}")
            else:
                error_msg = f"{image_service.title()} returned no data for scene {scene['scene_number']}."
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Update progress
            if progress_callback:
                progress = ((idx + 1) / total_scenes) * 100
                progress_callback(progress)
                
        except Exception as e:
            logger.error(f"Error generating image for scene {scene['scene_number']}: {e}")
            raise
    
    return scenes
