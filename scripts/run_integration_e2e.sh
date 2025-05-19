#!/bin/bash

set -euo pipefail

# Ensure the external Docker network exists
NETWORK_NAME="ml-orchestrator-network"
if ! docker network ls | grep -q "$NETWORK_NAME"; then
  echo "Creating external Docker network: $NETWORK_NAME"
  docker network create "$NETWORK_NAME"
else
  echo "Docker network $NETWORK_NAME already exists."
fi

# Paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
MOCKS_DIR="$SCRIPT_DIR/mocks"

# Model names and ports
MODELS=(mock-model-1 mock-model-2 mock-model-3)
PORTS=(8001 8002 8003)

# Start mock models first
MOCK_PIDS=()
for i in ${!MODELS[@]}; do
  bash "$MOCKS_DIR/start_mock_model.sh" "${MODELS[$i]}" "${PORTS[$i]}" &
  pid=$!
  MOCK_PIDS+=("$pid")
  echo "Started ${MODELS[$i]} on port ${PORTS[$i]} (PID $pid)"
done

# Wait for mock models health
for i in ${!PORTS[@]}; do
  MODEL_HEALTHY=0
  for j in {1..20}; do
    if curl -sf http://localhost:${PORTS[$i]}/health > /dev/null; then
      MODEL_HEALTHY=1
      echo "${MODELS[$i]} is healthy."
      break
    fi
    sleep 1
  done
  if [ "$MODEL_HEALTHY" -ne 1 ]; then
    echo "${MODELS[$i]} did not become healthy in time."
    exit 1
  fi
done

# Start orchestrator after mock models are healthy
bash "$SCRIPT_DIR/start_orchestrator.sh" &
ORCH_PID=$!
echo "Started orchestrator (PID $ORCH_PID)"

# Cleanup function
cleanup() {
  echo "\nCleaning up..."
  for pid in "${MOCK_PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  kill "$ORCH_PID" 2>/dev/null || true
  # Stop all services
  bash "$SCRIPT_DIR/stop_services.sh" || true
}
trap cleanup EXIT

# Wait for orchestrator health
ORCH_HEALTHY=0
for i in {1..30}; do
  if curl -sf http://localhost:8000/health > /dev/null; then
    ORCH_HEALTHY=1
    echo "Orchestrator is healthy."
    break
  fi
  sleep 2
done
if [ "$ORCH_HEALTHY" -ne 1 ]; then
  echo "Orchestrator did not become healthy in time."
  exit 1
fi

# Run integration tests
cd "$PROJECT_ROOT"
echo "Running integration tests..."
pytest -v tests/test_integration/

# Cleanup will be handled by trap 