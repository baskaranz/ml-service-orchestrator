# Mock Model Setup Guide

This guide explains how to create, configure, and test mock models for the ML Service Orchestrator. It includes all necessary API endpoints for testing and integration.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Cleanup Existing Containers](#cleanup-existing-containers)
3. [Setting Up Mock Model Services](#setting-up-mock-model-services)
   - [Using Docker (Recommended)](#option-1-using-docker-recommended)
   - [Running Directly with Python](#option-2-running-directly-with-python)
4. [Testing API Endpoints](#testing-api-endpoints)
   - [Model Management](#model-management)
   - [Health Checks](#health-checks)
   - [Making Predictions](#making-predictions)
   - [Admin Endpoints](#admin-endpoints)
4. [Troubleshooting](#troubleshooting)
5. [Cleanup](#cleanup)

## Setting Up Mock Model Services

### Option 1: Using Docker (Recommended)

1. Create a new directory for the mock model service:
   ```bash
   mkdir -p mock-model
   cd mock-model
   ```

2. Create the following files in the `mock-model` directory:

   `model_server.py`:
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

   `requirements.txt`:
   ```
   fastapi==0.95.1
   uvicorn==0.22.0
   pydantic==1.10.7
   ```

   `Dockerfile`:
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

3. Build and run two mock model services:
   ```bash
   # Build the Docker image
   docker build -t mock-model:latest .

   # Create a Docker network if it doesn't exist
   docker network create ml-network || true

   # Run the first mock model service
   docker run -d \
     --network ml-network \
     -p 9001:8000 \
     -e MODEL_NAME=mock-model-1 \
     -e MODEL_VERSION=1.0.0 \
     --name mock-model-1 \
     mock-model:latest

   # Run the second mock model service
   docker run -d \
     --network ml-network \
     -p 9002:8000 \
     -e MODEL_NAME=mock-model-2 \
     -e MODEL_VERSION=1.0.0 \
     --name mock-model-2 \
     mock-model:latest
   ```

## Testing API Endpoints

### Model Management

1. **List all available models**:
   ```bash
   curl -s http://localhost:8000/api/v1/orchestrator/models | jq
   ```

2. **Get model information**:
   ```bash
   curl -s http://localhost:8000/api/v1/orchestrator/models/mock-model-1/info | jq
   ```

3. **Get model health status**:
   ```bash
   curl -s http://localhost:8000/api/v1/orchestrator/models/mock-model-1/health | jq
   ```

4. **Get model configuration**:
   ```bash
   curl -s http://localhost:8000/api/v1/orchestrator/models/mock-model-1/config | jq
   ```

5. **Refresh model registry**:
   ```bash
   curl -X 'POST' 'http://localhost:8000/api/v1/orchestrator/refresh' | jq
   ```

### Health Checks

1. **Basic health check**:
   ```bash
   curl -s http://localhost:8000/health | jq
   ```

2. **Detailed health check**:
   ```bash
   curl -s http://localhost:8000/health/details | jq
   ```

3. **Model-specific health check**:
   ```bash
   curl -s http://localhost:8000/health/models/mock-model-1 | jq
   ```

### Making Predictions

1. **Make a prediction**:
   ```bash
   curl -X 'POST' 'http://localhost:8000/api/v1/orchestrator/models/mock-model-1' \
     -H 'Content-Type: application/json' \
     -d '{"input": "Test input"}' | jq
   ```

### Admin Endpoints

1. **List all models (admin)**:
   ```bash
   curl -s http://localhost:8000/admin/models | jq
   ```

2. **Get model details (admin)**:
   ```bash
   curl -s http://localhost:8000/admin/models/mock-model-1 | jq
   ```

## Troubleshooting

1. **Check container logs**:
   ```bash
   docker logs mock-model-1
   ```

2. **Check if containers are running**:
   ```bash
   docker ps
   ```

3. **Common issues**:
   - **404 Not Found**: Verify the model ID is correct and registered
   - **500 Internal Server Error**: Check the orchestrator logs
   - **Connection refused**: Ensure the model service is running and accessible

## Cleanup

To stop and remove all containers:

```bash
# Stop and remove any existing containers
docker stop mock-model-1 mock-model-2 2>/dev/null || true
docker rm mock-model-1 mock-model-2 2>/dev/null || true

# Remove the Docker network if it exists
docker network rm ml-network 2>/dev/null || true

# Verify cleanup
docker ps -a | grep mock-model || echo "No mock model containers found"
```

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

## Registering Models with the Orchestrator

To register your mock models with the orchestrator, use the admin API to configure each model:

#### Register mock-model-1

```bash
curl -X PUT http://localhost:8000/admin/admin/models/mock-model-1 \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "id": "mock-model-1",
      "name": "Mock Model 1",
      "endpoint_url": "http://host.docker.internal:9001",
      "active": true,
      "timeout": 10.0,
      "max_retries": 3,
      "health_check": {
        "enabled": true,
        "endpoint": "/health",
        "interval": 30,
        "timeout": 3,
        "failure_threshold": 3,
        "success_threshold": 2
      },
      "headers": {
        "Content-Type": "application/json"
      }
    }
  }' | jq
```

#### Register mock-model-2

```bash
curl -X PUT http://localhost:8000/admin/admin/models/mock-model-2 \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "id": "mock-model-2",
      "name": "Mock Model 2",
      "endpoint_url": "http://host.docker.internal:9002",
      "active": true,
      "timeout": 10.0,
      "max_retries": 3,
      "health_check": {
        "enabled": true,
        "endpoint": "/health",
        "interval": 30,
        "timeout": 3,
        "failure_threshold": 3,
        "success_threshold": 2
      },
      "headers": {
        "Content-Type": "application/json"
      }
    }
  }' | jq
```

#### Reload the Orchestrator Configuration

After registering or updating models, reload the orchestrator to apply changes:

```bash
curl -X POST http://localhost:8000/admin/admin/reload
```
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

### 1. Verify the mock models are running

```bash
# Check health of mock-model-1 directly
curl http://localhost:9001/health | jq

# Make a prediction through mock-model-1 directly
curl -X POST http://localhost:9001/predict \
  -H "Content-Type: application/json" \
  -d '{"input": "test input"}' | jq

# Check health of mock-model-2 directly
curl http://localhost:9002/health | jq
```

### 2. Verify the orchestrator can reach the mock models

```bash
# Check orchestrator health
curl http://localhost:8000/health | jq

# Check detailed health
curl http://localhost:8000/health/details | jq

# Check health of mock-model-1 through orchestrator
curl http://localhost:8000/health/models/mock-model-1 | jq

# Check health of mock-model-2 through orchestrator
curl http://localhost:8000/health/models/mock-model-2 | jq
```

## Making Predictions

### 1. Make a prediction through the orchestrator

```bash
# Using mock-model-1
curl -X POST "http://localhost:8000/api/v1/orchestrator/models/mock-model-1" \
  -H "Content-Type: application/json" \
  -d '{"input": "test prediction"}' | jq

# Using mock-model-2
curl -X POST "http://localhost:8000/api/v1/orchestrator/models/mock-model-2" \
  -H "Content-Type: application/json" \
  -d '{"input": "another test prediction"}' | jq
```

### 2. Example Response

```json
{
  "status_code": 200,
  "content": {
    "output": "Processed by mock-model-1: test prediction",
    "model": "mock-model-1"
  },
  "headers": {
    "date": "Sun, 25 May 2025 14:29:28 GMT",
    "server": "uvicorn",
    "content-length": "78",
    "content-type": "application/json"
  }
}
```

## Troubleshooting

### 1. Model not reachable
   - Verify the model service is running:
     ```bash
     docker ps | grep mock-model
     ```
   - Check the port mapping if using Docker
   - Verify network connectivity between services
   - Check if the orchestrator can reach the model:
     ```bash
     docker exec orchestrator sh -c "curl -v http://host.docker.internal:9001/health"
     ```

### 2. Health check failures
   - Check the model's health endpoint directly:
     ```bash
     curl -v http://localhost:9001/health
     ```
   - Verify the health check configuration matches the model's implementation
   - Check the orchestrator logs for errors:
     ```bash
     docker logs orchestrator
     ```

### 3. Prediction errors
   - Check the model's logs for errors
   - Verify the input format matches what the model expects
   - Ensure you're using the correct endpoint:
     - For predictions: `POST /api/v1/orchestrator/models/{model_id}`
     - Not: `POST /api/v1/orchestrator/models/{model_id}/predict`

### 4. Common Issues
   - **404 Not Found**: Verify the model ID is correct and registered
   - **500 Internal Server Error**: Check the orchestrator logs for details
   - **Connection refused**: Ensure the model service is running and accessible

### 5. Viewing Logs
   - View orchestrator logs:
     ```bash
     docker logs orchestrator
     ```
   - View mock model logs:
     ```bash
     docker logs mock-model-1
     docker logs mock-model-2

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

## Using the Automated Mock Model Generator

For convenience, we provide a script that automates the creation of mock models. This script generates all the necessary files for a mock model, including the server code, Dockerfile, docker-compose.yml, and configuration files.

### Prerequisites

- Python 3.6+
- Git repository cloned locally

### Usage

```bash
# Make the script executable if it isn't already
chmod +x scripts/create_mock_model.py

# Basic usage (creates mock-model-1 on port 8003)
scripts/create_mock_model.py

# Create a specific mock model
scripts/create_mock_model.py --name custom-model --port 8010 --version 2.0.0

# Specify an output directory
scripts/create_mock_model.py --output-dir /path/to/custom/directory
```

### What the Script Creates

The script creates a complete mock model setup with the following files:

```
mock-models/mock-model-1/
├── Dockerfile                      # For containerizing the mock model
├── config/                        # Configuration directory
│   └── local/
│       └── models/
│           ├── mock-model-1.yaml       # For localhost access
│           └── mock-model-1-docker.yaml # For container-to-container access
├── docker-compose.yml             # For easy deployment with Docker Compose
├── model_server.py                # The FastAPI application
├── requirements.txt               # Dependencies needed
└── run.sh                         # Script to run directly with Python
```

### Running the Generated Mock Model

#### With Docker Compose

```bash
cd mock-models/mock-model-1
docker-compose up -d
```

#### With Python Directly

```bash
cd mock-models/mock-model-1
./run.sh
```

### Using the Generated Configuration Files

The script generates two configuration files:

1. `mock-model-1.yaml` - For when the orchestrator is running on the host
2. `mock-model-1-docker.yaml` - For when both are running in Docker containers

Copy the appropriate configuration file to your orchestrator's configuration directory:

```bash
cp mock-models/mock-model-1/config/local/models/mock-model-1.yaml /path/to/orchestrator/config/local/models/
```
