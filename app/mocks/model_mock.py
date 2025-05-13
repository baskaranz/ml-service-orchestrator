from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn
import os
import json
import argparse
from typing import Dict, Any, Optional
import random
import time
import logging

app = FastAPI(title="Model Mock Server")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model_mock")

class PredictionRequest(BaseModel):
    inputs: Any
    parameters: Optional[Dict[str, Any]] = None

class PredictionResponse(BaseModel):
    outputs: Dict[str, Any]
    metadata: Dict[str, Any]

@app.get("/health")
async def health_check():
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
async def predict(request: PredictionRequest):
    logger.info("[MODEL MOCK] predict function called")
    logger.info(f"[MODEL MOCK] Raw request: {request}")
    logger.info(f"[MODEL MOCK] Request inputs type: {type(request.inputs)}")
    logger.info(f"[MODEL MOCK] Request inputs: {request.inputs}")
    
    if request.inputs and "error_type" in request.inputs:
        await _simulate_error(request.inputs["error_type"])
    else:
        # Normal response
        return PredictionResponse(
            outputs={
                "predictions": [0.5] * 10,  # Mock predictions
                "confidence": 0.95
            },
            metadata={
                "model_name": os.getenv("MODEL_NAME", "mock-model"),
                "version": os.getenv("MODEL_VERSION", "1.0.0")
            }
        )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"[MODEL MOCK] Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    return response

@app.get("/{path:path}")
async def catch_all(path: str):
    logger.info(f"[MODEL MOCK] Catch-all route hit: {path}")
    return {"message": "Catch-all route", "path": path}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the mock model server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--model-name", type=str, default="mock-model", help="Name of the model")
    args = parser.parse_args()
    
    os.environ["MODEL_NAME"] = args.model_name
    uvicorn.run(app, host="0.0.0.0", port=args.port) 