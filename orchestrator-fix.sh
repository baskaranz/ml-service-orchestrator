#!/bin/bash

# Script to fix the HTTP client in the orchestrator container
# This script should be run when the orchestrator container is running

# Stop all containers
echo "Stopping all containers..."
docker-compose down

# Copy the fixed HTTP client
echo "Copying fixed HTTP client..."
cp app/utils/http_fixed.py app/utils/http.py

# Rebuild and start containers
echo "Building and starting containers..."
docker-compose build orchestrator
docker-compose up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Install requests package in orchestrator container
echo "Installing requests package in orchestrator container..."
docker-compose exec orchestrator pip install requests httpx

# Reload the configuration
echo "Reloading orchestrator configuration..."
docker-compose exec orchestrator curl -X POST -H "X-API-Key: test-admin-key" http://localhost:8000/admin/admin/reload

echo "Fix applied. Testing connection to models..."
docker-compose exec orchestrator python -c "import requests; print(requests.post('http://lasso-mock-model-1-1:8000/predict', json={'input': 'Hello world'}).json())"

echo "Done!"