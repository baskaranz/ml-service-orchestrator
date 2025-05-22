"""
API request/response Pydantic models for the orchestrator service.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.config_models import ModelConfig


class HealthStatus(str, Enum):
    """Health status enum."""

    OK = "OK"
    ERROR = "ERROR"
    WARNING = "WARNING"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    status: HealthStatus = Field(..., description="Health status of the component")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health details")


class ModelSummary(BaseModel):
    """Summary of a model configuration."""

    id: str
    name: str
    active: bool = True


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    code: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response model."""

    status: HealthStatus
    version: str
    models: Optional[List[ModelSummary]] = Field(
        default_factory=list, description="List of model summaries"
    )
    components: Optional[Dict[str, ComponentHealth]] = Field(
        default_factory=dict, description="Component health information"
    )


class ModelListResponse(BaseModel):
    models: List[ModelSummary] = Field(..., description="List of model summaries")
    count: int = Field(..., description="Total number of models")


class CreateModelRequest(BaseModel):
    model: ModelConfig = Field(..., description="Model configuration")
