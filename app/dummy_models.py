import asyncio
import random

from fastapi import FastAPI
from pydantic import BaseModel


class PredictionRequest(BaseModel):
    input: str


class PredictionResponse(BaseModel):
    prediction: float
    confidence: float


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Welcome to Dummy Model API"}


@app.post("/predict", response_model=PredictionResponse)
async def predict(data: PredictionRequest):
    # Simulate some processing time
    await asyncio.sleep(random.uniform(0.1, 0.5))
    return PredictionResponse(prediction=random.random(), confidence=random.random())


@app.get("/health")
async def health():
    return {"status": "healthy"}


def create_model_api():
    return app
