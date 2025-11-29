#!/bin/bash
# Wait for FastAPI backend to be ready
# This script retries until the backend responds successfully

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ENDPOINT="${ENDPOINT:-/docs}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-30}"
RETRY_INTERVAL="${RETRY_INTERVAL:-2}"

echo "⏳ Waiting for backend to be ready at ${BACKEND_URL}${ENDPOINT}..."

attempt=0
while [ $attempt -lt $MAX_ATTEMPTS ]; do
    attempt=$((attempt + 1))
    
    # Try to curl the endpoint
    if curl -s -f "${BACKEND_URL}${ENDPOINT}" > /dev/null 2>&1; then
        echo "✅ Backend is ready! (attempt $attempt/$MAX_ATTEMPTS)"
        exit 0
    fi
    
    # Print waiting message
    if [ $((attempt % 5)) -eq 0 ]; then
        echo "   Still waiting... (attempt $attempt/$MAX_ATTEMPTS)"
    else
        echo -n "."
    fi
    
    # Wait before next attempt
    sleep $RETRY_INTERVAL
done

echo ""
echo "❌ Backend failed to start after $MAX_ATTEMPTS attempts (${MAX_ATTEMPTS} × ${RETRY_INTERVAL}s = $((MAX_ATTEMPTS * RETRY_INTERVAL))s)"
echo "   Check backend logs for errors"
exit 1

