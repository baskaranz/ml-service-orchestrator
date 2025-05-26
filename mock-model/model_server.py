import logging
import os
import random

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    inputs: dict


class PredictionResponse(BaseModel):
    outputs: dict
    model: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for the model service."""
    return {
        "status": "ok",
        "model": os.getenv("MODEL_NAME", "mock-model"),
        "version": os.getenv("MODEL_VERSION", "1.0.0"),
    }


@app.post("/predict")
async def predict(request: PredictionRequest):
    """Generate mock predictions based on input data."""
    model_name = os.getenv("MODEL_NAME", "mock-model")
    model_version = os.getenv("MODEL_VERSION", "1.0.0")

    # Generate mock predictions based on input
    if isinstance(request.inputs, dict) and "data" in request.inputs:
        predictions = [round(random.random(), 4) for _ in request.inputs["data"]]
    else:
        # Default to 3 random predictions
        predictions = [round(random.random(), 4) for _ in range(3)]

    return {
        "outputs": {"predictions": predictions, "confidence": 0.95},
        "model": model_name,
        "version": model_version,
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    model_name = os.getenv("MODEL_NAME", "mock-model")
    logger.info(f"Starting {model_name} server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
