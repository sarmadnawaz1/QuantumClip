"""Main API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, videos, styles, settings, websocket

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(videos.router, prefix="/videos", tags=["Videos"])
api_router.include_router(styles.router, prefix="/styles", tags=["Styles"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(websocket.router, tags=["WebSocket"])

