#!/bin/bash
# Direct model access workflow for the mock models

echo "=== STEP 1: Clean up any existing containers ==="
docker-compose -f simplified-compose.yml down
echo ""

echo "=== STEP 2: Start Mock Model containers ==="
docker-compose -f simplified-compose.yml up -d
echo "Waiting for mock models to fully initialize..."
sleep 5
echo ""

echo "=== STEP 3: Verify containers are running ==="
docker-compose -f simplified-compose.yml ps
echo ""

echo "=== STEP 4: Test direct access to mock models ==="
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

echo "=== Direct Model Workflow complete ==="
echo "You can continue to use the models directly with:"
echo "curl -X POST -H \"Content-Type: application/json\" -d '{\"input\": \"Hello\"}' http://localhost:8001/predict"
echo ""
echo "To stop all services: docker-compose -f simplified-compose.yml down"