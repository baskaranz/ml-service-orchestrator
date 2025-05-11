"""
DB/config Pydantic models for the orchestrator service.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class CircuitBreakerSettings(BaseModel):
    """Circuit breaker settings for fault tolerance."""
    model_config = ConfigDict(populate_by_name=True)
    failure_threshold: int = Field(5, description="Number of failures before circuit opens")
    reset_timeout: float = Field(30.0, description="Time in seconds before trying to close circuit")
    exclude_exceptions: List[str] = Field(default_factory=list, description="Exception types to exclude from failure count")

class AuthType(str, Enum):
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    NONE = "none"

class AuthLocation(str, Enum):
    HEADER = "header"
    QUERY = "query"

class AuthConfig(BaseModel):
    """Authentication configuration for a model endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    type: AuthType = Field(AuthType.NONE, description="Authentication type")
    key_name: Optional[str] = Field(None, description="Name of the key or header")
    key_value: Optional[str] = Field(None, description="Value of the key or token")
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[str] = Field(None, description="Password for basic auth")
    location: Optional[AuthLocation] = Field(None, description="Location of the auth parameter")

class CacheConfig(BaseModel):
    """Caching configuration for model responses."""
    model_config = ConfigDict(populate_by_name=True)
    enabled: bool = Field(False, description="Whether caching is enabled")
    ttl: int = Field(300, description="Time to live in seconds")
    max_size: int = Field(100, description="Maximum number of cached responses")
    vary_by_headers: List[str] = Field(default_factory=list, description="Headers to vary cache by")

class TransformationConfig(BaseModel):
    """Configuration for request/response transformations."""
    model_config = ConfigDict(populate_by_name=True)
    request_template: Optional[str] = Field(None, description="Jinja2 template for request transformation")
    response_template: Optional[str] = Field(None, description="Jinja2 template for response transformation")

class ModelConfig(BaseModel):
    """Configuration for a model endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Description of the model")
    endpoint_url: str = Field(..., description="URL of the model endpoint")
    version: str = Field("1.0.0", description="Model version")
    timeout: float = Field(30.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    circuit_breaker: CircuitBreakerSettings = Field(default_factory=lambda: CircuitBreakerSettings(failure_threshold=5, reset_timeout=30.0, exclude_exceptions=[]), description="Circuit breaker configuration")
    auth: AuthConfig = Field(default_factory=lambda: AuthConfig(type=AuthType.NONE, key_name=None, key_value=None, username=None, password=None, location=None), description="Authentication configuration")
    cache: CacheConfig = Field(default_factory=lambda: CacheConfig(enabled=False, ttl=300, max_size=100, vary_by_headers=[]), description="Caching configuration")
    transformations: Optional[TransformationConfig] = Field(None, description="Transformations configuration")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional headers to send with requests")
    active: bool = Field(True, description="Whether the model is active")

class ModelRegistryEntry(BaseModel):
    """Entry in the models registry."""
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(..., description="Unique identifier for the model")
    config_file: str = Field(..., description="Path to the model configuration file")

class GlobalSettings(BaseModel):
    """Global settings for all models."""
    model_config = ConfigDict(populate_by_name=True)
    default_timeout: float = Field(30.0, description="Default timeout in seconds")
    default_max_retries: int = Field(3, description="Default number of retries")
    circuit_breaker: CircuitBreakerSettings = Field(default_factory=lambda: CircuitBreakerSettings(failure_threshold=5, reset_timeout=30.0, exclude_exceptions=[]), description="Default circuit breaker configuration")

class ModelRegistry(BaseModel):
    """Registry of all model configurations."""
    model_config = ConfigDict(populate_by_name=True)
    version: str = Field("1.0.0", description="Registry version")
    name: str = Field("ML Model Orchestrator Registry", description="Registry name")
    description: Optional[str] = Field(None, description="Registry description")
    settings: GlobalSettings = Field(default_factory=lambda: GlobalSettings(default_timeout=30.0, default_max_retries=3, circuit_breaker=CircuitBreakerSettings(failure_threshold=5, reset_timeout=30.0, exclude_exceptions=[])), description="Global settings for all models")
    models: List[ModelRegistryEntry] = Field(..., description="List of model registry entries") 