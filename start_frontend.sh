#!/bin/bash
# Start frontend development server
# Usage: ./start_frontend.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"

echo "🚀 Starting QuantumClip Frontend..."

# Check if node_modules exists
if [ ! -d "${FRONTEND_DIR}/node_modules" ]; then
    echo "📦 Installing dependencies..."
    cd "${FRONTEND_DIR}"
    npm install
fi

# Start frontend
echo "📡 Starting Vite development server..."
cd "${FRONTEND_DIR}"
npm run dev

