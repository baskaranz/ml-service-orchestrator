#!/bin/bash

set -e

echo "🧹 Cleaning up Docker containers and network..."

# Stop and remove all mock model containers
docker ps -a --filter "name=mock-" --format "{{.Names}}" | xargs -r docker rm -f

# Stop and remove orchestrator
docker rm -f ml-orchestrator 2>/dev/null || true

# Remove network if no containers are using it
if [ "$(docker network inspect ml-network -f '{{.Containers | len}}' 2>/dev/null)" != "0" ]; then
    echo "Some containers are still using the network. Not removing network."
else
    docker network rm ml-network 2>/dev/null || true
fi

echo "✅ Cleanup complete!"
echo "Remaining containers:"
docker ps -a
