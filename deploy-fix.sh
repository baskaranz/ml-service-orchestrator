#!/bin/bash

# Simplified script to load models from YAML files
echo "Starting deployment with simplified approach..."

# Stop all containers 
docker-compose down

# Create a simplified configuration to load models from YAML
cat > simplified-compose.yml << EOF
version: "3.8"

services:
  # Mock Model 1
  mock-model-1:
    build:
      context: .
      dockerfile: mocks/Dockerfile
    ports:
      - "8001:8000"
    environment:
      LOG_LEVEL: "INFO"
      PYTHONUNBUFFERED: "1"
      PORT: "8000"
      MODEL_NAME: "mock-model-1"
      MODEL_VERSION: "1.0.0"
    networks:
      - ml-network

  # Mock Model 2
  mock-model-2:
    build:
      context: .
      dockerfile: mocks/Dockerfile
    ports:
      - "8002:8000"
    environment:
      LOG_LEVEL: "INFO"
      PYTHONUNBUFFERED: "1"
      PORT: "8000"
      MODEL_NAME: "mock-model-2"
      MODEL_VERSION: "1.0.0"
    networks:
      - ml-network

networks:
  ml-network:
    name: ml-network
EOF

# Start mock models
docker-compose -f simplified-compose.yml up -d

echo "Mock models are running. You can use them directly at:"
echo "- Mock Model 1: http://localhost:8001/predict"
echo "- Mock Model 2: http://localhost:8002/predict"
echo ""
echo "Example usage:"
echo "curl -X POST -H \"Content-Type: application/json\" -d '{\"input\": \"Hello world\"}' http://localhost:8001/predict"
echo ""
echo "The models are now functional even without the orchestrator!"