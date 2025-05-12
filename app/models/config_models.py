"""
DB/config Pydantic models for the orchestrator service.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, validator, AnyUrl

class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    model_config = ConfigDict(populate_by_name=True)
    failure_threshold: int = Field(default=5, description="Number of failures before opening circuit")
    reset_timeout: float = Field(default=30.0, description="Time in seconds before attempting to close circuit")
    exclude_exceptions: List[str] = Field(default_factory=list, description="List of exception names to exclude from circuit breaker")

    @validator("failure_threshold")
    def validate_failure_threshold(cls, v: int) -> int:
        """Validate failure threshold."""
        if v < 1:
            raise ValueError("Failure threshold must be at least 1")
        return v

    @validator("reset_timeout")
    def validate_reset_timeout(cls, v: float) -> float:
        """Validate reset timeout."""
        if v <= 0:
            raise ValueError("Reset timeout must be positive")
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
    """Authentication configuration."""
    enabled: bool = Field(default=False, description="Whether authentication is enabled")
    type: str = Field(default="api_key", description="Authentication type (api_key, bearer, basic)")
    header_name: Optional[str] = Field(default=None, description="Header name for API key")
    query_param: Optional[str] = Field(default=None, description="Query parameter name for API key")
    value: Optional[str] = Field(default=None, description="Authentication value (API key, token, etc.)")

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

class LLMProviderConfig(BaseModel):
    """Configuration for LLM providers."""
    type: str = Field(..., description="Type of LLM provider (huggingface or ollama)")
    model_name: Optional[str] = Field(None, description="Name of the model to use")
    timeout: Optional[int] = Field(30, description="Timeout in seconds for API calls")
    max_retries: Optional[int] = Field(3, description="Maximum number of retries for API calls")
    api_key: Optional[str] = Field(None, description="API key for the provider (optional)")

class ModelConfig(BaseModel):
    """Model configuration."""
    id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Display name of the model")
    description: str = Field(..., description="Description of the model")
    version: str = Field(..., description="Version of the model")
    endpoint_url: str = Field(..., description="URL of the model endpoint")
    active: bool = Field(default=True, description="Whether the model is active")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    type: Optional[str] = Field(default=None, description="Type of the model (e.g., classification, regression)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the model")
    llm_provider: Optional[LLMProviderConfig] = Field(None, description="LLM provider configuration")

    @validator("endpoint_url")
    def validate_endpoint_url(cls, v: str) -> str:
        """Validate endpoint URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint URL must start with http:// or https://")
        return v

    @validator("timeout")
    def validate_timeout(cls, v: float) -> float:
        """Validate timeout."""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    @validator("max_retries")
    def validate_max_retries(cls, v: int) -> int:
        """Validate max retries."""
        if v < 0:
            raise ValueError("Max retries cannot be negative")
        return v

class ModelRegistry(BaseModel):
    """Model registry configuration."""
    version: str = Field(..., description="Version of the registry")
    name: str = Field(..., description="Name of the registry")
    description: str = Field(..., description="Description of the registry")
    models: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Dictionary of model configurations")

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