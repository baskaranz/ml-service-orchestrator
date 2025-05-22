# Mock Model Setup Guide

This guide explains how to create and configure mock models for the ML Service Orchestrator.

## Table of Contents

1. [Creating the Mock Model Service](#creating-the-mock-model-service)
   - [Using Docker (Recommended)](#option-1-using-docker-recommended)
   - [Running Directly with Python](#option-2-running-directly-with-python)
2. [Creating the Model Configuration](#creating-the-model-configuration-for-the-orchestrator)
3. [Testing the Integration](#testing-the-integration)
4. [Troubleshooting](#troubleshooting)

## Creating the Mock Model Service

The mock model service is a simple FastAPI application that simulates an ML model API. Here's how to set it up:

### Option 1: Using Docker (Recommended)

#### Step 1: Create a directory for your mock model

```bash
mkdir -p mock-model/config/models
```

#### Step 2: Create the model server script

Create a file `mock-model/model_server.py` with the following content:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthResponse(BaseModel):
    status: str = "ok"
    model: str
    version: str

class PredictionRequest(BaseModel):
    input: str

class PredictionResponse(BaseModel):
    output: str
    model: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "ok",
        "model": os.getenv("MODEL_NAME", "mock-model"),
        "version": os.getenv("MODEL_VERSION", "1.0.0")
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    return {
        "output": f"Processed by {os.getenv('MODEL_NAME')}: {request.input}",
        "model": os.getenv("MODEL_NAME", "mock-model")
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting mock model server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
```

#### Step 3: Create a requirements.txt file

Create a file `mock-model/requirements.txt` with:

```
fastapi==0.95.1
uvicorn==0.22.0
pydantic==1.10.7
```

#### Step 4: Create a Dockerfile

Create a file `mock-model/Dockerfile` with:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt requests

# Copy mock model server
COPY model_server.py .

# Create config directory
RUN mkdir -p /app/config/models

# Set default environment variables
ENV PORT=8000
ENV MODEL_NAME=mock-model
ENV MODEL_VERSION=1.0.0
ENV LOG_LEVEL=INFO

# Expose the port the app runs on
EXPOSE ${PORT}

# Run the application
CMD exec uvicorn model_server:app --host 0.0.0.0 --port $PORT
```

#### Step 5: Build and run the Docker container

```bash
cd mock-model
docker build -t mock-model:latest .

# Create Docker network if it doesn't exist
docker network create ml-network

# Run the mock model
docker run -d \
  --network ml-network \
  -p 8003:8000 \
  -e MODEL_NAME=mock-model-1 \
  -e MODEL_VERSION=1.0.0 \
  --name mock-model-1 \
  mock-model:latest
```

### Option 2: Running Directly with Python

#### Step 1: Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 2: Install dependencies

```bash
pip install fastapi uvicorn pydantic
```

#### Step 3: Create the model server script

Create the `model_server.py` file with the same content as shown in Option 1, Step 2.

#### Step 4: Run the mock model

```bash
MODEL_NAME=mock-model-1 MODEL_VERSION=1.0.0 PORT=8003 python model_server.py
```

## Creating the Model Configuration for the Orchestrator

To configure the orchestrator to use your mock model, you need to create a YAML configuration file:

#### Step 1: Create a directory for model configurations

```bash
mkdir -p config/local/models
```

#### Step 2: Create the model configuration file

Create a file `config/local/models/mock-model-1.yaml` with:

```yaml
# Mock Model 1 Configuration
name: mock-model-1
version: 1.0.0
endpoint_url: http://localhost:8003  # If running on same machine
# endpoint_url: http://mock-model-1:8000  # If using Docker Compose with container-to-container communication
type: rest
active: true
health_check:
  enabled: true
  endpoint: /health
  interval_seconds: 30
circuit_breaker:
  enabled: true
  failure_threshold: 5
  reset_timeout_seconds: 30
request_timeout_seconds: 10
retries: 3
backoff_factor: 0.5
max_concurrent_requests: 100
routing:
  default_weight: 100
metadata:
  description: "Mock Model 1 for testing"
  owner: "ML Team"
  tags: ["mock", "test"]
```

**Important Note on `endpoint_url`:**
- Use `http://localhost:8003` when the orchestrator is running on the host and the mock model is accessible via localhost port 8003
- Use `http://mock-model-1:8000` when both the orchestrator and mock models are running in Docker containers on the same Docker network

#### Step 3: Mount this configuration when running the orchestrator

```bash
docker run -d -p 8000:8000 \
  -e APP_ENV=local \
  -v $(pwd)/config:/app/config/local \
  ml-orchestrator:latest
```

## Testing the Integration

#### Step 1: Check if the mock model is running

```bash
curl http://localhost:8003/health
```

Expected response:
```json
{"status":"ok","model":"mock-model-1","version":"1.0.0"}
```

#### Step 2: Check if the orchestrator can see the model

```bash
curl http://localhost:8000/api/v1/models
```

#### Step 3: Send a request to the model through the orchestrator

```bash
curl -X POST http://localhost:8000/api/v1/models/mock-model-1 \
  -H "Content-Type: application/json" \
  -d '{"input": "test input"}'
```

**Important**: The mock model expects a JSON payload with a key `input`, not `data`. Using `{"data": ...}` will cause a validation error.

## Troubleshooting

### Network Issues

If the orchestrator can't connect to the mock models, check:

1. The models are running and accessible on the expected ports
2. The endpoint URLs in the configuration files are correct
3. There are no firewall rules blocking the connections

### Configuration Issues

If the models don't appear in the orchestrator:

1. Verify the configuration files are in the correct location
2. Check the orchestrator logs for any errors loading the configurations
3. Make sure the model names in the configuration files match the expected format

### Request Format Issues

Remember that the mock models expect a JSON payload with a key `input`, not `data`:

```json
{"input": "test input"}
```

### Docker Network Issues

If using Docker and containers can't communicate:

1. Ensure all containers are on the same Docker network
2. Check that the network exists: `docker network ls`
3. Inspect the network: `docker network inspect ml-network`

## Running Multiple Mock Models

To run multiple mock models, simply repeat the process with different names and ports:

```bash
# Run Mock Model 2
docker run -d \
  --network ml-network \
  -p 8004:8000 \
  -e MODEL_NAME=mock-model-2 \
  -e MODEL_VERSION=1.0.0 \
  --name mock-model-2 \
  mock-model:latest
```

Then create another configuration file `config/local/models/mock-model-2.yaml` with the appropriate endpoint URL.
