"""
WebSocket manager for real-time video progress updates.

This module manages WebSocket connections and broadcasts progress updates
to connected clients when video generation progresses.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Union
from fastapi import WebSocket, WebSocketDisconnect
from app.models.video import VideoStatus
from app.schemas.video import normalize_video_status

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Map of video_id -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, video_id: int):
        """Connect a WebSocket client for a specific video."""
        await websocket.accept()
        
        async with self.lock:
            if video_id not in self.active_connections:
                self.active_connections[video_id] = set()
            self.active_connections[video_id].add(websocket)
        
        logger.info(f"WebSocket connected for video {video_id} (total connections: {len(self.active_connections.get(video_id, set()))})")
    
    async def disconnect(self, websocket: WebSocket, video_id: int):
        """Disconnect a WebSocket client."""
        async with self.lock:
            if video_id in self.active_connections:
                self.active_connections[video_id].discard(websocket)
                if not self.active_connections[video_id]:
                    del self.active_connections[video_id]
        
        logger.info(f"WebSocket disconnected for video {video_id}")
    
    async def send_progress(self, video_id: int, data: dict):
        """Send progress update to all connected clients for a video."""
        if video_id not in self.active_connections:
            return
        
        message = json.dumps(data)
        disconnected = set()
        
        async with self.lock:
            connections = self.active_connections.get(video_id, set()).copy()
        
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Error sending WebSocket message to video {video_id}: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        if disconnected:
            async with self.lock:
                if video_id in self.active_connections:
                    self.active_connections[video_id] -= disconnected
                    if not self.active_connections[video_id]:
                        del self.active_connections[video_id]
    
    async def broadcast_progress(
        self,
        video_id: int,
        status: Union[str, VideoStatus],
        progress: float,
        current_step: str = None,
        error_message: str = None,
        scene_count: int = None,
        current_scene: int = None,
    ):
        """
        Broadcast a progress update with standardized format.
        
        Normalizes status to user-facing value: "in_progress", "completed", or "failed"
        before sending to frontend.
        """
        # Normalize status to user-facing value
        if isinstance(status, VideoStatus):
            normalized_status = normalize_video_status(status)
        elif isinstance(status, str):
            # Try to normalize if it's an internal status
            try:
                status_enum = VideoStatus(status)
                normalized_status = normalize_video_status(status_enum)
            except (ValueError, AttributeError):
                # Already normalized or unknown, use as-is
                normalized_status = status if status in ["in_progress", "completed", "failed"] else "in_progress"
        else:
            normalized_status = "in_progress"  # Default fallback
        
        data = {
            "type": "progress",
            "video_id": video_id,
            "status": normalized_status,  # Always send normalized status
            "progress": progress,
            "current_step": current_step,
            "error_message": error_message,
            "scene_count": scene_count,
            "current_scene": current_scene,
        }
        
        await self.send_progress(video_id, data)
    
    def get_connection_count(self, video_id: int) -> int:
        """Get number of active connections for a video."""
        return len(self.active_connections.get(video_id, set()))


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


