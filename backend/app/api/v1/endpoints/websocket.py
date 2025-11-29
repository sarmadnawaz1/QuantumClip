"""WebSocket endpoints for real-time video progress updates."""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.video import Video
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/videos/{video_id}/progress")
async def video_progress_websocket(
    websocket: WebSocket,
    video_id: int,
):
    """
    WebSocket endpoint for real-time video generation progress.
    
    Clients connect to this endpoint to receive real-time updates
    about video generation progress, including:
    - Status changes (pending, processing, generating_images, etc.)
    - Progress percentage (0-100)
    - Current step description
    - Error messages
    - Scene count and current scene being processed
    """
    # Verify video exists
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Video).where(Video.id == video_id))
            video = result.scalar_one_or_none()
            
            if not video:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Video not found")
                return
        
        # Connect to WebSocket manager
        await websocket_manager.connect(websocket, video_id)
        
        # Send initial status
        initial_data = {
            "type": "connected",
            "video_id": video_id,
            "status": video.status,
            "progress": video.progress,
            "current_step": None,
        }
        await websocket.send_text(json.dumps(initial_data))
        
        logger.info(f"WebSocket client connected for video {video_id}")
        
        # Keep connection alive and handle disconnects
        try:
            while True:
                # Wait for any message from client (ping/pong or close)
                data = await websocket.receive_text()
                
                # Handle ping
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected for video {video_id}")
        except Exception as e:
            logger.error(f"WebSocket error for video {video_id}: {e}", exc_info=True)
        finally:
            await websocket_manager.disconnect(websocket, video_id)
            
    except Exception as e:
        logger.error(f"Error setting up WebSocket for video {video_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass



