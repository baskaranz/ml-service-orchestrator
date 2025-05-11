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
# Create default dummy models (apple_model and orange_model)
python scripts/create_dummy_models.py

# Create custom models with specific names
python scripts/create_dummy_models.py --model-name model1 model2 model3

# Create models with specific ports
python scripts/create_dummy_models.py --model-name apple_model orange_model --port 8001 8002
```

This script automatically:
- Creates FastAPI applications for each dummy model
- Generates model configuration files in `config/models/`
- Updates the model registry at `config/models_registry.yaml`
- Creates a startup script at `scripts/start_dummy_models.sh`

The generated configurations are saved in `config/dummy_models.json`.

## Running Dummy Models

Start the dummy model APIs using the generated script:

```bash
# Start all dummy models as background processes
bash scripts/start_dummy_models.sh
```

This will:
- Start `apple_model` on port 8001
- Start `orange_model` on port 8002
- Keep the processes running until you press a key

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
- Load model configurations from `config/models_registry.yaml`
- Connect to the dummy model APIs running on ports 8001 and 8002
- Expose endpoints for accessing the models through the orchestrator

## Testing the Complete System

### Through the Orchestrator

Once both the dummy models and orchestrator are running, you can test the complete system:

```bash
# Call apple_model through the orchestrator
curl -X POST http://localhost:8000/orchestrator/apple_model/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test input"}'

# Call orange_model through the orchestrator
curl -X POST http://localhost:8000/orchestrator/orange_model/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test input"}'
```

### Testing Different Input Types

The dummy models support various input formats:

```bash
# String input
curl -X POST http://localhost:8000/orchestrator/apple_model/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "text to process"}'

# Dictionary input
curl -X POST http://localhost:8000/orchestrator/apple_model/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"text": "sample text", "value": 42}, "parameters": {"temperature": 0.7}}'

# List input
curl -X POST http://localhost:8000/orchestrator/apple_model/predict \
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
# Apple Model prediction
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test input"}'

# Orange Model prediction
curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test input"}'
```

### Health Check Endpoints

```bash
# Apple Model health
curl http://localhost:8001/health

# Orange Model health
curl http://localhost:8002/health
```

### Model Information Endpoints

```bash
# Apple Model info
curl http://localhost:8001/info

# Orange Model info
curl http://localhost:8002/info
```

### Example Responses

#### Prediction Response

```json
{
  "outputs": "[apple_model] Processed: test input",
  "model_id": "apple_model",
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
  "model_id": "apple_model",
  "version": "1.0.0"
}
```

#### Info Response

```json
{
  "model_id": "apple_model",
  "version": "1.0.0",
  "display_name": "Apple Model",
  "description": "Dummy model API for apple_model",
  "input_type": "json",
  "output_type": "json"
}
```

## Advanced Usage

### Running a Single Model

To run just one of the models:

```bash
# Run only the apple_model (index 0)
python -m scripts.create_dummy_models --run-server --model-index 0

# Run only the orange_model (index 1)
python -m scripts.create_dummy_models --run-server --model-index 1
```

### Testing with Python Requests

```python
import requests
import json

# Prediction request
response = requests.post(
    "http://localhost:8001/predict",
    headers={"Content-Type": application/json"},
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

### Testing Error Rates

The dummy models have a configurable error rate (around 2-3%). To test the error responses:

```bash
# Make multiple requests to potentially trigger errors
for i in {1..20}; do
  echo "Request $i"
  curl -s -X POST http://localhost:8001/predict \
    -H "Content-Type: application/json" \
    -d '{"inputs": "test"}' | grep -q "error" && echo "Got an error!"
  sleep 0.5
done
```

### Creating Custom Models

You can create models with custom behavior by modifying the parameters:

```bash
# Create models with custom error rates and latency
python scripts/create_dummy_models.py \
  --model-name reliable_model slow_model \
  --port 8003 8004
```

Then edit `config/dummy_models.json` to customize:
- `latency_mean`: Average response time in seconds (e.g., 0.1 for 100ms)
- `latency_stddev`: Standard deviation of latency (for jitter)
- `error_rate`: Probability of returning an error (0.0 to 1.0)

### Adding Models to the Orchestrator Manually

The `create_dummy_models.py` script automatically adds models to the registry, but you can also do it manually:

1. Create a YAML configuration in `config/models/my_model.yaml`:
   ```yaml
   my_model:
     version: "1.0.0"
     endpoint: "http://127.0.0.1:8001/predict"
     timeout_ms: 1000
     max_retries: 3
     circuit_breaker:
       max_failures: 5
       reset_timeout_ms: 30000
     auth:
       enabled: false
   ```

2. Add the model to `config/models_registry.yaml`:
   ```yaml
   models:
     my_model:
       config_file: models/my_model.yaml
       enabled: true
   ```

3. The orchestrator will automatically detect and load the new configuration if hot-reloading is enabled.

## Troubleshooting

### Port Already in Use

If you get an error about the port being already in use:

```bash
# Check what's using the port
lsof -i :8001

# Kill the process
kill <PID>

# Or specify different ports
python scripts/create_dummy_models.py --model-name apple_model orange_model --port 9001 9002
```

### Models Not Starting

If the models fail to start:

```bash
# Check the model configurations
cat config/dummy_models.json

# Try running a single model in the foreground to see any errors
python -m scripts.create_dummy_models --run-server --model-index 0
```

### Orchestrator Not Connecting to Models

If the orchestrator can't connect to the dummy models:

1. Make sure the dummy models are running (`ps aux | grep create_dummy_models`)
2. Check the model registry configuration (`cat config/models_registry.yaml`)
3. Verify the model configuration files (`cat config/models/apple_model.yaml`)
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
python scripts/create_dummy_models.py --model-name reliable_model --port 8003
```

Then edit `config/dummy_models.json` to set `error_rate` to a lower value (e.g., 0.01 for 1% errors).