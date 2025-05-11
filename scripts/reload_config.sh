#!/bin/bash

# Script to reload configurations without restarting the service

# Set default values
HOST=${HOST:-localhost}
PORT=${PORT:-8000}
API_KEY=${ADMIN_API_KEY:-}

# Construct the API key header
if [ -n "$API_KEY" ]; then
  API_KEY_HEADER="-H \"X-API-Key: $API_KEY\""
else
  API_KEY_HEADER=""
fi

# Make the request to reload configurations
echo "Reloading configurations..."

# Build the command
CMD="curl -X POST http://$HOST:$PORT/admin/reload $API_KEY_HEADER"

# Execute the command
eval $CMD

echo -e "\nConfiguration reload complete."