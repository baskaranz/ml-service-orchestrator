# ML Orchestrator - API Layer Instructions

This file provides detailed guidance for implementing API-related code in the ML Orchestrator service.

## Overview

The API layer is responsible for:
1. Defining FastAPI routes and endpoints
2. Handling HTTP requests and responses
3. Managing dependencies and authentication
4. Validating request data
5. Error handling

## Key Files

- `app/api/routes/orchestrator.py`: Main model request routing
- `app/api/routes/admin.py`: Admin operations for model management
- `app/api/routes/health.py`: Health checking and monitoring
- `app/api/dependencies.py`: FastAPI dependency injection

## FastAPI Dependency Injection

The ML Orchestrator uses FastAPI's dependency injection system extensively. Common dependencies are defined in `app/api/dependencies.py`:

```python
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# API key security scheme for admin endpoints
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> str:
    """Validate the API key for admin endpoints.
    
    Args:
        api_key: API key from request header
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If the API key is invalid
    """
    # Skip validation if admin API key is not configured
    if not settings.ADMIN_API_KEY:
        return ""
    
    # Check if the provided API key matches the configured key
    if api_key == settings.ADMIN_API_KEY:
        return api_key
    
    # Invalid API key
    logger.warning("Invalid API key attempt")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key"
    )
```

Service dependencies are defined in the respective service files:

```python
def get_model_registry_service() -> ModelRegistryService:
    """Dependency provider for the model registry service."""
    config_manager = ModelConfigManager(
        config_dir=settings.CONFIG_DIR,
        registry_file=settings.MODELS_REGISTRY_FILE
    )
    return ModelRegistryService(config_manager)

def get_orchestrator() -> Orchestrator:
    """Dependency provider for the orchestrator."""
    return Orchestrator()

def get_proxy_service(
    model_registry: ModelRegistryService = Depends(get_model_registry_service),
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> ProxyService:
    """Dependency provider for the proxy service."""
    return ProxyService(model_registry, orchestrator)
```

When implementing new endpoints, follow this pattern for dependency injection.

## API Routes

### Orchestrator Routes

The main orchestrator routes are defined in `app/api/routes/orchestrator.py`:

```python
from fastapi import APIRouter, Depends, Request, status

from app.core.exceptions import ModelRequestError
from app.services.proxy import ProxyService, get_proxy_service

router = APIRouter()

@router.post(
    "/{model_id}",
    status_code=status.HTTP_200_OK
)
async def proxy_request(
    model_id: str,
    request: Request,
    proxy_service: ProxyService = Depends(get_proxy_service)
):
    """Proxy a request to a model endpoint.
    
    Args:
        model_id: The model ID to proxy to
        request: The FastAPI request object
        proxy_service: The proxy service
        
    Returns:
        The model response
        
    Raises:
        HTTPException: If the model doesn't exist
        ModelRequestError: If the request fails
    """
    return await proxy_service.proxy_to_model(model_id, request)
```

### Admin Routes

Admin routes for managing model configurations are defined in `app/api/routes/admin.py`:

```python
from fastapi import APIRouter, Depends, status, Body, HTTPException

from app.api.dependencies import get_api_key
from app.core.models import ModelConfig
from app.services.model_registry import ModelRegistryService, get_model_registry_service

router = APIRouter()

@router.get(
    "/models",
    response_model=List[ModelConfig],
    status_code=status.HTTP_200_OK
)
async def list_models(
    model_registry: ModelRegistryService = Depends(get_model_registry_service),
    api_key: str = Depends(get_api_key)
):
    """List all registered models.
    
    Args:
        model_registry: The model registry service
        api_key: The API key for authentication
        
    Returns:
        List of model configurations
    """
    return model_registry.list_models()

@router.get(
    "/models/{model_id}",
    response_model=ModelConfig,
    status_code=status.HTTP_200_OK
)
async def get_model(
    model_id: str,
    model_registry: ModelRegistryService = Depends(get_model_registry_service),
    api_key: str = Depends(get_api_key)
):
    """Get a model configuration.
    
    Args:
        model_id: The model ID
        model_registry: The model registry service
        api_key: The API key for authentication
        
    Returns:
        The model configuration
        
    Raises:
        HTTPException: If the model doesn't exist
    """
    try:
        return model_registry.get_model_config(model_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

@router.post(
    "/models",
    response_model=ModelConfig,
    status_code=status.HTTP_201_CREATED
)
async def add_model(
    model: ModelConfig = Body(...),
    model_registry: ModelRegistryService = Depends(get_model_registry_service),
    api_key: str = Depends(get_api_key)
):
    """Add a new model configuration.
    
    Args:
        model: The model configuration
        model_registry: The model registry service
        api_key: The API key for authentication
        
    Returns:
        The added model configuration
        
    Raises:
        HTTPException: If the model already exists
    """
    try:
        return await model_registry.add_model(model)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
```

### Health Routes

Health check routes are defined in `app/api/routes/health.py`:

```python
from fastapi import APIRouter, Depends, status

from app.core.models import HealthStatus, HealthCheck, SystemHealth
from app.services.model_registry import ModelRegistryService, get_model_registry_service

router = APIRouter()

@router.get(
    "",
    response_model=HealthCheck,
    status_code=status.HTTP_200_OK
)
async def health_check():
    """Get basic health status of the service."""
    return HealthCheck(
        status="ok",
        version=settings.APP_VERSION
    )

@router.get(
    "/details",
    response_model=SystemHealth,
    status_code=status.HTTP_200_OK
)
async def health_details(
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
):
    """Get detailed health status of the service."""
    # Check model registry health
    registry_status = "ok"
    registry_message = None
    
    try:
        models = model_registry.list_models()
        model_count = len(models)
        registry_message = f"Registry contains {model_count} models"
    except Exception as e:
        registry_status = "error"
        registry_message = str(e)
    
    # Assemble health status
    components = {
        "model_registry": {
            "status": registry_status,
            "message": registry_message
        }
    }
    
    # Determine overall status
    overall_status = "ok"
    if "error" in [comp["status"] for comp in components.values()]:
        overall_status = "error"
    elif "warning" in [comp["status"] for comp in components.values()]:
        overall_status = "warning"
    
    return SystemHealth(
        status=overall_status,
        version=settings.APP_VERSION,
        components=components
    )
```

## API Request and Response Models

Request and response models are defined using Pydantic in `app/core/models.py`:

```python
class HealthStatus(str, Enum):
    """Health status enum."""
    
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"

class HealthCheck(BaseModel):
    """Basic health check response."""
    
    status: HealthStatus
    version: str

class SystemHealth(BaseModel):
    """Detailed system health response."""
    
    status: HealthStatus
    version: str
    components: Dict[str, Dict[str, Any]]
```

When adding new endpoints, define appropriate Pydantic models for request and response validation.

## Error Handling

Error handling is centralized using FastAPI exception handlers defined in `app/core/exceptions.py`:

```python
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

def model_request_exception_handler(
    request: Request,
    exc: ModelRequestError
) -> JSONResponse:
    """Handle ModelRequestError exceptions.
    
    Args:
        request: The request that caused the exception
        exc: The exception
        
    Returns:
        JSON response with error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "model_request_error",
            "detail": exc.message
        }
    )

def setup_exception_handlers(app: FastAPI) -> None:
    """Set up exception handlers for the application.
    
    Args:
        app: The FastAPI application
    """
    app.add_exception_handler(ModelRequestError, model_request_exception_handler)
```

When implementing new endpoints, use appropriate exception types and let the global exception handlers manage the response formatting.

## Testing API Endpoints

When testing API endpoints, follow these patterns:

```python
@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)

def test_health_check(client: TestClient):
    """Test the basic health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data

@pytest.mark.asyncio
async def test_health_details_async(async_client):
    """Test the detailed health check endpoint asynchronously."""
    response = await async_client.get("/health/details")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "warning", "error"]
    assert "components" in data
    assert "model_registry" in data["components"]
```

For testing authenticated endpoints, mock the authentication dependency:

```python
def test_admin_list_models(client: TestClient):
    """Test listing models via admin API."""
    # Override authentication dependency
    app.dependency_overrides[get_api_key] = lambda: "test_key"
    
    # Make request
    response = client.get("/admin/models", headers={"X-API-Key": "test_key"})
    
    # Clean up dependency override
    app.dependency_overrides = {}
    
    # Verify response
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```