#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
DEFAULT_PORT=8000
DEFAULT_MODEL="mock-model-1"
CONFIG_DIR="config/local/models"
DOCKER_COMPOSE_FILE="mocks/docker-compose.yml"

# Help function
function show_help() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -n, --name NAME     Name of the mock model (default: $DEFAULT_MODEL)"
  echo "  -p, --port PORT     Port to expose the mock model on (default: $DEFAULT_PORT)"
  echo "  -h, --help         Show this help message"
  echo ""
  echo "Example: $0 -n my-model -p 8080"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -n|--name)
      MODEL_NAME="$2"
      shift # past argument
      shift # past value
      ;;
    -p|--port)
      PORT="$2"
      shift # past argument
      shift # past value
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)    # unknown option
      echo -e "${RED}Error: Unknown option: $1${NC}"
      show_help
      exit 1
      ;;
  esac
done

# Set defaults if not provided
MODEL_NAME=${MODEL_NAME:-$DEFAULT_MODEL}
PORT=${PORT:-$DEFAULT_PORT}

# Validate port is a number
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
  echo -e "${RED}Error: Port must be a number${NC}"
  show_help
  exit 1
fi

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
endpoint_url: "http://$MODEL_NAME:8000/predict"
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

# Check if orchestrator is running and provide guidance if not
if ! docker ps --format '{{.Names}}' | grep -q 'orchestrator'; then
  echo -e "${YELLOW}Note: Orchestrator is not running. Please start it using the start_orchestrator.sh script.${NC}"
  echo -e "${YELLOW}The mock model will still start but won't be accessible through the orchestrator.${NC}"
  echo -e "${YELLOW}To start the orchestrator, run: ./scripts/start_orchestrator.sh${NC}"
  echo ""
  read -p "Press Enter to continue starting just the mock model..."
fi

# Start the mock model container
echo -e "${GREEN}Starting mock model '$MODEL_NAME' on port $PORT...${NC}

# Create a temporary docker-compose file for the specific model
TEMP_COMPOSE="/tmp/${MODEL_NAME}-docker-compose.yml"
cat > "$TEMP_COMPOSE" <<EOL
version: '3.8'
services:
  ${MODEL_NAME}:
    image: mock-model:latest
    build:
      context: ./mocks
      dockerfile: Dockerfile
    container_name: ${MODEL_NAME}
    environment:
      - MODEL_NAME=${MODEL_NAME}
      - PORT=8000
    ports:
      - "${PORT}:8000"
    networks:
      - ml-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

networks:
  ml-network:
    name: ml-network
    driver: bridge
EOL

# Start the mock model
docker-compose -f "$TEMP_COMPOSE" up -d

# Clean up the temporary file
rm -f "$TEMP_COMPOSE"

# Wait for the model to be ready
echo -e "${YELLOW}Waiting for $MODEL_NAME to be ready...${NC}
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
  exit 1
fi

echo -e "\n${GREEN}Mock model '$MODEL_NAME' is now running and ready!${NC}"
echo -e "Model endpoint: http://localhost:${PORT}/predict"
echo -e "Health check:   http://localhost:${PORT}/health"

# Only show orchestrator URL if orchestrator is running
if docker ps --format '{{.Names}}' | grep -q 'orchestrator'; then
  echo -e "\nYou can now send requests to the orchestrator at http://localhost:8000/api/v1/models/${MODEL_NAME}"
else
  echo -e "\n${YELLOW}Note: Orchestrator is not running. Start it with: ./scripts/start_orchestrator.sh${NC}"
fi

# Show example request
echo -e "\n${YELLOW}Example request:${NC}"
echo "curl -X POST http://localhost:8000/api/v1/models/${MODEL_NAME} \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"input\": \"test input\"}' | jq"

exit 0
