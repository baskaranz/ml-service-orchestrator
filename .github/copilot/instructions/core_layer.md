# ML Orchestrator - Core Layer Instructions

This file provides detailed guidance for implementing core domain code in the ML Orchestrator service.

## Overview

The core layer contains the central domain logic of the ML Orchestrator:
1. Core data models using Pydantic
2. Orchestration logic for request handling
3. Circuit breaker implementation
4. Custom exception types and handlers

## Key Files

- `app/core/models.py`: Pydantic data models for configuration
- `app/core/orchestrator.py`: Main orchestration logic and circuit breakers
- `app/core/exceptions.py`: Custom exception types and handlers

## Data Models

The primary data models are defined in `app/core/models.py`:

```python
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, validator

class CircuitBreakerSettings(BaseModel):
    """Settings for circuit breaker pattern."""
    
    failure_threshold: int = Field(
        default=5,
        description="Number of failures before opening the circuit"
    )
    reset_timeout: float = Field(
        default=30.0,
        description="Seconds to wait before attempting to close the circuit"
    )
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "forbid"

class AuthType(str, Enum):
    """Authentication type enum."""
    
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC = "basic"

class AuthConfig(BaseModel):
    """Authentication configuration."""
    
    type: AuthType = Field(default=AuthType.NONE, description="Authentication type")
    key_name: Optional[str] = Field(
        default=None,
        description="Header name for API key authentication"
    )
    key_value: Optional[str] = Field(
        default=None,
        description="API key or token value"
    )
    username: Optional[str] = Field(
        default=None,
        description="Username for basic authentication"
    )
    password: Optional[str] = Field(
        default=None,
        description="Password for basic authentication"
    )
    location: Optional[str] = Field(
        default="header",
        description="Location of the auth data (header, query, etc.)"
    )
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "forbid"
    
    @validator("key_name")
    def validate_key_name(cls, v, values):
        """Validate that key_name is provided for API key auth."""
        if values.get("type") == AuthType.API_KEY and not v:
            raise ValueError("key_name is required for API key authentication")
        return v
    
    @validator("key_value")
    def validate_key_value(cls, v, values):
        """Validate that key_value is provided for API key or bearer token auth."""
        auth_type = values.get("type")
        if auth_type in [AuthType.API_KEY, AuthType.BEARER_TOKEN] and not v:
            raise ValueError(f"key_value is required for {auth_type} authentication")
        return v

class ModelConfig(BaseModel):
    """Configuration for a model endpoint."""
    
    id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Display name for the model")
    description: str = Field(default="", description="Description of the model")
    endpoint_url: str = Field(..., description="URL for the model endpoint")
    version: str = Field(default="1.0.0", description="Model version")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    
    # Nested configuration objects
    circuit_breaker: Optional[CircuitBreakerSettings] = Field(
        default=None,
        description="Circuit breaker settings"
    )
    auth: Optional[AuthConfig] = Field(
        default=None,
        description="Authentication configuration"
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional headers to send with requests"
    )
    active: bool = Field(default=True, description="Whether the model is active")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "forbid"
```

When extending these models, follow these patterns:
1. Use nested Pydantic models for complex configuration
2. Add proper validation with validators
3. Use Field with descriptions and defaults
4. Set `extra = "forbid"` to prevent unexpected fields

## Orchestration Logic

The orchestration logic is implemented in `app/core/orchestrator.py`:

```python
import asyncio
import time
from typing import Dict, Optional, Any

from app.core.exceptions import CircuitBreakerError
from app.core.models import ModelConfig, AuthType
from app.utils.http import HttpClient
from app.utils.logging import get_logger

logger = get_logger(__name__)

class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(self, failure_threshold: int, reset_timeout: float):
        """Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Seconds to wait before attempting to close the circuit
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self._is_open = False
    
    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if not self._is_open:
                logger.warning("Circuit breaker opened due to failures")
            self._is_open = True
    
    def record_success(self) -> None:
        """Record a success and reset the failure count."""
        self.failure_count = 0
        self._is_open = False
    
    def is_open(self) -> bool:
        """Check if the circuit is open.
        
        Returns:
            True if the circuit is open, False otherwise
        """
        # Check if it's time to try closing the circuit
        if self._is_open and time.time() - self.last_failure_time > self.reset_timeout:
            logger.info("Attempting to close circuit breaker")
            self._is_open = False
            self.failure_count = 0
        
        return self._is_open

class Orchestrator:
    """Orchestrates requests to model endpoints."""
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.http_client = HttpClient()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def get_circuit_breaker(self, model_id: str, config: ModelConfig) -> CircuitBreaker:
        """Get or create a circuit breaker for a model.
        
        Args:
            model_id: The model ID
            config: The model configuration
            
        Returns:
            The circuit breaker for the model
        """
        if model_id not in self.circuit_breakers:
            # Use model config or default settings
            if config.circuit_breaker:
                failure_threshold = config.circuit_breaker.failure_threshold
                reset_timeout = config.circuit_breaker.reset_timeout
            else:
                # Default values
                failure_threshold = 5
                reset_timeout = 30.0
            
            self.circuit_breakers[model_id] = CircuitBreaker(
                failure_threshold=failure_threshold,
                reset_timeout=reset_timeout
            )
        
        return self.circuit_breakers[model_id]
    
    async def proxy_request(
        self,
        model_id: str,
        request_data: Any,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Proxy a request to a model endpoint.
        
        Args:
            model_id: The model ID
            request_data: The request data
            headers: Additional headers to send
            
        Returns:
            The model response
            
        Raises:
            CircuitBreakerError: If the circuit breaker is open
            HTTPError: If the request fails
        """
        # Get model configuration from registry
        model_config = self.model_registry.get_model_config(model_id)
        
        # Check if model is active
        if not model_config.active:
            raise ValueError(f"Model {model_id} is not active")
        
        # Check circuit breaker
        circuit_breaker = self.get_circuit_breaker(model_id, model_config)
        if circuit_breaker.is_open():
            raise CircuitBreakerError(
                model_id=model_id,
                message=f"Circuit breaker is open for model {model_id}"
            )
        
        # Prepare request headers
        request_headers = {}
        if headers:
            request_headers.update(headers)
        
        # Add model-specific headers
        if model_config.headers:
            request_headers.update(model_config.headers)
        
        # Add authentication if configured
        if model_config.auth:
            self._add_auth_headers(request_headers, model_config.auth)
        
        try:
            # Send request to model endpoint
            response = await self.http_client.request(
                method="POST",
                url=model_config.endpoint_url,
                headers=request_headers,
                json=request_data,
                timeout=model_config.timeout
            )
            
            # Record success
            circuit_breaker.record_success()
            
            return response
        except Exception as e:
            # Record failure
            circuit_breaker.record_failure()
            logger.error(f"Request to model {model_id} failed: {str(e)}")
            raise
    
    def _add_auth_headers(self, headers: Dict[str, str], auth_config: AuthConfig) -> None:
        """Add authentication headers to a request.
        
        Args:
            headers: Headers dictionary to update
            auth_config: Authentication configuration
        """
        if auth_config.type == AuthType.API_KEY:
            headers[auth_config.key_name] = auth_config.key_value
        elif auth_config.type == AuthType.BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {auth_config.key_value}"
        # Other auth types...
```

When enhancing the orchestrator, follow these patterns:
1. Maintain backward compatibility for existing code
2. Use proper error handling and circuit breaker patterns
3. Implement proper logging at appropriate levels
4. Use type hints consistently

## Circuit Breaker Pattern

The ML Orchestrator uses the circuit breaker pattern for fault tolerance:

```python
class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(self, failure_threshold: int, reset_timeout: float):
        """Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Seconds to wait before attempting to close the circuit
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self._is_open = False
    
    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if not self._is_open:
                logger.warning("Circuit breaker opened due to failures")
            self._is_open = True
    
    def record_success(self) -> None:
        """Record a success and reset the failure count."""
        self.failure_count = 0
        self._is_open = False
    
    def is_open(self) -> bool:
        """Check if the circuit is open.
        
        Returns:
            True if the circuit is open, False otherwise
        """
        # Check if it's time to try closing the circuit
        if self._is_open and time.time() - self.last_failure_time > self.reset_timeout:
            logger.info("Attempting to close circuit breaker")
            self._is_open = False
            self.failure_count = 0
        
        return self._is_open
```

When enhancing the circuit breaker, you might:
1. Add a half-open state for more graceful recovery
2. Implement more sophisticated failure detection
3. Add metrics for circuit breaker state changes
4. Improve logging for better observability

Example enhancement for half-open state:

```python
class CircuitBreaker:
    """Enhanced circuit breaker with half-open state."""
    
    # State enum
    class State:
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"
    
    def __init__(self, failure_threshold: int, reset_timeout: float):
        """Initialize the circuit breaker."""
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = self.State.CLOSED
        self.test_request_in_progress = False
    
    def record_failure(self) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == self.State.HALF_OPEN:
            # Failed test request, back to open
            logger.warning("Test request failed, circuit breaker reopened")
            self.state = self.State.OPEN
            self.test_request_in_progress = False
        elif self.failure_count >= self.failure_threshold:
            if self.state != self.State.OPEN:
                logger.warning("Circuit breaker opened due to failures")
                self.state = self.State.OPEN
    
    def record_success(self) -> None:
        """Record a success."""
        if self.state == self.State.HALF_OPEN:
            # Successful test request, close circuit
            logger.info("Test request succeeded, circuit breaker closed")
            self.state = self.State.CLOSED
            self.failure_count = 0
            self.test_request_in_progress = False
        else:
            # Normal success, reset failure count
            self.failure_count = 0
    
    def is_open(self) -> bool:
        """Check if the circuit is open."""
        if self.state == self.State.OPEN:
            # Check if it's time to try a test request
            if time.time() - self.last_failure_time > self.reset_timeout:
                logger.info("Transitioning to half-open state for test request")
                self.state = self.State.HALF_OPEN
                return False  # Allow the test request
            return True  # Still open
        
        if self.state == self.State.HALF_OPEN and self.test_request_in_progress:
            return True  # Only one test request at a time
        
        if self.state == self.State.HALF_OPEN:
            # Mark that we're starting a test request
            self.test_request_in_progress = True
            return False
        
        return False  # Circuit is closed
```

## Custom Exceptions

Custom exceptions are defined in `app/core/exceptions.py`:

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse

class ModelRequestError(Exception):
    """Exception raised when a model request fails."""
    
    def __init__(self, message: str, status_code: int = 500):
        """Initialize the exception.
        
        Args:
            message: The error message
            status_code: The HTTP status code
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class CircuitBreakerError(Exception):
    """Exception raised when a circuit breaker is open."""
    
    def __init__(self, model_id: str, message: Optional[str] = None):
        """Initialize the exception.
        
        Args:
            model_id: The model ID with the open circuit
            message: Optional error message
        """
        self.model_id = model_id
        self.message = message or f"Circuit breaker is open for model {model_id}"
        super().__init__(self.message)

class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str):
        """Initialize the exception.
        
        Args:
            message: The error message
        """
        self.message = message
        super().__init__(self.message)

# Exception handlers
def model_request_exception_handler(
    request: Request,
    exc: ModelRequestError
) -> JSONResponse:
    """Handle ModelRequestError exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "model_request_error",
            "detail": exc.message
        }
    )

def circuit_breaker_exception_handler(
    request: Request,
    exc: CircuitBreakerError
) -> JSONResponse:
    """Handle CircuitBreakerError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "circuit_breaker_open",
            "detail": exc.message,
            "model_id": exc.model_id
        }
    )

def configuration_exception_handler(
    request: Request,
    exc: ConfigurationError
) -> JSONResponse:
    """Handle ConfigurationError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "configuration_error",
            "detail": exc.message
        }
    )

def setup_exception_handlers(app: FastAPI) -> None:
    """Set up exception handlers for the application."""
    app.add_exception_handler(ModelRequestError, model_request_exception_handler)
    app.add_exception_handler(CircuitBreakerError, circuit_breaker_exception_handler)
    app.add_exception_handler(ConfigurationError, configuration_exception_handler)
```

When adding new exception types, follow these patterns:
1. Create a specific exception class for each error type
2. Include relevant context in the exception
3. Create a corresponding exception handler
4. Register the handler in the `setup_exception_handlers` function
5. Use consistent error response format

## Testing Core Layer

When testing core layer components, follow these patterns:

```python
@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker for testing."""
    return CircuitBreaker(failure_threshold=3, reset_timeout=5.0)

def test_circuit_breaker_initially_closed(circuit_breaker):
    """Test that circuit breaker is initially closed."""
    assert not circuit_breaker.is_open()

def test_circuit_breaker_opens_after_threshold(circuit_breaker):
    """Test that circuit breaker opens after threshold failures."""
    # Record failures up to threshold
    for _ in range(3):
        circuit_breaker.record_failure()
    
    # Verify circuit is open
    assert circuit_breaker.is_open()

@pytest.mark.asyncio
async def test_orchestrator_proxy_request():
    """Test proxying a request through the orchestrator."""
    # Mock dependencies
    mock_http_client = AsyncMock()
    mock_http_client.request.return_value = {"result": "success"}
    
    mock_registry = MagicMock()
    mock_registry.get_model_config.return_value = ModelConfig(
        id="test_model",
        name="Test Model",
        endpoint_url="http://example.com/test"
    )
    
    # Create orchestrator with mocks
    orchestrator = Orchestrator()
    orchestrator.http_client = mock_http_client
    orchestrator.model_registry = mock_registry
    
    # Proxy request
    result = await orchestrator.proxy_request(
        model_id="test_model",
        request_data={"prompt": "test"}
    )
    
    # Verify result
    assert result == {"result": "success"}
    mock_http_client.request.assert_called_once()
    
    # Verify URL and method
    call_args = mock_http_client.request.call_args[1]
    assert call_args["url"] == "http://example.com/test"
    assert call_args["method"] == "POST"
```

For testing with async code, use the `pytest.mark.asyncio` decorator and `AsyncMock` for mocking coroutines.