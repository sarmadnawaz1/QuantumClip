# Docker Setup Guide - QuantumClip

## Overview

This document describes the Docker configuration for QuantumClip and how to reliably start all services.

## Services

### Database (PostgreSQL)
- **Container**: `shazi_db`
- **Port**: `5432:5432`
- **Health Check**: `pg_isready -U shazi`
- **Start Period**: 10s
- **Purpose**: Stores users, videos, and application data

### Redis
- **Container**: `shazi_redis`
- **Port**: `6379:6379`
- **Health Check**: `redis-cli ping`
- **Start Period**: 5s
- **Purpose**: Message broker for Celery task queue

### Backend (FastAPI)
- **Container**: `shazi_backend`
- **Port**: `8000:8000`
- **Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- **Health Check**: `curl -f http://localhost:8000/health`
- **Start Period**: 60s (allows time for heavy imports like MoviePy)
- **Endpoints**:
  - API: `http://localhost:8000/api/v1`
  - Docs: `http://localhost:8000/docs`
  - Health: `http://localhost:8000/health`

### Celery Worker
- **Container**: `shazi_celery_worker`
- **Command**: `celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2`
- **Depends On**: Redis (healthy), DB (healthy), Backend (healthy)
- **Purpose**: Processes background video generation tasks

### Celery Beat
- **Container**: `shazi_celery_beat`
- **Command**: `celery -A app.tasks.celery_app beat --loglevel=info`
- **Depends On**: Redis (healthy), DB (healthy)
- **Purpose**: Schedules periodic tasks

### Frontend (React/Vite)
- **Container**: `shazi_frontend`
- **Port**: `3000:3000`
- **Depends On**: Backend (healthy)
- **Purpose**: React frontend development server

## Starting Services

### Start All Services

```bash
cd web-app
docker-compose up --build
```

### Start Specific Services

```bash
# Start only backend and dependencies
docker-compose up db redis backend

# Start backend and frontend
docker-compose up db redis backend frontend
```

### Start in Background (Detached Mode)

```bash
docker-compose up -d
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

## Health Checks

### Manual Health Check

```bash
# Check backend health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"...","environment":"..."}
```

### Check Service Status

```bash
# List all services and their status
docker-compose ps

# Check health status
docker inspect shazi_backend | grep -A 10 Health
```

## Startup Sequence

1. **PostgreSQL** starts and becomes healthy (~10s)
2. **Redis** starts and becomes healthy (~5s)
3. **Backend** waits for DB and Redis, then:
   - Initializes database tables
   - Verifies schema
   - Starts uvicorn server
   - Becomes healthy (~60s total, including heavy imports)
4. **Celery Worker** waits for Redis, DB, and Backend, then starts
5. **Celery Beat** waits for Redis and DB, then starts
6. **Frontend** waits for Backend, then starts Vite dev server

## Troubleshooting

### Backend Not Starting

1. **Check logs**:
   ```bash
   docker-compose logs backend
   ```

2. **Check if port is in use**:
   ```bash
   lsof -i :8000
   ```

3. **Verify database connection**:
   ```bash
   docker-compose exec backend python -c "from app.core.config import settings; print(settings.database_url)"
   ```

4. **Check health endpoint manually**:
   ```bash
   docker-compose exec backend curl http://localhost:8000/health
   ```

### Backend Health Check Failing

- **Symptom**: Container shows as "unhealthy" in `docker-compose ps`
- **Cause**: Backend takes longer than 60s to start (heavy imports)
- **Solution**: Increase `start_period` in `docker-compose.yml` healthcheck

### Frontend Can't Connect to Backend

- **Symptom**: Frontend shows "Connection refused" or API errors
- **Cause**: Frontend started before backend was healthy
- **Solution**: Ensure `depends_on` uses `condition: service_healthy`

### Database Connection Errors

- **Symptom**: Backend logs show "connection refused" to database
- **Cause**: Backend started before database was ready
- **Solution**: Verify `depends_on` has `condition: service_healthy` for db

## Testing the Setup

### 1. Start Services

```bash
cd web-app
docker-compose up --build
```

### 2. Watch Logs

In another terminal:
```bash
docker-compose logs -f backend
```

You should see:
```
============================================================
🚀 Starting QuantumClip Backend Application
============================================================
Environment: development
Debug mode: True
Database URL: postgresql://...
Initializing database...
✅ Database tables created/verified
✅ Database schema verified
✅ Database initialized successfully
============================================================
✅ Application startup complete - ready to accept requests
📡 Server will listen on: http://0.0.0.0:8000
📚 API docs available at: http://0.0.0.0:8000/docs
❤️  Health check: http://0.0.0.0:8000/health
============================================================
```

### 3. Verify Health

```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status":"healthy","version":"...","environment":"..."}
```

### 4. Check API Docs

Open in browser: `http://localhost:8000/docs`

### 5. Verify Frontend

Open in browser: `http://localhost:3000`

## Production Setup

For production, use the nginx profile:

```bash
docker-compose --profile production up -d
```

This starts:
- All services above
- Nginx reverse proxy (ports 80, 443)

## Key Improvements Made

1. **Health Checks**: All services have proper health checks with `start_period` to allow initialization time
2. **Dependencies**: Services use `condition: service_healthy` instead of just `depends_on`
3. **Backend Health Check**: Increased `start_period` to 60s to account for heavy imports (MoviePy, etc.)
4. **Startup Logging**: Backend now logs clear startup messages showing progress
5. **No Fixed Sleeps**: Removed fragile `sleep 5 && curl` patterns in favor of proper health checks
6. **Error Visibility**: Failures are logged clearly and containers exit with non-zero status

## Manual Testing Checklist

- [ ] `docker-compose up --build` starts all services
- [ ] Backend logs show startup sequence clearly
- [ ] `curl http://localhost:8000/health` returns `{"status":"healthy",...}`
- [ ] `curl http://localhost:8000/docs` returns HTML (API docs)
- [ ] Frontend loads at `http://localhost:3000`
- [ ] No "Backend still starting..." spam in logs
- [ ] Services show as "healthy" in `docker-compose ps`
- [ ] Restarting backend (`docker-compose restart backend`) works reliably

