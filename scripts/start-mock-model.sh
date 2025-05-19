#!/bin/bash

set -e

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <model-name> <port>"
    echo "Example: $0 model1 8001"
    exit 1
fi

MODEL_NAME=$1
PORT=$2
ACTIVE="true"

# Remove any existing container with the same name
docker rm -f "mock-${MODEL_NAME}" 2>/dev/null || true

# Create network if it doesn't exist
docker network create ml-network 2>/dev/null || true

# Create a temporary directory for the model server
TMP_DIR=$(mktemp -d)
cp "$(pwd)/mocks/model_server.py" "${TMP_DIR}/"
cp "$(pwd)/mocks/requirements.txt" "${TMP_DIR}/"

# Start new container
docker run -d \
    --name "mock-${MODEL_NAME}" \
    -p "${PORT}:8000" \
    -e MODEL_NAME="${MODEL_NAME}" \
    -e MODEL_VERSION="1.0.0" \
    -e ACTIVE="${ACTIVE}" \
    -e LOG_LEVEL="DEBUG" \
    --network ml-network \
    --health-cmd='curl -f http://localhost:8000/health || exit 1' \
    --health-interval=10s \
    --health-timeout=5s \
    --health-retries=3 \
    -v "${TMP_DIR}:/app" \
    python:3.11-slim bash -c "pip install -r /app/requirements.txt && cd /app && uvicorn model_server:app --host 0.0.0.0 --port 8000"

echo "Started mock model '${MODEL_NAME}' on port ${PORT}"
echo "Health check: http://localhost:${PORT}/health"
echo "To stop: docker stop mock-${MODEL_NAME}"

# Generate config for this model
if [ -f "$(pwd)/scripts/generate-model-config.sh" ]; then
    "$(pwd)/scripts/generate-model-config.sh" "${MODEL_NAME}" "${PORT}" "${ACTIVE}" "Mock model ${MODEL_NAME}"
fi
