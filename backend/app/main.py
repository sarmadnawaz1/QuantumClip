"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import os

from sqlalchemy import text

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.v1.router import api_router

# Import all models to ensure they're registered before database initialization
# This is critical - tables won't be created if models aren't imported
from app.models import User, Video, CustomStyle, UserAPIKey  # noqa: F401

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def ensure_video_columns():
    """
    Ensure all required columns exist on the videos table (async, non-blocking).
    This runs after init_db() and doesn't block server startup.
    Adds missing columns that were added to the model after initial table creation.
    """
    try:
        from app.core.database import engine
        from sqlalchemy import inspect
        
        # Use existing async engine from database.py (no new connection overhead)
        async with engine.begin() as connection:
            # For async SQLAlchemy, we need to use run_sync for inspection
            from sqlalchemy import inspect as sync_inspect
            
            def check_and_add_columns(sync_conn):
                """Synchronous function to check and add columns."""
                inspector = sync_inspect(sync_conn)
                
                if 'videos' not in inspector.get_table_names():
                    return []
                
                columns = {column['name'] for column in inspector.get_columns('videos')}
                statements = []
                
                # Transition columns
                if 'transition_type' not in columns:
                    if 'sqlite' in settings.database_url:
                        statements.append(text("ALTER TABLE videos ADD COLUMN transition_type TEXT DEFAULT 'none'"))
                    else:
                        statements.append(text("ALTER TABLE videos ADD COLUMN transition_type VARCHAR DEFAULT 'none'"))
                
                if 'transition_duration' not in columns:
                    if 'sqlite' in settings.database_url:
                        statements.append(text("ALTER TABLE videos ADD COLUMN transition_duration REAL DEFAULT 0.5"))
                    else:
                        statements.append(text("ALTER TABLE videos ADD COLUMN transition_duration DOUBLE PRECISION DEFAULT 0.5"))
                
                # Target scene count column
                if 'target_scene_count' not in columns:
                    if 'sqlite' in settings.database_url:
                        statements.append(text("ALTER TABLE videos ADD COLUMN target_scene_count INTEGER"))
                    else:
                        statements.append(text("ALTER TABLE videos ADD COLUMN target_scene_count INTEGER"))
                
                return statements
            
            # Run sync inspection in thread pool to avoid blocking
            statements = await connection.run_sync(lambda sync_conn: check_and_add_columns(sync_conn))
            
            # Execute any needed ALTER statements
            for statement in statements:
                await connection.execute(statement)
                logger.info("Applied schema upgrade: %s", statement)
    except Exception as exc:
        # Don't fail startup if schema check fails - just log warning
        logger.warning("Could not verify or update video columns: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    
    Startup sequence:
    1. Initialize database (create tables if needed)
    2. Verify/update schema columns
    3. Initialize Sentry (if configured)
    4. Application is ready - uvicorn will start accepting requests
    
    This function runs before uvicorn starts listening on the port.
    Heavy imports (MoviePy, PIL, etc.) happen during module import,
    which occurs before this function runs.
    """
    # Startup
    # Minimal startup logging - don't slow down startup with excessive logging
    logger.info("Starting QuantumClip Backend...")
    
    try:
        await init_db()
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        raise  # Fail fast - don't start if DB is broken
    
    # Schema verification - run asynchronously but don't block if it fails
    # This is optional and won't prevent server from starting
    try:
        await ensure_video_columns()
        logger.info("✅ Database schema verified")
    except Exception as e:
        # Don't log as warning - this is optional and may fail on first run
        logger.debug(f"Schema verification skipped: {e}")
    
    logger.info("✅ Database initialized successfully")
    
    # Initialize Sentry if configured
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.environment,
                traces_sample_rate=1.0 if settings.debug else 0.1,
            )
            logger.info("✅ Sentry initialized")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize Sentry: {e}")
    
    logger.info("✅ Application startup complete - ready to accept requests")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered video generation from text scripts",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Mount static files (uploads directory)
# Create uploads directory if it doesn't exist
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
    logger.info(f"Created uploads directory: {uploads_dir}")

app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
logger.info(f"Mounted /uploads static files from: {uploads_dir}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.debug else None,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
    )

