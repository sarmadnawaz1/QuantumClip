#!/bin/bash
# Start backend and wait for it to be ready
# Usage: ./start_backend.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/web-app/backend"

echo "🚀 Starting QuantumClip Backend..."

# Check if venv exists
if [ ! -d "${BACKEND_DIR}/venv" ]; then
    echo "❌ Virtual environment not found. Please create it first:"
    echo "   cd ${BACKEND_DIR} && python -m venv venv"
    exit 1
fi

# Activate virtual environment
source "${BACKEND_DIR}/venv/bin/activate"

# Start backend in background
echo "📡 Starting FastAPI server..."
cd "${BACKEND_DIR}"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/quantumclip_backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
if [ -f "${BACKEND_DIR}/wait_for_backend.sh" ]; then
    "${BACKEND_DIR}/wait_for_backend.sh"
else
    # Fallback: simple retry loop
    MAX_ATTEMPTS=30
    RETRY_INTERVAL=2
    attempt=0
    
    while [ $attempt -lt $MAX_ATTEMPTS ]; do
        attempt=$((attempt + 1))
        
        if curl -s -f http://localhost:8000/docs > /dev/null 2>&1; then
            echo "✅ Backend is ready! (attempt $attempt/$MAX_ATTEMPTS)"
            break
        fi
        
        if [ $attempt -eq $MAX_ATTEMPTS ]; then
            echo "❌ Backend failed to start after $MAX_ATTEMPTS attempts"
            echo "   Check logs: tail -f /tmp/quantumclip_backend.log"
            kill $BACKEND_PID 2>/dev/null || true
            exit 1
        fi
        
        if [ $((attempt % 5)) -eq 0 ]; then
            echo "   Still waiting... (attempt $attempt/$MAX_ATTEMPTS)"
        else
            echo -n "."
        fi
        
        sleep $RETRY_INTERVAL
    done
fi

echo ""
echo "✅ Backend is running!"
echo "   - API: http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo "   - PID: $BACKEND_PID"
echo "   - Logs: tail -f /tmp/quantumclip_backend.log"
echo ""
echo "Press Ctrl+C to stop the backend"

# Wait for backend process
trap "echo ''; echo 'Stopping backend...'; kill $BACKEND_PID 2>/dev/null || true; exit 0" INT TERM
wait $BACKEND_PID

