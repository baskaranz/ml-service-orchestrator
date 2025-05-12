# Dummy Model APIs for ML Orchestrator

This document explains how to use the `create_dummy_models.py` script to generate and run dummy model APIs that can be attached to the ML Orchestrator for testing and development.

## Overview

The script creates:

1. FastAPI applications for each dummy model
2. Model configuration files for the orchestrator
3. A model registry configuration
4. A startup script to run all the dummy models at once

Each dummy model API provides:

- A `/predict` endpoint for inference
- A `/health` endpoint for health checks
- A `/info` endpoint for model information
- Configurable latency and error rates
- Realistic request/response formats compatible with the orchestrator

## Quick Start

### Create Dummy Models

```bash
# Create default dummy models (apple_model and orange_model)
python scripts/create_dummy_models.py

# Create custom models with specific names
python scripts/create_dummy_models.py --model-name model1 model2 model3

# Create models with specific ports
python scripts/create_dummy_models.py --model-name apple_model orange_model --port 8001 8002
```

### Run Dummy Models

After creating the models, you can start them using the generated startup script:

```bash
# Start all dummy models as background processes
bash scripts/start_dummy_models.sh
```

This will start all the dummy model APIs in the background. Press any key to terminate all the processes.

### Using with ML Orchestrator

1. Make sure the orchestrator is configured to use the model registry
2. Start the dummy models using the startup script
3. Start the orchestrator with hot-reloading enabled

The orchestrator will automatically load the model configurations from the registry and route requests to the appropriate dummy model API.

## API Endpoints

Each dummy model API provides the following endpoints:

### `/predict` (POST)

Main inference endpoint that accepts model inputs and returns outputs.

**Request:**

```json
{
  "inputs": "your input text or data",
  "parameters": {
    "optional_param1": "value1",
    "optional_param2": "value2"
  }
}
```

**Response:**

```json
{
  "outputs": "processed result",
  "model_id": "model_name",
  "request_id": "unique-uuid",
  "processing_time": 0.123,
  "metadata": {
    "version": "1.0.0",
    "timestamp": 1620000000.123,
    "parameters": {
      "optional_param1": "value1",
      "optional_param2": "value2"
    }
  }
}
```

### `/health` (GET)

Health check endpoint to verify the model is running.

**Response:**

```json
{
  "status": "ok",
  "model_id": "model_name",
  "version": "1.0.0"
}
```

### `/info` (GET)

Model information endpoint.

**Response:**

```json
{
  "model_id": "model_name",
  "version": "1.0.0",
  "display_name": "Model Name",
  "description": "Dummy model API for model_name",
  "input_type": "json",
  "output_type": "json"
}
```

## Advanced Usage

### Running a Single Model

To run a specific model directly:

```bash
# Run the first model (index 0)
python -m scripts.create_dummy_models --run-server --model-index 0

# Run the second model (index 1)
python -m scripts.create_dummy_models --run-server --model-index 1
```

### Modifying Model Behavior

The model configurations are saved in `config/models/` directory as YAML files. You can edit these files to change the latency, error rate, or other properties of the models.

### Testing with curl

You can test the dummy models using curl:

```bash
# Health check
curl http://localhost:8001/health

# Model info
curl http://localhost:8001/info

# Prediction
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": "test input", "parameters": {"param1": "value1"}}'
```

## Generated Files

The script generates the following files:

- `config/models/`: Model configuration files (YAML)
- `config/models/registry.yaml`: Model registry configuration
- `scripts/start_dummy_models.sh`: Startup script for all models

## Troubleshooting

### Port already in use

If you get an error about the port being already in use, specify different ports:

```bash
python scripts/create_dummy_models.py --model-name apple_model orange_model --port 9001 9002
```

### Orchestrator not connecting to models

Make sure the dummy models are running and the orchestrator is properly configured to use the model registry.

### Simulated errors

The dummy models intentionally generate random errors based on the configured error rate. This is normal and helps test the orchestrator's error handling.
