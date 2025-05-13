#!/bin/bash

echo "Stopping all services..."

# Stop the orchestrator
docker compose down

# Stop all mock models
for compose_file in docker-compose.mock-model-*.yml; do
    if [ -f "$compose_file" ]; then
        echo "Stopping service from $compose_file"
        docker compose -f "$compose_file" down
    fi
done

# Remove any orphaned containers
docker compose down --remove-orphans

# Clean up any unused networks
docker network prune -f

# Remove model configuration files from config/models
rm -f config/models/mock-model-*.yaml

echo "All services stopped and cleaned up" 