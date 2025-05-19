#!/bin/bash

# Script to check the health of the orchestrator service

# Set default values
HOST=${HOST:-localhost}
PORT=${PORT:-8000}
DETAILED=${DETAILED:-false}

# Determine the endpoint
if [ "$DETAILED" = "true" ]; then
  ENDPOINT="/health/details"
else
  ENDPOINT="/health"
fi

# Make the request
echo "Checking health at http://$HOST:$PORT$ENDPOINT..."
curl -s http://$HOST:$PORT$ENDPOINT | jq .

# Check exit status
STATUS=$?
if [ $STATUS -ne 0 ]; then
  echo "Health check failed with status $STATUS"
  exit 1
fi