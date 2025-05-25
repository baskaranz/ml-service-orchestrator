import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Mock Model 2 Service")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mock-model-2", "version": "1.0.0"}


@app.post("/predict")
async def predict(payload: Dict[str, Any]):
    """Mock prediction endpoint"""
    try:
        logger.info(f"Received prediction request with payload: {payload}")

        # Different response structure from model 1
        response = {
            "model": "mock-model-2",
            "input_data": payload,
            "results": {
                "confidence": 0.87,
                "class": "negative",
                "probabilities": {"positive": 0.13, "negative": 0.87},
            },
            "performance": {"inference_time_ms": 8.2, "model_timestamp": "2024-01-01T00:00:00Z"},
        }
        return response

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
