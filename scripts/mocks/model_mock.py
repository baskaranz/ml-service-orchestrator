#!/usr/bin/env python3
"""
Mock Model API

A simple mock model API that can be used for testing the ML Orchestrator.
"""

import argparse
import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mock_model_api")

# Get environment variables
MODEL_NAME = os.getenv("MODEL_NAME", "mock-model")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")

class ModelInput(BaseModel):
    """Model input class."""
    inputs: Any = Field(..., description="Model inputs (any format supported)")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional parameters")

class ModelOutput(BaseModel):
    """Model output class."""
    outputs: Any = Field(..., description="Model outputs")
    model_id: str = Field(..., description="ID of the model that processed the request")
    request_id: str = Field(..., description="Unique request ID")
    processing_time: float = Field(..., description="Processing time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

# Create FastAPI app at module level
app = FastAPI(
    title=f"{MODEL_NAME} API",
    description=f"Mock API for {MODEL_NAME}",
    version=MODEL_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "model_id": MODEL_NAME, "version": MODEL_VERSION}

@app.get("/info")
async def info():
    """Model information endpoint."""
    return {
        "model_id": MODEL_NAME,
        "version": MODEL_VERSION,
        "display_name": MODEL_NAME,
        "description": "Mock model for testing",
        "input_type": "json",
        "output_type": "json",
    }

@app.post("/predict", response_model=ModelOutput, status_code=status.HTTP_200_OK)
async def predict(request: Request, data: ModelInput):
    """
    Main prediction endpoint.
    
    Returns a simulated response based on the input.
    """
    # Extract request information
    request_id = request.state.request_id
    start_time = time.time()
    
    # Generate output based on input format
    if isinstance(data.inputs, dict):
        # For dictionary inputs, echo back with some modifications
        outputs = {k: f"processed_{v}" if isinstance(v, str) else v * 2 for k, v in data.inputs.items()}
    elif isinstance(data.inputs, list):
        # For list inputs, transform each item
        outputs = [f"processed_{item}" if isinstance(item, str) else item * 2 for item in data.inputs]
    elif isinstance(data.inputs, str):
        # For string inputs, echo back with model identifier
        outputs = f"[{MODEL_NAME}] Processed: {data.inputs}"
    else:
        # For other inputs, return a dummy response
        outputs = {"result": f"Processed by {MODEL_NAME}", "confidence": 0.95}
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    # Create response
    return ModelOutput(
        outputs=outputs,
        model_id=MODEL_NAME,
        request_id=request_id,
        processing_time=processing_time,
        metadata={
            "model_name": MODEL_NAME,
            "version": MODEL_VERSION,
            "timestamp": time.time(),
            "parameters": data.parameters
        }
    )

# Register error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "model_id": MODEL_NAME,
            "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception in {MODEL_NAME}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": f"Internal server error: {str(exc)}",
            "model_id": MODEL_NAME,
            "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
            "status_code": 500
        }
    )

def main():
    """Run the mock model API server."""
    parser = argparse.ArgumentParser(description="Run a mock model API server")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Port to run the server on")
    parser.add_argument("--model-name", type=str, default=MODEL_NAME, help="Name of the model")
    args = parser.parse_args()
    uvicorn.run("model_mock:app", host="0.0.0.0", port=args.port, factory=False)

if __name__ == "__main__":
    main() 