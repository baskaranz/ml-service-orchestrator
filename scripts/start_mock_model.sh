#!/bin/bash

# Check if model name and port are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <model_name> <port>"
    echo "Example: $0 mock-model-1 8001"
    exit 1
fi

MODEL_NAME=$1
PORT=$2

# Create model configuration directory if it doesn't exist
mkdir -p config/models

# Create model configuration file
cat > "config/models/${MODEL_NAME}.yaml" << EOF
id: ${MODEL_NAME}
name: ${MODEL_NAME}
description: Mock model for testing
endpoint_url: http://${MODEL_NAME}:${PORT}
version: 1.0.0
active: true
timeout: 30.0
max_retries: 3
type: classification
metadata:
  framework: mock
  tags: [test, dummy]
llm_provider:
  type: huggingface
  model_name: test-model
  timeout: 30
  max_retries: 3
EOF

# Create Docker Compose file for the mock model
cat > "docker-compose.${MODEL_NAME}.yml" << EOF
version: "3.8"

services:
  ${MODEL_NAME}:
    build:
      context: .
      dockerfile: Dockerfile.mock
    ports:
      - "${PORT}:${PORT}"
    environment:
      - MODEL_NAME=${MODEL_NAME}
      - MODEL_VERSION=1.0.0
      - PORT=${PORT}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:${PORT}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - ml-orchestrator-network

networks:
  ml-orchestrator-network:
    driver: bridge
EOF

# Start the mock model container
docker compose -f "docker-compose.${MODEL_NAME}.yml" up -d

echo "Mock model ${MODEL_NAME} started on port ${PORT}"
echo "Configuration file created at config/models/${MODEL_NAME}.yaml"
echo "Test the model directly with: curl -X POST http://localhost:${PORT}/predict -H \"Content-Type: application/json\" -d '{\"inputs\": {\"data\": [1, 2, 3, 4, 5]}, \"parameters\": {\"threshold\": 0.5}}'"
echo "Test through orchestrator with: curl -X POST http://localhost:8000/orchestrator/models/${MODEL_NAME} -H \"Content-Type: application/json\" -d '{\"inputs\": {\"data\": [1, 2, 3, 4, 5]}, \"parameters\": {\"threshold\": 0.5}}'" 