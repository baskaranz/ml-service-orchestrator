from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import json
import argparse
from typing import Dict, Any, Optional

app = FastAPI(title="Model Mock Server")

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
    # Simple mock response
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the mock model server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--model-name", type=str, default="mock-model", help="Name of the model")
    args = parser.parse_args()
    
    os.environ["MODEL_NAME"] = args.model_name
    uvicorn.run(app, host="0.0.0.0", port=args.port) 