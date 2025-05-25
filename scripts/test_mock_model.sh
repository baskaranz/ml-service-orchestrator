#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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

# Start the mock model using the existing mock-model-1 configuration
# but with a different port and name
echo -e "${GREEN}Starting mock model '$MODEL_NAME' on port $PORT...${NC}

# Stop any existing test-model container
docker stop $MODEL_NAME 2>/dev/null || true
docker rm $MODEL_NAME 2>/dev/null || true

# Start a new container
docker run -d \
  --name $MODEL_NAME \
  -p $PORT:8000 \
  -e MODEL_NAME=$MODEL_NAME \
  -e PORT=8000 \
  --network ml-network \
  mock-model:latest

# Wait for the model to be ready
echo -e "${YELLOW}Waiting for $MODEL_NAME to be ready...${NC}"
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
  echo -e "\n${RED}Error: Timed out waiting for $MODEL_NAME to be ready${NC}"
  echo -e "${YELLOW}Check the logs with: docker logs $MODEL_NAME${NC}"
  exit 1
fi

echo -e "\n${GREEN}Mock model '$MODEL_NAME' is now running and ready!${NC}"
echo -e "Model endpoint: http://localhost:${PORT}/predict"
echo -e "Health check:   http://localhost:${PORT}/health"
echo -e "\n${YELLOW}Testing the model...${NC}"

# Test the model
curl -X POST http://localhost:$PORT/predict \
  -H "Content-Type: application/json" \
  -d '{"input": "test input"}'

echo -e "\n\n${YELLOW}To stop the model, run: docker stop $MODEL_NAME && docker rm $MODEL_NAME${NC}"
echo -e "${YELLOW}Configuration file: $CONFIG_FILE${NC}"

