#!/bin/bash
# Kill existing backend process
echo "Stopping existing backend..."
PID=$(lsof -ti:8000)
if [ ! -z "$PID" ]; then
  kill -9 $PID
  echo "Backend stopped."
fi

# Start backend in background
echo "Starting backend..."
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
if [ -f "$(dirname "$0")/wait_for_backend.sh" ]; then
    "$(dirname "$0")/wait_for_backend.sh"
else
    # Fallback: simple wait loop
    for i in {1..30}; do
        if curl -s -f http://localhost:8000/docs > /dev/null 2>&1; then
            echo "✅ Backend is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Backend failed to start"
            exit 1
        fi
        sleep 2
    done
fi

echo "Backend is running (PID: $BACKEND_PID)"
wait $BACKEND_PID
