#!/bin/bash

# Test the full workflow of the orchestrator and mock models

echo "=== Testing full workflow ==="
echo

echo "1. Cleaning up any existing services..."
./scripts/stop_services.sh

echo "2. Checking Docker network..."
NETWORK_NAME="ml-orchestrator-network"
if ! docker network ls | grep -q "$NETWORK_NAME"; then
    echo "   Creating Docker network: $NETWORK_NAME"
    docker network create "$NETWORK_NAME"
else
    echo "   Docker network $NETWORK_NAME already exists"
fi

echo "3. Starting the orchestrator..."
./scripts/start_orchestrator.sh

# Wait for orchestrator to be ready
echo "   Waiting for orchestrator to be ready..."
sleep 10

# Check orchestrator health
echo "4. Testing orchestrator health..."
HEALTH_STATUS=$(curl -s http://localhost:8000/health)
if [[ "$HEALTH_STATUS" == *"OK"* ]]; then
    echo "   ✅ Orchestrator is healthy: $HEALTH_STATUS"
else
    echo "   ❌ Orchestrator health check failed: $HEALTH_STATUS"
    echo "   Stopping workflow test"
    exit 1
fi

# Start mock models
echo "5. Starting mock models..."
./scripts/mocks/start_mock_model.sh mock-model-1 8001
./scripts/mocks/start_mock_model.sh mock-model-2 8002

# Wait for models to be ready
echo "   Waiting for models to be ready..."
sleep 10

# Test model through orchestrator
echo "6. Testing model prediction through orchestrator..."
MODEL1_RESPONSE=$(curl -s -X POST http://localhost:8000/orchestrator/models/mock-model-1 \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"data": [1, 2, 3, 4, 5]}, "parameters": {"threshold": 0.5}}')

if [[ "$MODEL1_RESPONSE" == *"predictions"* ]]; then
    echo "   ✅ Model 1 prediction successful"
else
    echo "   ❌ Model 1 prediction failed: $MODEL1_RESPONSE"
fi

MODEL2_RESPONSE=$(curl -s -X POST http://localhost:8000/orchestrator/models/mock-model-2 \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"data": [1, 2, 3, 4, 5]}, "parameters": {"threshold": 0.5}}')

if [[ "$MODEL2_RESPONSE" == *"predictions"* ]]; then
    echo "   ✅ Model 2 prediction successful"
else
    echo "   ❌ Model 2 prediction failed: $MODEL2_RESPONSE"
fi

echo
echo "=== Testing error scenarios ==="

# Start error test model
echo "7. Starting error test model..."
./scripts/mocks/start_mock_model.sh error-test-model 8003

# Wait for model to be ready
echo "   Waiting for error test model to be ready..."
sleep 10

# Test rate limit error
echo "8. Testing rate limit error..."
curl -s -X POST http://localhost:8000/orchestrator/models/error-test-model \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"error_type": "rate_limit"}}' > /dev/null

# Test auth error
echo "9. Testing authentication error..."
curl -s -X POST http://localhost:8000/orchestrator/models/error-test-model \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"error_type": "auth"}}' > /dev/null

echo
echo "=== Workflow test completed ==="
echo "To clean up all services, run: ./scripts/stop_services.sh"
