#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
MODEL_NAME="test-model"
PORT=8005
CONFIG_DIR="config/local/models"

# Ensure docker is running
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Error: Docker is not running${NC}"
  exit 1
fi

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Create model config file
CONFIG_FILE="$CONFIG_DIR/$MODEL_NAME.yaml"
cat > "$CONFIG_FILE" <<EOL
id: $MODEL_NAME
name: "$MODEL_NAME"
endpoint_url: "http://localhost:$PORT/predict"
active: true
timeout: 30.0
max_retries: 3
http2: false

# Health check configuration
health_check:
  enabled: true
  endpoint: "/health"
  interval: 30
  timeout: 5
  failure_threshold: 3
  success_threshold: 2

# Request headers
headers:
  Content-Type: "application/json"
  X-API-Version: "1.0"
  X-Environment: "local"

# Connection pooling
max_connections: 100
max_keepalive_connections: 50
keepalive_timeout: 60
pool_connections: 10
pool_maxsize: 100

# Authentication
auth:
  enabled: false

# Monitoring and logging
monitoring:
  enabled: true
  metrics_interval: 60
  log_level: "INFO"
EOL

echo -e "${GREEN}Created model configuration: $CONFIG_FILE${NC}"

# Create a temporary docker-compose file
echo -e "${GREEN}Starting mock model '$MODEL_NAME' on port $PORT...${NC}"

cat > /tmp/test-docker-compose.yml <<EOL
version: '3.8'
services:
  test-model:
    image: mock-model:latest
    build:
      context: ./mocks
      dockerfile: Dockerfile
    container_name: test-model
    environment:
      - MODEL_NAME=test-model
      - PORT=8000
    ports:
      - "8005:8000"
    networks:
      - ml-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

networks:
  ml-network:
    name: ml-network
    driver: bridge
EOL

# Start the mock model
docker-compose -f /tmp/test-docker-compose.yml up -d

# Wait for the model to be ready
echo -e "${YELLOW}Waiting for test-model to be ready...${NC}"
MAX_RETRIES=10
COUNTER=0

while [ $COUNTER -lt $MAX_RETRIES ]; do
  if curl -s "http://localhost:${PORT}/health" > /dev/null; then
    break
  fi
  echo -n "."
  sleep 2
  COUNTER=$((COUNTER + 1))
done

if [ $COUNTER -eq $MAX_RETRIES ]; then
  echo -e "\n${RED}Error: Timed out waiting for test-model to be ready${NC}"
  echo -e "${YELLOW}Check the logs with: docker logs test-model${NC}"
  exit 1
fi

echo -e "\n${GREEN}Mock model is now running and ready!${NC}"
echo -e "Model endpoint: http://localhost:${PORT}/predict"
echo -e "Health check:   http://localhost:${PORT}/health"
echo -e "\nTo stop the model: docker-compose -f /tmp/test-docker-compose.yml down"

echo -e "\n${YELLOW}Testing the model...${NC}"
curl -X POST http://localhost:8005/predict -H "Content-Type: application/json" -d '{"input": "test input"}'
