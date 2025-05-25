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
