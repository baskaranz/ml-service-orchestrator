#!/bin/bash
# Standard workflow for running the ML Service Orchestrator with mock models

echo "=== STEP 1: Clean up any existing containers ==="
docker-compose down
echo ""

echo "=== STEP 2: Start Orchestrator container ==="
docker-compose up -d orchestrator
echo "Waiting for orchestrator to fully initialize..."
sleep 10
echo ""

echo "=== STEP 3: Start Mock Model containers ==="
docker-compose up -d mock-model-1 mock-model-2
echo "Waiting for mock models to fully initialize..."
sleep 5
echo ""

echo "=== STEP 4: Verify containers are running ==="
docker-compose ps
echo ""

echo "=== STEP 5: Install required packages in orchestrator ==="
docker-compose exec orchestrator pip install -q requests
echo ""

echo "=== STEP 6: Register models with orchestrator ==="
echo "Registering mock-model-1..."
curl -X POST http://localhost:8000/admin/admin/models \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-admin-key" \
  -d '{
    "model": {
      "id": "mock-model-1",
      "name": "Mock Model 1",
      "endpoint_url": "http://mock-model-1:8000",
      "active": true,
      "timeout": 30.0,
      "max_retries": 3,
      "http2": false
    }
  }'
echo ""

echo "Registering mock-model-2..."
curl -X POST http://localhost:8000/admin/admin/models \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-admin-key" \
  -d '{
    "model": {
      "id": "mock-model-2",
      "name": "Mock Model 2",
      "endpoint_url": "http://mock-model-2:8000",
      "active": true,
      "timeout": 30.0,
      "max_retries": 3,
      "http2": false
    }
  }'
echo ""

echo "=== STEP 7: Verify models are registered ==="
echo "Listing models from orchestrator:"
curl -X GET http://localhost:8000/admin/admin/models \
  -H "X-API-Key: test-admin-key"
echo ""
echo ""

echo "=== STEP 8: Test direct access to mock models ==="
echo "Testing mock-model-1 directly:"
curl -X POST -H "Content-Type: application/json" \
  -d '{"input": "Hello from direct call"}' \
  http://localhost:8001/predict
echo ""
echo ""

echo "Testing mock-model-2 directly:"
curl -X POST -H "Content-Type: application/json" \
  -d '{"input": "Hello from direct call"}' \
  http://localhost:8002/predict
echo ""
echo ""

echo "=== STEP 9: Test access through orchestrator ==="
echo "Testing mock-model-1 via orchestrator:"
curl -X POST -H "Content-Type: application/json" \
  -d '{"input": "Hello via orchestrator"}' \
  http://localhost:8000/orchestrator/models/mock-model-1
echo ""
echo ""

echo "Testing mock-model-2 via orchestrator:"
curl -X POST -H "Content-Type: application/json" \
  -d '{"input": "Hello via orchestrator"}' \
  http://localhost:8000/orchestrator/models/mock-model-2
echo ""
echo ""

echo "=== Workflow complete ==="
echo "You can continue to use the models either:"
echo "- Directly: curl -X POST -H \"Content-Type: application/json\" -d '{\"input\": \"Hello\"}' http://localhost:8001/predict"
echo "- Via orchestrator: curl -X POST -H \"Content-Type: application/json\" -d '{\"input\": \"Hello\"}' http://localhost:8000/orchestrator/models/mock-model-1"
echo ""
echo "To stop all services: docker-compose down"