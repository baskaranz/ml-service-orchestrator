"""
API request/response Pydantic models for the orchestrator service.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.config_models import ModelConfig

class HealthStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"

class ComponentHealth(BaseModel):
    status: HealthStatus = Field(..., description="Health status of the component")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health details")

class HealthResponse(BaseModel):
    status: HealthStatus = Field(..., description="Overall health status")
    version: str = Field(..., description="Service version")
    components: Dict[str, 'ComponentHealth'] = Field(default_factory=dict, description="Component health statuses")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

class ModelSummary(BaseModel):
    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    description: Optional[str] = Field(None, description="Model description")
    version: str = Field(..., description="Model version")
    active: bool = Field(..., description="Whether the model is active")

class ModelListResponse(BaseModel):
    models: List[ModelSummary] = Field(..., description="List of model summaries")
    count: int = Field(..., description="Total number of models")

class CreateModelRequest(BaseModel):
    model: ModelConfig = Field(..., description="Model configuration") 