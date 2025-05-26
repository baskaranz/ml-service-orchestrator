#!/bin/bash
set -e

# Default values
PORT_START=9001
NUM_MODELS=2
DOCKER_COMPOSE_FILE="docker-compose.mock.yml"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -n|--num-models)
      NUM_MODELS="$2"
      shift # past argument
      shift # past value
      ;;
    -p|--port-start)
      PORT_START="$2"
      shift # past argument
      shift # past value
      ;;
    -f|--file)
      DOCKER_COMPOSE_FILE="$2"
      shift # past argument
      shift # past value
      ;;
    *)
      echo "Unknown parameter: $1"
      exit 1
      ;;
  esac
done

# Create docker-compose file
echo "Generating $DOCKER_COMPOSE_FILE with $NUM_MODELS mock models starting at port $PORT_START..."

cat > $DOCKER_COMPOSE_FILE <<EOL
version: "3.8"

services:
EOL

# Generate services for each model
for ((i=0; i<NUM_MODELS; i++)); do
  PORT=$((PORT_START + i))
  MODEL_NAME="mock-model-$((i + 1))"

  cat >> $DOCKER_COMPOSE_FILE <<EOL
  ${MODEL_NAME}:
    build:
      context: .
      dockerfile: mocks/Dockerfile.mock
    environment:
      - MODEL_NAME=${MODEL_NAME}
      - PORT=${PORT}
      - MODEL_VERSION=1.0.0
    ports:
      - "${PORT}:${PORT}"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${PORT}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    networks:
      - mock-network
EOL

done

# Add network configuration
cat >> $DOCKER_COMPOSE_FILE <<EOL
networks:
  mock-network:
    driver: bridge
EOL

echo "Created $DOCKER_COMPOSE_FILE with $NUM_MODELS mock models"
echo "To start the mock models, run:"
echo "docker-compose -f $DOCKER_COMPOSE_FILE up --build -d"
