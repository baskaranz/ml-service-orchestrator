#!/bin/bash

if [ $# -ne 2 ]; then
  echo "Usage: $0 <model_name> <port>"
  exit 1
fi

MODEL_NAME=$1
PORT=$2
CONFIG_DIR="config/models"
COMPOSE_FILE="docker-compose.${MODEL_NAME}.yml"

mkdir -p $CONFIG_DIR

cat > $CONFIG_DIR/${MODEL_NAME}.yaml <<EOF
id: ${MODEL_NAME}
name: ${MODEL_NAME}
description: "Error demo mock model for orchestrator error handling demo"
endpoint_url: http://${MODEL_NAME}:${PORT}
version: "1.0.0"
active: true
timeout: 5.0
max_retries: 2
type: classification
metadata:
  error_demo: true
llm_provider:
  provider: "none"
EOF

cat > $COMPOSE_FILE <<EOF
services:
  ${MODEL_NAME}:
    build:
      context: .
      dockerfile: Dockerfile.mock
    container_name: lasso-${MODEL_NAME}-1
    command: ["python", "-u", "/app/mocks/model_mock_error_demo.py", "--port", "${PORT}", "--model-name", "${MODEL_NAME}"]
    ports:
      - "${PORT}:${PORT}"
    environment:
      - MODEL_NAME=${MODEL_NAME}
      - MODEL_VERSION=1.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${PORT}/health"]
      interval: 5s
      timeout: 2s
      retries: 5
    networks:
      - ml-orchestrator-network
networks:
  ml-orchestrator-network:
    external: true
EOF

docker compose -f "$COMPOSE_FILE" up -d

echo "Error demo mock model ${MODEL_NAME} started on port ${PORT}"
echo "Configuration file created at $CONFIG_DIR/${MODEL_NAME}.yaml"
echo "Test error handling through orchestrator with:"
echo "curl -X POST http://localhost:8000/orchestrator/models/${MODEL_NAME} -H 'Content-Type: application/json' -d '{\"inputs\": {\"error_type\": \"server\"}}'" 