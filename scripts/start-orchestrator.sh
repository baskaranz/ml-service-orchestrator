#!/bin/bash

set -e

# Default port
PORT=${1:-8000}
CONFIG_DIR="$(pwd)/config"

# Create network if it doesn't exist
docker network create ml-network 2>/dev/null || true

echo "🚀 Starting ML Orchestrator on port ${PORT}..."

# Stop and remove existing container if it exists
docker rm -f ml-orchestrator 2>/dev/null || true

# Build the orchestrator image if it doesn't exist
if [ -z "$(docker images -q ml-orchestrator 2>/dev/null)" ]; then
    echo "Building orchestrator image..."
    docker build -t ml-orchestrator .
fi

# Start the orchestrator
docker run -d \
    --name ml-orchestrator \
    -p "${PORT}:8000" \
    -v "$(pwd)/config:/app/config" \
    -e APP_ENV=local \
    -e LOG_LEVEL=DEBUG \
    -e MODELS_DIR=/app/config/local/models \
    -e CONFIG_DIR=/app/config \
    -e CONFIG_PATH=/app/config \
    -v ${PWD}/config:/app/config \
    --network ml-network \
    --add-host=host.docker.internal:host-gateway \
    ml-orchestrator uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
    --reload-dir /app/app \
    --reload-dir /app/config \
    --reload-include '*.yaml' \
    --reload-include '*.yml' \
    --reload-include '*.json' \
    --reload-include '*.py'

echo "✅ Orchestrator started successfully!"
echo "   - API Docs: http://localhost:${PORT}/docs"
echo "   - Health: http://localhost:${PORT}/health"
echo "   - Models: http://localhost:${PORT}/api/v1/models"
echo "\nTo stop: docker stop ml-orchestrator"
