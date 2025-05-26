"""Pydantic schemas for model configurations and related data structures."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, validator


class ModelHealthCheck(BaseModel):
    """Health check configuration for a model."""

    enabled: bool = True
    endpoint: str = "/health"
    interval: int = Field(30, ge=5, description="Health check interval in seconds")
    timeout: float = Field(3.0, gt=0, description="Health check timeout in seconds")
    failure_threshold: int = Field(
        3, ge=1, description="Number of consecutive failures before marking as unhealthy"
    )
    success_threshold: int = Field(
        2, ge=1, description="Number of consecutive successes before marking as healthy"
    )


class ModelConfig(BaseModel):
    """Base model configuration schema."""

    id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Human-readable name of the model")
    endpoint_url: str = Field(..., description="Base URL for the model's API endpoint")
    active: bool = Field(True, description="Whether the model is currently active")
    timeout: float = Field(10.0, gt=0, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, description="Maximum number of retries for failed requests")

    # Health check configuration
    health_check: ModelHealthCheck = Field(default_factory=ModelHealthCheck)

    # HTTP client configuration
    headers: Dict[str, str] = Field(
        default_factory=lambda: {"Content-Type": "application/json"},
        description="Default headers to include in requests to the model",
    )
    max_connections: int = Field(100, ge=1, description="Maximum number of concurrent connections")
    max_keepalive_connections: int = Field(
        50, ge=0, description="Maximum number of keepalive connections"
    )
    keepalive_timeout: int = Field(60, ge=0, description="Keepalive timeout in seconds")
    pool_connections: int = Field(10, ge=1, description="Number of connection pools to cache")
    pool_maxsize: int = Field(
        100, ge=1, description="Maximum number of connections per connection pool"
    )
    http2: bool = Field(False, description="Whether to use HTTP/2")

    # Metadata
    description: Optional[str] = Field(None, description="Detailed description of the model")
    version: Optional[str] = Field(None, description="Model version")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    # Validation
    @validator("endpoint_url")
    def validate_endpoint_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("endpoint_url must start with http:// or https://")
        return v


class ModelConfigList(BaseModel):
    """Schema for listing model configurations."""

    models: List[ModelConfig]


class ModelPredictionRequest(BaseModel):
    """Schema for model prediction requests."""

    input: Dict[str, Any] = Field(..., description="Input data for the model prediction")
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Additional prediction parameters"
    )


class ModelPredictionResponse(BaseModel):
    """Schema for model prediction responses."""

    model_id: str
    prediction: Any
    model_version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ModelHealthStatus(BaseModel):
    """Schema for model health status."""

    model_id: str
    healthy: bool
    status: str
    timestamp: str
    response_time: Optional[float] = None
    error: Optional[str] = None
