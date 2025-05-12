# ML Orchestrator + Dummy Model APIs: Run Instructions

This guide provides detailed instructions for setting up, running, and testing the ML Orchestrator service with the dummy model APIs.

## Table of Contents

1. [Setup](#setup)
2. [Creating Dummy Models](#creating-dummy-models)
3. [Running Dummy Models](#running-dummy-models)
4. [Running the Orchestrator](#running-the-orchestrator)
5. [Testing the Complete System](#testing-the-complete-system)
6. [Calling APIs Directly](#calling-apis-directly)
7. [Advanced Usage](#advanced-usage)
8. [Troubleshooting](#troubleshooting)

## Setup

Before starting, make sure you have the development environment set up:

```bash
# Set up development environment
./scripts/setup_dev.sh

# Activate virtual environment
source venv/bin/activate
```

## Creating Dummy Models

The `create_dummy_models.py` script generates dummy model APIs for testing:

```bash
# Create default dummy models (5 models)
python scripts/create_dummy_models.py

# Create custom number of models
python scripts/create_dummy_models.py --num-models 10

# Create custom models with specific names
python scripts/create_dummy_models.py --model-name model1 model2 model3

# Create models with specific ports
python scripts/create_dummy_models.py --model-name model_1 model_2 --port 8001 8002
```

This script automatically:

- Creates FastAPI applications for each dummy model
- Generates model configuration files in `config/models/`
- Updates the model registry at `config/models/registry.yaml`
- Creates a startup script at `scripts/start_dummy_models.py`

The generated configurations are saved in `config/models/` directory as YAML files.

## Running Dummy Models

Start the dummy model APIs using the Python script:

```bash
# Start all dummy models as background processes
python scripts/start_dummy_models.py
```

This will:

- Read the model registry configuration
- Start each enabled model on its configured port
- Monitor the models and restart them if they crash
- Keep the processes running until you press Ctrl+C

Each model provides the following endpoints:

- `/predict` - POST endpoint for model predictions
- `/health` - GET endpoint for health checks
- `/info` - GET endpoint for model information

## Running the Orchestrator

With the dummy models running, start the ML Orchestrator:

```bash
# Using Make
make run

# Or using the CLI
./scripts/dev_cli.py run
```

The orchestrator will:

- Load model configurations from `config/models/registry.yaml`
- Connect to all the dummy model APIs
- Expose endpoints for accessing the models through the orchestrator

## Testing the Complete System

### Through the Orchestrator

Once both the dummy models and orchestrator are running, you can test the complete system:

```bash
# Call any model through the orchestrator
curl -X POST http://localhost:8000/orchestrator/model_1/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test input"}'

# Try different models
curl -X POST http://localhost:8000/orchestrator/model_2/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test input"}'
```

### Testing Different Input Types

The dummy models support various input formats:

```bash
# String input
curl -X POST http://localhost:8000/orchestrator/model_1/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "text to process"}'

# Dictionary input
curl -X POST http://localhost:8000/orchestrator/model_1/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"text": "sample text", "value": 42}, "parameters": {"temperature": 0.7}}'

# List input
curl -X POST http://localhost:8000/orchestrator/model_1/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": ["item1", "item2", "item3"]}'
```

### Checking Orchestrator Health

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health status (includes model status)
curl http://localhost:8000/health/details
```

## Calling APIs Directly

You can also call the dummy model APIs directly, bypassing the orchestrator:

### Prediction Endpoints

```bash
# Model 1 prediction
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test input"}'

# Model 2 prediction
curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test input"}'
```

### Health Check Endpoints

```bash
# Model 1 health
curl http://localhost:8001/health

# Model 2 health
curl http://localhost:8002/health
```

### Model Information Endpoints

```bash
# Model 1 info
curl http://localhost:8001/info

# Model 2 info
curl http://localhost:8002/info
```

### Example Responses

#### Prediction Response

```json
{
  "outputs": "[model_1] Processed: test input",
  "model_id": "model_1",
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "processing_time": 0.123,
  "metadata": {
    "version": "1.0.0",
    "timestamp": 1620000000.123,
    "parameters": null
  }
}
```

#### Health Response

```json
{
  "status": "ok",
  "model_id": "model_1",
  "version": "1.0.0"
}
```

#### Info Response

```json
{
  "model_id": "model_1",
  "version": "1.0.0",
  "display_name": "Model 1",
  "description": "Dummy model API for model_1",
  "input_type": "json",
  "output_type": "json"
}
```

## Advanced Usage

### Running a Single Model

To run just one of the models:

```bash
# Run only model_1 (index 0)
python -m scripts.create_dummy_models --run-server --model-index 0

# Run only model_2 (index 1)
python -m scripts.create_dummy_models --run-server --model-index 1
```

### Testing with Python Requests

```python
import requests
import json

# Prediction request
response = requests.post(
    "http://localhost:8001/predict",
    headers={"Content-Type": "application/json"},
    json={"inputs": "test input", "parameters": {"param1": "value1"}}
)
print(json.dumps(response.json(), indent=2))

# Health check
health = requests.get("http://localhost:8001/health")
print(json.dumps(health.json(), indent=2))

# Info check
info = requests.get("http://localhost:8001/info")
print(json.dumps(info.json(), indent=2))
```

## Troubleshooting

### Port Conflicts

If you get port conflicts:

```bash
# Kill existing processes
pkill -f "create_dummy_models"

# Or specify different ports
python scripts/create_dummy_models.py --num-models 5 --port 9001 9002 9003 9004 9005
```

### Models Not Starting

If the models fail to start:

```bash
# Check the model configurations
cat config/models/dummy-model-1.yaml

# Try running a single model in the foreground to see any errors
python -m scripts.create_dummy_models --run-server --model-index 0
```

### Orchestrator Not Connecting to Models

If the orchestrator can't connect to the dummy models:

1. Make sure the dummy models are running (`ps aux | grep create_dummy_models`)
2. Check the model registry configuration (`cat config/models/registry.yaml`)
3. Verify the model configuration files (`cat config/models/dummy-model-1.yaml`)
4. Ensure the ports match between the running models and the configuration

### Testing Model Health Independently

To check if a model is running correctly:

```bash
# Check health endpoint directly
curl http://localhost:8001/health

# Try a simple prediction request
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test"}'
```

### Simulated Errors

The dummy models intentionally generate random errors based on the configured error rate. This is normal and helps test the orchestrator's error handling and circuit breaker functionality.

If you want models with fewer errors, create new ones with a lower error rate:

```bash
python scripts/create_dummy_models.py --num-models 1 --port 8003
```

Then edit the corresponding model configuration in `config/models/` directory to set `error_rate` to a lower value (e.g., 0.01 for 1% errors).
