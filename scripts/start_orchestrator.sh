#!/bin/bash

# Create docker-compose.yml for orchestrator if it doesn't exist
if [ ! -f "docker-compose.yml" ]; then
    cat > "docker-compose.yml" << EOF
version: "3.8"

services:
  orchestrator:
    build:
      context: .
      dockerfile: Dockerfile
    platform: linux/arm64/v8
    ports:
      - "8000:8000"
    volumes:
      - ./config/models:/app/config/models
    environment:
      - APP_NAME=orchestrator
      - APP_VERSION=1.0.0
      - DEBUG=true
      - HOST=0.0.0.0
      - PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    networks:
      - ml-orchestrator-network

networks:
  ml-orchestrator-network:
    driver: bridge
EOF
fi

# Start the orchestrator
docker compose up -d

echo "Orchestrator started on port 8000"
echo "Test the orchestrator health with: curl http://localhost:8000/health"
echo "Test model predictions with: curl -X POST http://localhost:8000/orchestrator/models/mock-model-1 -H \"Content-Type: application/json\" -d '{\"inputs\": {\"data\": [1, 2, 3, 4, 5]}, \"parameters\": {\"threshold\": 0.5}}'"
echo "List available models with: curl -H \"X-API-Key: dev-admin-key\" http://localhost:8000/admin/models" 