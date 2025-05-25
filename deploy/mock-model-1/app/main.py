import logging
import os
import random
from typing import Any, Dict

from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI(title="Mock Model 1 Service")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mock-model-1", "version": "1.0.0"}


@app.post("/predict")
async def predict(payload: Dict[str, Any]):
    """Mock prediction endpoint"""
    try:
        logger.info(f"Received prediction request with payload: {payload}")

        # Simple echo response with some mock data
        response = {
            "model": "mock-model-1",
            "input": payload,
            "prediction": {"score": 0.95, "label": "positive"},
            "metadata": {"model_version": "1.0", "inference_time_ms": 12.5},
        }
        return response

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
