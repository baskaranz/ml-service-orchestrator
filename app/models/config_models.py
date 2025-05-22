"""
DB/config Pydantic models for the orchestrator service.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_validator

from app.models.auth_config import AuthConfig


class CircuitBreakerConfig(BaseModel):
    """Base circuit breaker configuration."""

    enabled: bool = Field(default=True, description="Whether the circuit breaker is enabled")
    failure_threshold: int = Field(
        default=5, ge=1, description="Number of failures before opening circuit"
    )
    reset_timeout: float = Field(
        default=60.0, ge=1.0, description="Seconds to wait before attempting to close circuit"
    )
    half_open_timeout: float = Field(default=30.0, ge=1.0, description="Seconds in half-open state")
    success_threshold: int = Field(
        default=2, ge=1, description="Successful requests to close circuit"
    )


class GlobalCircuitBreakerConfig(BaseModel):
    """Global circuit breaker configuration."""

    enabled: bool = Field(default=True, description="Whether global circuit breaking is enabled")
    default: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig, description="Default circuit breaker settings"
    )
    per_model_overrides: Dict[str, CircuitBreakerConfig] = Field(
        default_factory=dict, description="Per-model circuit breaker overrides"
    )


class PlatformConfig(BaseModel):
    """Platform configuration."""

    timeout: float = Field(default=30.0, description="Default request timeout in seconds")
    max_retries: int = Field(default=3, description="Default maximum number of retry attempts")
    health_check: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": True,
            "interval": 30,
            "timeout": 5,
            "failure_threshold": 3,
            "success_threshold": 2,
        },
        description="Health check configuration",
    )
    circuit_breaker: GlobalCircuitBreakerConfig = Field(
        default_factory=GlobalCircuitBreakerConfig,
        description="Global circuit breaker configuration",
    )

    @field_validator("health_check", "circuit_breaker", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, BaseModel):
            return v.model_dump()
        if isinstance(v, dict):
            return v
        # Let Pydantic's default validation handle other types or raise an error
        return v


class BasicErrorHandlingConfig(BaseModel):
    """Basic error handling configuration."""

    model_config = ConfigDict(populate_by_name=True)
    enabled: bool = Field(default=True, description="Whether basic error handling is enabled")
    max_retries: int = Field(default=3, ge=0, description="Maximum number of retries")
    retry_delay: float = Field(default=1.0, ge=0.0, description="Initial retry delay in seconds")
    max_retry_delay: float = Field(
        default=30.0, ge=0.0, description="Maximum retry delay in seconds"
    )
    backoff_factor: float = Field(default=2.0, ge=1.0, description="Exponential backoff factor")


class LLMProviderConfig(BaseModel):
    """LLM provider configuration."""

    model_config = ConfigDict(populate_by_name=True)
    type: str = Field(..., description="LLM provider type (huggingface or ollama)")
    model_name: str = Field(..., description="Name of the LLM model to use")
    timeout: int = Field(default=30, ge=1, description="Timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum number of retries")
    api_key: Optional[str] = Field(default=None, description="API key for the LLM provider")


class LLMErrorHandlingConfig(BaseModel):
    """LLM-based error handling configuration."""

    model_config = ConfigDict(populate_by_name=True)
    enabled: bool = Field(default=False, description="Whether LLM-based error handling is enabled")
    provider: Optional[LLMProviderConfig] = Field(
        default=None, description="LLM provider configuration"
    )


class ErrorHandlingConfig(BaseModel):
    """Error handling configuration."""

    model_config = ConfigDict(populate_by_name=True)
    basic: BasicErrorHandlingConfig = Field(default_factory=BasicErrorHandlingConfig)
    llm: LLMErrorHandlingConfig = Field(default_factory=LLMErrorHandlingConfig)


class BasicCircuitBreakerConfig(BaseModel):
    """Basic circuit breaker configuration."""

    model_config = ConfigDict(populate_by_name=True)
    enabled: bool = Field(default=True, description="Whether basic circuit breaker is enabled")
    failure_threshold: int = Field(
        default=5, ge=1, description="Number of failures before opening circuit"
    )
    reset_timeout: float = Field(
        default=60.0, ge=1.0, description="Seconds to wait before attempting to close circuit"
    )
    half_open_timeout: float = Field(default=30.0, ge=1.0, description="Seconds in half-open state")
    success_threshold: int = Field(
        default=2, ge=1, description="Successful requests to close circuit"
    )


class ErrorTypeConfig(BaseModel):
    """Error type specific configuration."""

    model_config = ConfigDict(populate_by_name=True)
    threshold_multiplier: float = Field(..., ge=0.0, description="Multiplier for failure threshold")
    timeout_multiplier: float = Field(..., ge=0.0, description="Multiplier for reset timeout")


class LLMCircuitBreakerConfig(BaseModel):
    """LLM-based circuit breaker configuration."""

    model_config = ConfigDict(populate_by_name=True)
    enabled: bool = Field(default=False, description="Whether LLM-based circuit breaker is enabled")
    max_threshold: int = Field(default=10, ge=1, description="Maximum failure threshold")
    min_threshold: int = Field(default=3, ge=1, description="Minimum failure threshold")
    max_timeout: float = Field(default=300.0, ge=1.0, description="Maximum reset timeout")
    min_timeout: float = Field(default=30.0, ge=1.0, description="Minimum reset timeout")
    error_types: Dict[str, ErrorTypeConfig] = Field(
        default_factory=lambda: {
            "rate_limit": ErrorTypeConfig(threshold_multiplier=1.5, timeout_multiplier=0.5),
            "transient": ErrorTypeConfig(threshold_multiplier=1.2, timeout_multiplier=0.8),
            "permanent": ErrorTypeConfig(threshold_multiplier=0.6, timeout_multiplier=2.0),
        }
    )


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    model_config = ConfigDict(populate_by_name=True)
    basic: BasicCircuitBreakerConfig = Field(default_factory=BasicCircuitBreakerConfig)
    llm: LLMCircuitBreakerConfig = Field(default_factory=LLMCircuitBreakerConfig)


class RequestConfig(BaseModel):
    """Request configuration."""

    model_config = ConfigDict(populate_by_name=True)
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum number of retries")
    retry_delay: float = Field(default=1.0, ge=0.0, description="Initial retry delay in seconds")
    max_retry_delay: float = Field(
        default=30.0, ge=0.0, description="Maximum retry delay in seconds"
    )
    backoff_factor: float = Field(default=2.0, ge=1.0, description="Exponential backoff factor")


class HealthCheckConfig(BaseModel):
    """Health check configuration."""

    model_config = ConfigDict(populate_by_name=True)
    enabled: bool = Field(default=True, description="Whether health checks are enabled")
    interval: int = Field(default=30, ge=1, description="Seconds between health checks")
    timeout: int = Field(default=5, ge=1, description="Health check timeout in seconds")
    failure_threshold: int = Field(
        default=3, ge=1, description="Number of failures before marking unhealthy"
    )
    success_threshold: int = Field(
        default=2, ge=1, description="Number of successes before marking healthy"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    model_config = ConfigDict(populate_by_name=True)
    level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    format: str = Field(default="json", description="Log format (json or text)")
    include_metadata: bool = Field(default=True, description="Include request/response metadata")
    sensitive_fields: List[str] = Field(
        default_factory=lambda: ["api_key", "password", "token"],
        description="Fields to mask in logs",
    )


class RetryConfig(BaseModel):
    """Configuration for retrying failed requests."""

    model_config = ConfigDict(populate_by_name=True)
    max_attempts: int = Field(default=3, ge=1, description="Maximum number of retry attempts")
    initial_delay: float = Field(
        default=1.0, ge=0.1, description="Initial delay between retries in seconds"
    )
    max_delay: float = Field(
        default=30.0, ge=1.0, description="Maximum delay between retries in seconds"
    )
    backoff_factor: float = Field(default=2.0, ge=1.0, description="Exponential backoff factor")
    jitter: bool = Field(default=True, description="Whether to add jitter to retry delays")
    retry_on_status_codes: List[int] = Field(
        default_factory=lambda: [408, 429, 500, 502, 503, 504],
        description="HTTP status codes to retry on",
    )

    @field_validator("retry_on_status_codes", mode="before")
    def validate_status_codes(cls, v):
        if v is None:
            return [408, 429, 500, 502, 503, 504]
        return v


class ModelMetadata(BaseModel):
    """Metadata for a model."""

    model_config = ConfigDict(populate_by_name=True)
    owner: str = Field(default="unknown", description="Owner of the model")
    version: str = Field(default="1.0.0", description="Version of the model")
    description: Optional[str] = Field(default=None, description="Description of the model")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    @field_validator("created_at", "updated_at", mode="before")
    def set_timestamps(cls, v):
        if v is None:
            from datetime import datetime

            return datetime.utcnow().isoformat()
        return v


class ModelConfig(BaseModel):
    """Configuration for a model."""

    id: str = Field(..., description="Unique identifier of the model")
    name: str = Field(..., description="Display name of the model")
    endpoint_url: str = Field(..., description="URL endpoint for model predictions")
    active: bool = Field(default=True, description="Whether the model is active")

    # REST API Configuration
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")

    # Optional configurations
    health_check: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "enabled": True,
            "endpoint": "/health",
            "interval": 30,
            "timeout": 5,
            "failure_threshold": 3,
            "success_threshold": 2,
        },
        description="Health check configuration",
    )

    headers: Optional[Dict[str, str]] = Field(
        default_factory=lambda: {"Content-Type": "application/json"},
        description="Custom headers to include in requests",
    )

    # Connection pooling
    # Connection pooling settings
    max_connections: int = Field(
        default=100, ge=1, le=1000, description="Maximum number of connections in the pool"
    )
    max_keepalive_connections: int = Field(
        default=50, ge=1, le=500, description="Maximum number of keep-alive connections"
    )
    keepalive_timeout: int = Field(
        default=60, ge=1, le=300, description="Keep-alive timeout in seconds"
    )
    pool_connections: int = Field(
        default=10, ge=1, le=100, description="Number of connection pools to cache"
    )
    pool_maxsize: int = Field(
        default=100, ge=1, le=1000, description="Maximum number of connections per pool"
    )
    http2: bool = Field(
        default=False,
        description="Whether to enable HTTP/2 support. Defaults to False. Set to True only if the target server supports HTTP/2 and you have installed the required dependencies (httpx[http2]).",
    )
    platform: Optional[Union[PlatformConfig, Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Platform-specific configuration for the model as a PlatformConfig object or dictionary",
    )

    @field_validator("platform", mode="before")
    @classmethod
    def validate_platform(cls, v: Any) -> Optional[Union[PlatformConfig, Dict[str, Any]]]:
        if v is None or isinstance(v, (PlatformConfig, dict)):
            return v
        if isinstance(v, str):
            try:
                import json

                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError(
                    "Platform config must be a valid JSON string, dict, or PlatformConfig object"
                )
        raise TypeError("Platform config must be a dict, JSON string, or PlatformConfig object")

    auth: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "enabled": False,
            "type": "api_key",  # api_key, bearer_token, basic_auth, none
            "header_name": "X-API-Key",
            "api_key": "${API_KEY}",  # Use environment variables
        },
        description="Authentication configuration",
    )

    # Logging configuration is handled separately

    class Config:
        """Pydantic model configuration."""

        json_encoders = {AnyUrl: str}


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
    value: Optional[str] = Field(
        default=None, description="Authentication value (API key, token, etc.)"
    )


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
    request_template: Optional[str] = Field(
        None, description="Jinja2 template for request transformation"
    )
    response_template: Optional[str] = Field(
        None, description="Jinja2 template for response transformation"
    )


class ModelRegistry(BaseModel):
    """Registry of model configurations."""

    name: str = Field(default="Model Registry", description="Name of the registry")
    description: str = Field(
        default="Registry of model configurations", description="Description of the registry"
    )
    models: Dict[str, "ModelConfig"] = Field(
        default_factory=dict, description="Model configurations"
    )


# Update forward references
ModelRegistry.update_forward_refs()


class GlobalSettings(BaseModel):
    """Global settings for all models."""

    model_config = ConfigDict(populate_by_name=True)
    default_timeout: int = Field(30, ge=1, description="Default timeout in seconds")
    default_max_retries: int = Field(3, ge=0, description="Default number of retries")
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(
            basic=BasicCircuitBreakerConfig(
                failure_threshold=5, reset_timeout=60.0, half_open_timeout=30.0, success_threshold=2
            ),
            llm=LLMCircuitBreakerConfig(
                max_threshold=10, min_threshold=3, max_timeout=300.0, min_timeout=30.0
            ),
        ),
        description="Default circuit breaker configuration",
    )

    @field_validator("default_timeout")
    @classmethod
    def validate_default_timeout(cls, v: int) -> int:
        """Validate default timeout."""
        if v < 1:
            raise ValueError("default_timeout must be at least 1 second")
        return v

    @field_validator("default_max_retries")
    @classmethod
    def validate_default_max_retries(cls, v: int) -> int:
        """Validate default max retries."""
        if v < 0:
            raise ValueError("default_max_retries must be non-negative")
        return v
