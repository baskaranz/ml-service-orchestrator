import argparse
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# Global variables
MODEL_NAME = os.getenv("MODEL_NAME", "mock-model")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")

app = FastAPI(title="Mock Model Service")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model_mock")


class ModelInput(BaseModel):
    inputs: Dict[str, Any]
    parameters: Dict[str, Any] = {}


class ModelResponse(BaseModel):
    outputs: Dict[str, Any]
    metadata: Dict[str, str]


def generate_model_config(model_name: str, port: int) -> None:
    """Generate model configuration file with only necessary fields."""
    config = {
        "id": model_name,
        "name": model_name,
        "description": "Mock model for testing",
        "version": os.getenv("MODEL_VERSION", "1.0.0"),
        "endpoint_url": f"http://{model_name}:{port}",
        "active": True,
    }

    # Ensure config directory exists
    config_dir = Path("config/models")
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write config file
    config_path = config_dir / f"{model_name}.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    logger.info(f"Generated model configuration at {config_path}")


@app.get("/health")
async def health_check():
    logger.info("[MODEL MOCK] Health check endpoint called")
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[MODEL MOCK] Unhandled exception: {exc}")
    raise exc


async def _simulate_error(error_type: str) -> None:
    """Simulate different types of errors."""
    if error_type == "rate_limit":
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    elif error_type == "auth":
        raise HTTPException(status_code=401, detail="Authentication failed")
    elif error_type == "input_validation":
        raise HTTPException(status_code=422, detail="Input validation failed")
    elif error_type == "permanent":
        raise HTTPException(status_code=500, detail="Permanent error occurred")
    elif error_type == "transient":
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


@app.post("/predict")
async def predict(request: Request, input_data: ModelInput) -> ModelResponse:
    logger.info(
        f"[MODEL MOCK] Predict endpoint called with method: {request.method} and URL: {request.url}"
    )
    logger.info(f"[MODEL MOCK] Headers: {dict(request.headers)}")
    raw_body = await request.body()
    logger.info(f"[MODEL MOCK] Raw body: {raw_body}")
    logger.info(f"[MODEL MOCK] Predict endpoint called with input: {input_data}")
    # Simulate model prediction
    data = input_data.inputs.get("data", [])
    predictions = [random.random() for _ in range(len(data))]

    # Get model info from environment variables
    model_info = {"name": MODEL_NAME, "version": MODEL_VERSION}

    return ModelResponse(
        outputs={"predictions": predictions, "confidence": 0.95}, metadata=model_info
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"[MODEL MOCK] Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    return response


def main():
    global MODEL_NAME
    parser = argparse.ArgumentParser(description="Mock Model Service")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--model-name", type=str, default="mock-model", help="Name of the model")
    args = parser.parse_args()

    # Update model name
    MODEL_NAME = args.model_name

    # Generate model configuration
    generate_model_config(args.model_name, args.port)

    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
