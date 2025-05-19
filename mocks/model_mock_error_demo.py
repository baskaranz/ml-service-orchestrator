from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import argparse
from typing import Dict, Any, Optional
import random
import asyncio

app = FastAPI(title="Model Mock Server (Error Demo)")

class PredictionRequest(BaseModel):
    inputs: Dict[str, Any]
    parameters: Optional[Dict[str, Any]] = None

class PredictionResponse(BaseModel):
    outputs: Dict[str, Any]
    metadata: Dict[str, Any]

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/predict")
async def predict(request: PredictionRequest):
    # Simulate different types of errors based on input
    if "error_type" in request.inputs:
        error_type = request.inputs["error_type"]
        
        if error_type == "timeout":
            # Simulate timeout by sleeping asynchronously
            await asyncio.sleep(10)
            raise HTTPException(status_code=504, detail="Request timeout")
        elif error_type == "validation":
            # Simulate validation error
            raise HTTPException(status_code=400, detail="Invalid input format")
        elif error_type == "server":
            # Simulate server error
            raise HTTPException(status_code=500, detail="Internal server error")
        elif error_type == "random":
            # Randomly succeed or fail
            if random.random() < 0.5:
                raise HTTPException(status_code=500, detail="Random error occurred")
    # Normal response
    return PredictionResponse(
        outputs={
            "predictions": [0.5] * 10,  # Mock predictions
            "confidence": 0.95
        },
        metadata={
            "model_name": os.getenv("MODEL_NAME", "mock-model-error-demo"),
            "version": os.getenv("MODEL_VERSION", "1.0.0")
        }
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the mock model server (error demo)")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--model-name", type=str, default="mock-model-error-demo", help="Name of the model")
    args = parser.parse_args()
    os.environ["MODEL_NAME"] = args.model_name
    uvicorn.run(app, host="0.0.0.0", port=args.port) 