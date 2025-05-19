#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    # Stop all mock models
    pkill -f "start_mock_model.sh" || true
    # Stop orchestrator
    docker compose down || true
    # Remove network
    docker network rm ml-orchestrator-network || true
}

# Set up cleanup on script exit
trap cleanup EXIT

# Create network if it doesn't exist
docker network create ml-orchestrator-network || true

# Start mock models in background
echo "Starting mock models..."
"$SCRIPT_DIR/mocks/start_mock_model.sh" mock-model-1 8001 &
"$SCRIPT_DIR/mocks/start_mock_model.sh" mock-model-2 8002 &
"$SCRIPT_DIR/mocks/start_mock_model.sh" mock-model-3 8003 &

# Wait for mock models to start
echo "Waiting for mock models to start..."
sleep 10

# Start orchestrator
echo "Starting orchestrator..."
"$SCRIPT_DIR/start_orchestrator.sh"

# Wait for orchestrator to be healthy
echo "Waiting for orchestrator to be healthy..."
sleep 10

# Run integration tests
echo "Running integration tests..."
pytest tests/test_integration -v

# The cleanup function will be called automatically on exit 