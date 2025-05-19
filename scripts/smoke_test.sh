#!/bin/bash
# Smoke test for Docker workflow
# This will start the orchestrator and one mock model, run a test, and clean up

set -e  # Exit on any error

echo "===== DOCKER WORKFLOW SMOKE TEST ====="
echo

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# First stop any running services
echo -e "${YELLOW}Stopping any existing services...${NC}"
./scripts/stop_services.sh

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}ERROR: Docker is not running or not installed${NC}"
  exit 1
fi

echo -e "${YELLOW}Starting orchestrator...${NC}"
./scripts/start_orchestrator.sh

# Wait for orchestrator to start
echo "Waiting for orchestrator to be ready..."
for i in $(seq 1 30); do
  if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ Orchestrator is running${NC}"
    break
  fi
  
  if [ $i -eq 30 ]; then
    echo -e "${RED}✗ Orchestrator startup check timed out${NC}"
    echo -e "${YELLOW}Checking container logs...${NC}"
    docker logs $(docker ps -qf "name=orchestrator")
    
    # Let's see if it's actually responding
    HEALTH_CHECK=$(curl -s http://localhost:8000/health || echo "failed")
    if [[ "$HEALTH_CHECK" == *"healthy"* ]]; then
      echo -e "${GREEN}✓ Orchestrator is actually responding to health checks${NC}"
      break
    else
      echo -e "${RED}✗ Orchestrator health check failed: $HEALTH_CHECK${NC}"
      exit 1
    fi
  fi
  
  echo -n "."
  sleep 1
done

echo -e "${YELLOW}Starting mock model...${NC}"
./scripts/mocks/start_mock_model.sh smoke-test-model 8001

# Wait for model to be registered
echo "Waiting for model to be registered..."
sleep 5

echo -e "${YELLOW}Testing model prediction...${NC}"
PREDICTION_RESULT=$(curl -s -X POST http://localhost:8000/orchestrator/models/smoke-test-model \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"data": [1, 2, 3, 4, 5]}, "parameters": {"threshold": 0.5}}')

if echo "$PREDICTION_RESULT" | grep -q "predictions"; then
  echo -e "${GREEN}✓ Model prediction test passed${NC}"
else
  echo -e "${RED}✗ Model prediction test failed${NC}"
  echo "Result: $PREDICTION_RESULT"
  exit 1
fi

echo
echo -e "${GREEN}===== SMOKE TEST PASSED! =====${NC}"
echo

# Clean up
read -p "Do you want to clean up all services now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo -e "${YELLOW}Cleaning up services...${NC}"
  ./scripts/stop_services.sh
  echo -e "${GREEN}✓ All services stopped and cleaned up${NC}"
else
  echo -e "${YELLOW}Services are still running. You can stop them later with:${NC}"
  echo "./scripts/stop_services.sh"
fi
