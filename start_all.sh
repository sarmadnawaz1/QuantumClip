#!/bin/bash
# Start both backend and frontend
# Usage: ./start_all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting QuantumClip Application..."
echo ""

# Start backend in background
echo "📡 Starting Backend..."
"${SCRIPT_DIR}/start_backend.sh" &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend
echo ""
echo "📡 Starting Frontend..."
"${SCRIPT_DIR}/start_frontend.sh" &
FRONTEND_PID=$!

# Wait for both processes
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true; exit 0" INT TERM

wait $BACKEND_PID $FRONTEND_PID

