import logging
import os
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ML Model Orchestrator")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model registry
MODEL_REGISTRY = {
    "mock-model-1": {
        "base_url": "http://mock-model-1:8001",
        "active": True,
        "timeout": 30.0,
        "max_retries": 3,
    },
    "mock-model-2": {
        "base_url": "http://mock-model-2:8002",
        "active": True,
        "timeout": 30.0,
        "max_retries": 3,
    },
}

# HTTP client with connection pooling
client = httpx.AsyncClient(timeout=30.0)


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    models: List[str] = []
    components: Dict[str, Any] = {}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "models": list(MODEL_REGISTRY.keys())}


@app.get("/models")
async def list_models():
    """List all registered models"""
    return [{"model_id": model_id, **config} for model_id, config in MODEL_REGISTRY.items()]


@app.get("/models/{model_id}/health")
async def model_health(model_id: str):
    """Check health of a specific model"""
    if model_id not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    model = MODEL_REGISTRY[model_id]
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{model['base_url']}/health")
            status = "healthy" if response.status_code == 200 else "unhealthy"
            return {"model_id": model_id, "status": status, "details": response.json()}
    except Exception as e:
        return {"model_id": model_id, "status": "unhealthy", "error": str(e)}


@app.post("/models/{model_id}/predict")
async def predict(model_id: str, request: Request):
    """Route prediction to the specified model"""
    if model_id not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    if not MODEL_REGISTRY[model_id]["active"]:
        raise HTTPException(status_code=400, detail=f"Model {model_id} is not active")

    model = MODEL_REGISTRY[model_id]
    payload = await request.json()

    try:
        async with httpx.AsyncClient(timeout=model["timeout"]) as client:
            response = await client.post(
                f"{model['base_url']}/predict",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from model {model_id}: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error calling model {model_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Get system and model metrics"""
    metrics = {
        "system": {
            "models_loaded": len(MODEL_REGISTRY),
            "active_models": [
                model_id for model_id, model in MODEL_REGISTRY.items() if model.get("active", False)
            ],
        },
        "models": {},
    }

    # Check health of each model
    for model_id in MODEL_REGISTRY:
        health = await model_health(model_id)
        metrics["models"][model_id] = {
            "active": MODEL_REGISTRY[model_id].get("active", False),
            "health": health["status"],
            "endpoint": MODEL_REGISTRY[model_id]["base_url"],
        }

    return metrics


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
