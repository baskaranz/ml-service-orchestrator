# ML Orchestrator + Mock Model APIs: Docker Run Instructions

This guide provides step-by-step instructions for running the ML Orchestrator and mock model APIs using Docker.

## Table of Contents

1. [Setup](#setup)
2. [Starting the Orchestrator](#starting-the-orchestrator)
3. [Starting Mock Models](#starting-mock-models)
4. [Testing the System](#testing-the-system)
5. [Testing Error Scenarios](#testing-error-scenarios)
6. [Stopping All Services](#stopping-all-services)

## Setup

Ensure you have Docker and Docker Compose installed on your system.

## Starting the Orchestrator

Start the orchestrator using the provided script:

```bash
./scripts/start_orchestrator.sh
```

This will build and start the orchestrator container on port 8000.

## Starting Mock Models

You can create and start any number of mock models with custom names and ports. For example:

```bash
# Start a mock model with a custom name and port
./scripts/mocks/start_mock_model.sh my-custom-model 9001

# Start multiple mock models
./scripts/mocks/start_mock_model.sh mock-model-1 8001
./scripts/mocks/start_mock_model.sh mock-model-2 8002
```

Each command will create a model config and start a Docker container for that model.

## Testing the System

After starting the orchestrator and at least one mock model, you can test the setup:

```bash
# Check orchestrator health
curl http://localhost:8000/health

# List registered models (requires API key)
curl -H "X-API-Key: dev-admin-key" http://localhost:8000/admin/models

# Make predictions through orchestrator (replace <model_name> as needed)
curl -X POST http://localhost:8000/orchestrator/models/mock-model-1 \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"data": [1, 2, 3, 4, 5]}, "parameters": {"threshold": 0.5}}'
```

## Testing Error Scenarios

The orchestrator now supports advanced error handling and retry logic. You can test different error scenarios using the error-test-model:

```bash
# Test rate limit error (429)
curl -X POST http://localhost:8000/orchestrator/models/error-test-model \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"error_type": "rate_limit"}}'

# Test authentication error (401)
curl -X POST http://localhost:8000/orchestrator/models/error-test-model \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"error_type": "auth"}}'

# Test input validation error (422)
curl -X POST http://localhost:8000/orchestrator/models/error-test-model \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"error_type": "input_validation"}}'

# Test permanent error (500)
curl -X POST http://localhost:8000/orchestrator/models/error-test-model \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"error_type": "permanent"}}'
```

### Observing Retry Behavior

To observe the orchestrator's retry behavior, check the logs:

```bash
docker logs lasso-orchestrator-1 --tail 100
```

This will show detailed logs, including retry attempts, error classification, and when the orchestrator stops retrying.

## Stopping All Services

To stop the orchestrator and all running mock models, run:

```bash
./scripts/stop_services.sh
```

This will stop and clean up all Docker containers and networks related to the orchestrator and mock models.
