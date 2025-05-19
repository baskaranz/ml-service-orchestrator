#!/bin/bash

set -e

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <model-name> <port> <active> [description]"
    echo "Example: $0 model1 8001 true \"Test Model 1\""
    exit 1
fi

MODEL_NAME=$1
PORT=$2
ACTIVE=$3
DESCRIPTION=${4:-"Mock model ${MODEL_NAME}"}
CONFIG_DIR="$(pwd)/config/local/models"

# Create config directory if it doesn't exist
mkdir -p "${CONFIG_DIR}"

cat > "${CONFIG_DIR}/${MODEL_NAME}.yaml" <<EOL
id: ${MODEL_NAME}
name: "${MODEL_NAME}"
description: "${DESCRIPTION}"
endpoint_url: "http://host.docker.internal:${PORT}/predict"
active: ${ACTIVE}
platform:
  timeout: 30
  max_retries: 3
  circuit_breaker:
    failure_threshold: 5
    reset_timeout: 60
    half_open_timeout: 30
    success_threshold: 2
metadata:
  owner: "local-dev"
  version: "1.0.0"
  tags: ["local", "mock"]
  created_at: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
EOL

echo "✅ Generated config for ${MODEL_NAME} at ${CONFIG_DIR}/${MODEL_NAME}.yaml"
echo "   - Active: ${ACTIVE}"
echo "   - Endpoint: http://localhost:${PORT}"
echo "   - Health check: http://localhost:${PORT}/health"
