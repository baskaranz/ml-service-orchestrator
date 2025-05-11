"""
DB/config Pydantic models for the orchestrator service.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, validator, AnyUrl

class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    failure_threshold: int = Field(default=5, ge=1)
    reset_timeout: float = Field(default=60.0, ge=1.0)
    exclude_exceptions: List[str] = Field(default_factory=list, description="List of exception names to exclude from circuit breaker")
    
    @validator("failure_threshold")
    def validate_failure_threshold(cls, v):
        if v < 1:
            raise ValueError("Failure threshold must be at least 1")
        return v
    
    @validator("reset_timeout")
    def validate_reset_timeout(cls, v):
        if v < 1.0:
            raise ValueError("Reset timeout must be at least 1 second")
        return v

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
    """Model configuration."""
    id: Optional[str] = None
    name: str
    description: str
    version: str
    endpoint_url: str
    active: bool = True
    circuit_breaker: Optional[CircuitBreakerConfig] = None
    timeout: float = Field(30.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    headers: Dict[str, str] = Field(default_factory=dict, description="Default headers for requests")
    
    @validator("endpoint_url")
    def validate_endpoint_url(cls, v):
        if v != "dummy" and not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint URL must start with http://, https://, or be 'dummy'")
        return v
    
    @validator("timeout")
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError("Timeout must be greater than 0")
        return v
    
    @validator("max_retries")
    def validate_max_retries(cls, v):
        if v < 0:
            raise ValueError("Max retries must be non-negative")
        return v

class ModelRegistryEntry(BaseModel):
    """Model registry entry."""
    id: str
    config_file: str

class ModelRegistry(BaseModel):
    """Model registry."""
    model_config = ConfigDict(populate_by_name=True, extra='allow', frozen=False)
    version: str
    name: str
    description: str
    models: Dict[str, ModelRegistryEntry] = Field(default_factory=dict)

class GlobalSettings(BaseModel):
    """Global settings for all models."""
    model_config = ConfigDict(populate_by_name=True)
    default_timeout: float = Field(30.0, description="Default timeout in seconds")
    default_max_retries: int = Field(3, description="Default number of retries")
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=lambda: CircuitBreakerConfig(failure_threshold=5, reset_timeout=60.0), description="Default circuit breaker configuration")

    @validator("default_timeout")
    def validate_default_timeout(cls, v):
        if v <= 0:
            raise ValueError("Default timeout must be greater than 0")
        return v

    @validator("default_max_retries")
    def validate_default_max_retries(cls, v):
        if v < 1:
            raise ValueError("Default number of retries must be at least 1")
        return v 