# ML Orchestrator - GitHub Copilot Instructions

This file provides guidance for GitHub Copilot to effectively generate code for the ML Orchestrator service.

## Project Overview
We're building a YAML config-driven FastAPI orchestrator service for ML models. The orchestrator routes incoming requests to the appropriate model endpoints based on configuration. It supports dynamic model registration with zero downtime via hot-reloading of configuration.

## Project Architecture

The ML Orchestrator has these specific architectural components:

1. **Config Layer**
   - `app/config/models_config.py`: YAML model configuration loading
   - `app/config/settings.py`: Environment-based application settings

2. **API Layer**
   - `app/api/routes/orchestrator.py`: Main model request routing
   - `app/api/routes/admin.py`: Admin operations for model management
   - `app/api/routes/health.py`: Health checking and monitoring
   - `app/api/dependencies.py`: FastAPI dependency injection

3. **Core Layer**
   - `app/core/models.py`: Pydantic data models for configuration
   - `app/core/orchestrator.py`: Main orchestration logic and circuit breakers
   - `app/core/exceptions.py`: Custom exception types and handlers

4. **Service Layer**
   - `app/services/model_registry.py`: Model registration and lookups
   - `app/services/proxy.py`: Request proxying to model endpoints

5. **Utilities Layer**
   - `app/utils/http.py`: HTTP client and request handling
   - `app/utils/logging.py`: Structured logging utilities

## Key Patterns to Follow

When generating code for ML Orchestrator, follow these patterns:

### 1. YAML Configuration-Driven Architecture
- Models are defined in YAML with environment variable substitution
- Configuration files are hot-reloaded without service restart
- `ModelConfigManager` handles loading and parsing

### 2. FastAPI Dependency Injection
- Services are provided via dependency injection
- API key validation via `get_api_key` dependency
- Pattern: `service: ServiceClass = Depends(get_service)`

### 3. Async/Await Throughout
- All IO operations use async/await
- HTTP requests use the `HttpClient` in `app/utils/http.py`
- Endpoints are async functions with proper error handling

### 4. Circuit Breaker Pattern
- Implementation in `app/core/orchestrator.py`
- Models have individual circuit breaker configurations
- Failure counting and automatic reset after timeout

### 5. Structured Error Handling
- Custom exception types in `app/core/exceptions.py`
- Exception handlers registered in FastAPI
- Consistent error response format with status codes

### 6. Testing Approach
- Tests mirror application structure in `tests/` directory
- Async tests use `pytest.mark.asyncio`
- Mock usage for external dependencies

## Code Generation Guidelines

When generating code for ML Orchestrator, follow these guidelines:

### Configuration Features
```python
# Example ModelConfig extension
class NewFeatureConfig(BaseModel):
    """Configuration for the new feature."""
    
    enabled: bool = Field(default=False, description="Whether the feature is enabled")
    setting_one: str = Field(default="default", description="First setting")
    setting_two: int = Field(default=10, description="Second setting")
    
    class Config:
        extra = "forbid"

class ModelConfig(BaseModel):
    # Existing fields...
    
    new_feature: Optional[NewFeatureConfig] = Field(
        default=None,
        description="Configuration for the new feature"
    )
```

### Services
```python
# Example service following dependency injection pattern
class NewService:
    """Service for the new feature."""
    
    def __init__(
        self,
        model_registry: ModelRegistryService = Depends(get_model_registry_service)
    ):
        """Initialize the service.
        
        Args:
            model_registry: The model registry service
        """
        self.model_registry = model_registry
    
    async def some_method(self, model_id: str) -> dict:
        """Perform some operation.
        
        Args:
            model_id: The model ID
            
        Returns:
            Operation result
            
        Raises:
            SomeError: If the operation fails
        """
        try:
            # Implementation
            return result
        except Exception as e:
            raise SomeError(f"Operation failed: {str(e)}") from e

# Dependency provider
def get_new_service(
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> NewService:
    """Dependency provider for the new service."""
    return NewService(model_registry)
```

### API Routes
```python
# Example API route following project patterns
router = APIRouter()

@router.post(
    "/some-endpoint/{model_id}",
    response_model=ResponseModel,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse}
    }
)
async def some_endpoint(
    model_id: str,
    request: RequestModel,
    service: NewService = Depends(get_new_service),
    api_key: str = Depends(get_api_key)
):
    """Handle some operation.
    
    Args:
        model_id: The model ID
        request: The request data
        service: The service dependency
        api_key: The API key
        
    Returns:
        The operation result
        
    Raises:
        HTTPException: If the operation fails
    """
    try:
        result = await service.some_method(model_id)
        return result
    except SomeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

### Tests
```python
# Example test following project patterns
@pytest.mark.asyncio
async def test_some_functionality():
    """Test some functionality."""
    # Setup
    mock_dependency = AsyncMock()
    mock_dependency.some_method.return_value = {"result": "value"}
    
    # Execute
    result = await some_function(dependency=mock_dependency)
    
    # Assert
    assert result == {"result": "value"}
    mock_dependency.some_method.assert_called_once_with()
```

## Task-Specific Guidelines

### Config Loading System
- Implement a YAML config loader that can hot-reload configurations
- Support environment variable substitution in YAML configs
- Implement validation for config files using Pydantic models
- Create a singleton registry for model endpoints

### Dynamic Routing
- Implement a dynamic router that maps URL paths to model endpoints
- Support regex patterns for model endpoint matching
- Handle path parameters and query parameters properly
- Support request and response transformations

### Proxy Service
- Implement an async HTTP client for forwarding requests
- Support timeout configuration 
- Implement circuit breaker pattern for fault tolerance
- Add request/response logging with sensitive data redaction
- Support response caching for idempotent operations

### Admin API
- Implement endpoints for adding/updating/removing model configurations
- Implement validation for model configurations
- Add authentication and authorization for admin endpoints
- Implement audit logging for admin operations

## More Guidance

For more detailed guidance, see the component-specific instructions and examples:

### Layer-Specific Instructions

These files provide detailed guidance for each architectural layer:

- `instructions/config_layer.md`: Instructions for config-related code
- `instructions/api_layer.md`: Instructions for API-related code
- `instructions/core_layer.md`: Instructions for core domain code
- `instructions/service_layer.md`: Instructions for service-related code
- `instructions/test_patterns.md`: Instructions for test-related code

### Component Examples

The `component-examples/` directory contains complete reference implementations of key patterns:

- `component-examples/circuit_breaker.py`: Circuit breaker pattern implementation
- `component-examples/model_config.py`: YAML configuration system
- `component-examples/cache_implementation.py`: Caching pattern for optimization
- `component-examples/auth_scheme.py`: Authentication and authorization
- `component-examples/error_handling.py`: Error handling and response formatting
- `component-examples/middleware.py`: Request processing middleware
- `component-examples/request_response_transform.py`: Request/response transformation
- `component-examples/testing_patterns.py`: Test patterns and fixtures

These examples demonstrate complete implementations of common patterns used throughout the ML Orchestrator. They serve as reference code that should be followed when implementing similar functionality.