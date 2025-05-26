#!/bin/bash
set -e

# Default values
PORT_START=9001
NUM_MODELS=2

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -n|--num-models)
      NUM_MODELS="$2"
      shift # past argument
      shift # past value
      ;;
    -p|--port-start)
      PORT_START="$2"
      shift # past argument
      shift # past value
      ;;
    *)
      echo "Unknown parameter: $1"
      exit 1
      ;;
  esac
done

# Test each model
for ((i=0; i<NUM_MODELS; i++)); do
  PORT=$((PORT_START + i))
  MODEL_NAME="mock-model-$((i + 1))"
  URL="http://localhost:${PORT}"

  echo -e "\nTesting ${MODEL_NAME} at ${URL}..."

  # Test health endpoint
  echo -n "  Health check: "
  curl -s -f "${URL}/health" || echo "Failed"

  # Test predict endpoint
  echo -n "  Predict: "
  curl -s -X POST "${URL}/predict" \
    -H "Content-Type: application/json" \
    -d '{"inputs": {}}' || echo "Failed"
done

echo -e "\nAll tests completed!"
