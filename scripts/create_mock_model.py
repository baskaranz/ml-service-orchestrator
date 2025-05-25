#!/usr/bin/env python3
"""
Script to create and run a mock model for testing the ML Service Orchestrator.

Usage:
    python create_mock_model.py --name mock-model-1 --port 8003 --version 1.0.0
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Template for model_server.py
MODEL_SERVER_TEMPLATE = """
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
"""

# Template for requirements.txt
REQUIREMENTS_TEMPLATE = """
fastapi==0.95.1
uvicorn==0.22.0
pydantic==1.10.7
requests==2.28.2
"""

# Template for Dockerfile
DOCKERFILE_TEMPLATE = """
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
"""

# Template for model configuration YAML
MODEL_CONFIG_TEMPLATE = """
# {model_name} Configuration
name: {model_name}
version: {version}
endpoint_url: {endpoint_url}
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
  description: "{model_name} for testing"
  owner: "ML Team"
  tags: ["mock", "test"]
"""

# Template for docker-compose.yml
DOCKER_COMPOSE_TEMPLATE = """
version: "3.8"

services:
  {model_name}:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "{host_port}:8000"
    environment:
      - PORT=8000
      - MODEL_NAME={model_name}
      - MODEL_VERSION={version}
      - LOG_LEVEL=DEBUG
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    networks:
      - ml-network

networks:
  ml-network:
    name: ml-network
    external: true
"""

# Template for run script
RUN_SCRIPT_TEMPLATE = """
#!/bin/bash

# Run {model_name} on port {host_port}
export MODEL_NAME={model_name}
export MODEL_VERSION={version}
export PORT={host_port}

python model_server.py
"""


def create_mock_model(name, port, version, output_dir=None):
    """
    Create files for a mock model.

    Args:
        name: Name of the mock model
        port: Port to run the mock model on
        version: Version of the mock model
        output_dir: Directory to create files in (default: ./mock-models/{name})
    """
    if output_dir is None:
        output_dir = f"./mock-models/{name}"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create model_server.py
    with open(output_path / "model_server.py", "w") as f:
        f.write(MODEL_SERVER_TEMPLATE.strip())

    # Create requirements.txt
    with open(output_path / "requirements.txt", "w") as f:
        f.write(REQUIREMENTS_TEMPLATE.strip())

    # Create Dockerfile
    with open(output_path / "Dockerfile", "w") as f:
        f.write(DOCKERFILE_TEMPLATE.strip())

    # Create docker-compose.yml
    with open(output_path / "docker-compose.yml", "w") as f:
        f.write(
            DOCKER_COMPOSE_TEMPLATE.strip().format(model_name=name, host_port=port, version=version)
        )

    # Create run script
    run_script_path = output_path / "run.sh"
    with open(run_script_path, "w") as f:
        f.write(
            RUN_SCRIPT_TEMPLATE.strip().format(model_name=name, host_port=port, version=version)
        )

    # Make run script executable
    os.chmod(run_script_path, 0o755)

    # Create model configuration directory
    config_dir = output_path / "config" / "local" / "models"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create model configuration file for localhost access
    with open(config_dir / f"{name}.yaml", "w") as f:
        f.write(
            MODEL_CONFIG_TEMPLATE.strip().format(
                model_name=name, version=version, endpoint_url=f"http://localhost:{port}"
            )
        )

    # Create model configuration file for container-to-container access
    with open(config_dir / f"{name}-docker.yaml", "w") as f:
        f.write(
            MODEL_CONFIG_TEMPLATE.strip().format(
                model_name=name, version=version, endpoint_url=f"http://{name}:8000"
            )
        )

    logger.info(f"Created mock model {name} in {output_path}")
    logger.info(f"To run with Docker: cd {output_path} && docker-compose up -d")
    logger.info(f"To run with Python: cd {output_path} && ./run.sh")
    logger.info(f"Model configuration files created in {config_dir}")


def main():
    parser = argparse.ArgumentParser(description="Create a mock model for testing")
    parser.add_argument("--name", default="mock-model-1", help="Name of the mock model")
    parser.add_argument("--port", type=int, default=8003, help="Port to run the mock model on")
    parser.add_argument("--version", default="1.0.0", help="Version of the mock model")
    parser.add_argument("--output-dir", help="Directory to create files in")

    args = parser.parse_args()

    create_mock_model(args.name, args.port, args.version, args.output_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
