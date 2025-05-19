#!/bin/bash

# This script stops all running services and cleans up only mock model files.
# It deletes config/models/mock-model-*.yaml and docker-compose.mock-model-*.yml files.
# Any other config/models/*.yaml files (e.g., production or manually managed configs) will NOT be deleted.

# Get the project root directory
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

echo "Stopping all services..."

# Stop the orchestrator
cd "$PROJECT_ROOT" && docker compose down

# Stop all mock models
for compose_file in "$PROJECT_ROOT"/docker-compose.mock-model-*.yml; do
    if [ -f "$compose_file" ]; then
        echo "Stopping service from $compose_file"
        cd "$PROJECT_ROOT" && docker compose -f "$compose_file" down
    fi
done

# Remove any orphaned containers
cd "$PROJECT_ROOT" && docker compose down --remove-orphans

# Clean up any unused networks
docker network prune -f

# Remove all model configuration files
echo "Cleaning up model configurations..."
rm -f "$PROJECT_ROOT"/config/models/mock-model-*.yaml

# Remove docker compose files
echo "Cleaning up docker compose files..."
rm -f "$PROJECT_ROOT"/docker-compose.mock-model-*.yml

echo "All services stopped and cleaned up"
rm -f "$PROJECT_ROOT"/docker-compose.mock-model-*.yml

echo "All services stopped and cleaned up" 