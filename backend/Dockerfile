FROM python:3.12-slim

# Install system dependencies
# - ffmpeg: Video processing
# - libmagic1: File type detection
# - curl: Health checks
# - gcc/g++: Compile Python packages with C extensions
# - postgresql-client: Database client tools (optional, for debugging)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    curl \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
# This may take a while due to heavy packages like MoviePy, PIL, etc.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories for uploads and assets
RUN mkdir -p uploads music font overlays style_previews

# Expose port 8000 (FastAPI backend)
EXPOSE 8000

# Health check configuration
# Checks /health endpoint which returns {"status": "healthy", ...}
# - interval: Check every 30 seconds
# - timeout: 10 seconds max per check
# - start_period: Allow 60 seconds for initial startup (heavy imports like MoviePy)
# - retries: 3 failures before marking unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command: Start FastAPI with uvicorn
# Listens on 0.0.0.0:8000 (all interfaces) so it's reachable from host
# In docker-compose, this is overridden with --reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

