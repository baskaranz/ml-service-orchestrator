# ML Orchestrator - Service Layer Instructions

This file provides detailed guidance for implementing service-related code in the ML Orchestrator service.

## Overview

The service layer contains business logic components that:
1. Interface between the API layer and core domain logic
2. Provide specific functionality like model registry and request proxying
3. Encapsulate complex operations with clean interfaces
4. Follow dependency injection patterns for testability

## Key Files

- `app/services/model_registry.py`: Model registration and lookups
- `app/services/proxy.py`: Request proxying to model endpoints

## Model Registry Service

The `ModelRegistryService` manages model configurations and provides lookups:

```python
from typing import Dict, List, Optional
from fastapi import FastAPI, Depends

from app.config.models_config import ModelConfigManager
from app.core.models import ModelConfig
from app.utils.logging import get_logger

logger = get_logger(__name__)

class ModelRegistryService:
    """Service for managing model configurations."""
    
    def __init__(self, config_manager: ModelConfigManager):
        """Initialize the model registry service.
        
        Args:
            config_manager: The model configuration manager
        """
        self.config_manager = config_manager
        self._models: Dict[str, ModelConfig] = {}
    
    async def load_models(self) -> None:
        """Load model configurations."""
        try:
            self._models = await self.config_manager.load_configs()
            logger.info(f"Loaded {len(self._models)} model configurations")
        except Exception as e:
            logger.error(f"Failed to load model configurations: {str(e)}")
            raise
    
    def get_model_config(self, model_id: str) -> ModelConfig:
        """Get a model configuration.
        
        Args:
            model_id: The model ID
            
        Returns:
            The model configuration
            
        Raises:
            KeyError: If the model doesn't exist
        """
        if model_id not in self._models:
            logger.error(f"Model {model_id} not found")
            raise KeyError(f"Model {model_id} not found")
        
        return self._models[model_id]
    
    def list_models(self) -> List[ModelConfig]:
        """List all model configurations.
        
        Returns:
            List of model configurations
        """
        return list(self._models.values())
    
    async def add_model(self, model: ModelConfig) -> ModelConfig:
        """Add a new model configuration.
        
        Args:
            model: The model configuration
            
        Returns:
            The added model configuration
            
        Raises:
            ValueError: If the model already exists
        """
        if model.id in self._models:
            logger.error(f"Model {model.id} already exists")
            raise ValueError(f"Model {model.id} already exists")
        
        # Add to registry
        self._models[model.id] = model
        
        # Save to disk
        await self.config_manager.save_model_config(model)
        
        logger.info(f"Added model {model.id}")
        return model
    
    async def update_model(self, model_id: str, model: ModelConfig) -> ModelConfig:
        """Update a model configuration.
        
        Args:
            model_id: The model ID
            model: The updated model configuration
            
        Returns:
            The updated model configuration
            
        Raises:
            KeyError: If the model doesn't exist
        """
        if model_id not in self._models:
            logger.error(f"Model {model_id} not found")
            raise KeyError(f"Model {model_id} not found")
        
        # ID in path takes precedence
        model.id = model_id
        
        # Update registry
        self._models[model_id] = model
        
        # Save to disk
        await self.config_manager.save_model_config(model)
        
        logger.info(f"Updated model {model_id}")
        return model
    
    async def delete_model(self, model_id: str) -> None:
        """Delete a model configuration.
        
        Args:
            model_id: The model ID
            
        Raises:
            KeyError: If the model doesn't exist
        """
        if model_id not in self._models:
            logger.error(f"Model {model_id} not found")
            raise KeyError(f"Model {model_id} not found")
        
        # Remove from registry
        del self._models[model_id]
        
        # Remove from disk
        await self.config_manager.delete_model_config(model_id)
        
        logger.info(f"Deleted model {model_id}")
    
    def get_model_metadata(self, model_id: str) -> Dict:
        """Get metadata for a model.
        
        Args:
            model_id: The model ID
            
        Returns:
            Model metadata
            
        Raises:
            KeyError: If the model doesn't exist
        """
        model = self.get_model_config(model_id)
        return {
            "id": model.id,
            "name": model.name,
            "version": model.version,
            "description": model.description,
            "active": model.active
        }

# Setup FastAPI event handlers
async def setup_model_registry(app: FastAPI) -> None:
    """Set up the model registry service.
    
    Args:
        app: The FastAPI application
    """
    # Create the model registry service
    config_manager = ModelConfigManager(
        config_dir=settings.CONFIG_DIR,
        registry_file=settings.MODELS_REGISTRY_FILE
    )
    service = ModelRegistryService(config_manager)
    
    # Load models
    await service.load_models()
    
    # Start monitoring for changes
    asyncio.create_task(config_manager.monitor_configs())
    
    # Store service in app state
    app.state.model_registry = service

# Dependency provider
def get_model_registry_service(
    request: Request = None,
    app: FastAPI = None
) -> ModelRegistryService:
    """Dependency provider for the model registry service.
    
    Args:
        request: Optional FastAPI request
        app: Optional FastAPI app
        
    Returns:
        The model registry service
    """
    if request:
        return request.app.state.model_registry
    elif app:
        return app.state.model_registry
    else:
        # For testing or direct usage
        config_manager = ModelConfigManager(
            config_dir=settings.CONFIG_DIR,
            registry_file=settings.MODELS_REGISTRY_FILE
        )
        return ModelRegistryService(config_manager)

# FastAPI lifecycle events
@app.on_event("startup")
async def startup_model_registry():
    """Initialize the model registry on startup."""
    await setup_model_registry(app)

@app.on_event("shutdown")
async def shutdown_model_registry():
    """Clean up the model registry on shutdown."""
    # Any cleanup needed
    pass
```

When extending or modifying the `ModelRegistryService`, follow these patterns:
1. Maintain the dependency injection pattern
2. Use proper logging
3. Add appropriate error handling
4. Update configuration on disk when making changes
5. Support FastAPI lifecycle events

## Proxy Service

The `ProxyService` handles proxying requests to model endpoints:

```python
from fastapi import Depends, Request
from typing import Dict, Any

from app.core.exceptions import ModelRequestError, CircuitBreakerError
from app.core.orchestrator import Orchestrator
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

class ProxyService:
    """Service for proxying requests to model endpoints."""
    
    def __init__(
        self,
        model_registry: ModelRegistryService,
        orchestrator: Orchestrator
    ):
        """Initialize the proxy service.
        
        Args:
            model_registry: The model registry service
            orchestrator: The orchestrator
        """
        self.model_registry = model_registry
        self.orchestrator = orchestrator
    
    async def proxy_to_model(self, model_id: str, request: Request) -> Dict[str, Any]:
        """Proxy a request to a model endpoint.
        
        Args:
            model_id: The model ID to proxy to
            request: The FastAPI request object
            
        Returns:
            The model response
            
        Raises:
            ModelRequestError: If the request fails
        """
        try:
            # Get model configuration
            model_config = self.model_registry.get_model_config(model_id)
            
            # Extract request data
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                request_data = await request.json()
            else:
                request_data = await request.body()
            
            # Extract headers
            headers = dict(request.headers)
            
            # Proxy request
            return await self.orchestrator.proxy_request(
                model_id=model_id,
                request_data=request_data,
                headers=headers
            )
        except CircuitBreakerError as e:
            logger.warning(f"Circuit breaker error: {str(e)}")
            raise ModelRequestError(
                message=f"Request failed: circuit breaker open for model {model_id}",
                status_code=503
            )
        except KeyError as e:
            logger.error(f"Model not found: {str(e)}")
            raise ModelRequestError(
                message=f"Model {model_id} not found",
                status_code=404
            )
        except Exception as e:
            logger.error(f"Proxy error: {str(e)}")
            raise ModelRequestError(
                message=f"Request to model {model_id} failed: {str(e)}",
                status_code=500
            )

# Dependency provider
def get_proxy_service(
    model_registry: ModelRegistryService = Depends(get_model_registry_service),
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> ProxyService:
    """Dependency provider for the proxy service.
    
    Args:
        model_registry: The model registry service
        orchestrator: The orchestrator
        
    Returns:
        The proxy service
    """
    return ProxyService(model_registry, orchestrator)
```

When enhancing the `ProxyService`, follow these patterns:
1. Maintain clean separation of concerns
2. Handle different request content types
3. Properly propagate and transform errors
4. Log relevant information at appropriate levels

## Adding New Services

When adding new services to the ML Orchestrator, follow these patterns:

```python
from fastapi import Depends
from typing import Dict, List, Optional, Any

from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

class NewService:
    """Service for handling some functionality."""
    
    def __init__(
        self,
        model_registry: ModelRegistryService
    ):
        """Initialize the service.
        
        Args:
            model_registry: The model registry service
        """
        self.model_registry = model_registry
    
    async def some_method(self, model_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform some operation.
        
        Args:
            model_id: The model ID
            params: Operation parameters
            
        Returns:
            Operation result
            
        Raises:
            ValueError: If the parameters are invalid
            KeyError: If the model doesn't exist
        """
        try:
            # Get model configuration
            model_config = self.model_registry.get_model_config(model_id)
            
            # Perform operation
            # ...
            
            # Return result
            return result
        except Exception as e:
            logger.error(f"Operation failed: {str(e)}")
            raise

# Dependency provider
def get_new_service(
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> NewService:
    """Dependency provider for the new service.
    
    Args:
        model_registry: The model registry service
        
    Returns:
        The new service
    """
    return NewService(model_registry)
```

Key patterns for new services:
1. Clear service responsibility
2. Dependency injection
3. Proper error handling
4. Thorough logging
5. Clean interface

## Testing Services

When testing services, follow these patterns:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.model_registry import ModelRegistryService
from app.services.proxy import ProxyService
from app.core.models import ModelConfig
from app.core.exceptions import CircuitBreakerError

@pytest.fixture
def mock_model_registry():
    """Create a mock model registry service."""
    registry = MagicMock(spec=ModelRegistryService)
    
    # Configure mock
    registry.get_model_config.return_value = ModelConfig(
        id="test_model",
        name="Test Model",
        endpoint_url="http://example.com/test"
    )
    
    registry.list_models.return_value = [
        ModelConfig(
            id="test_model",
            name="Test Model",
            endpoint_url="http://example.com/test"
        )
    ]
    
    return registry

@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    orchestrator = MagicMock()
    orchestrator.proxy_request = AsyncMock()
    orchestrator.proxy_request.return_value = {"result": "success"}
    return orchestrator

@pytest.fixture
def proxy_service(mock_model_registry, mock_orchestrator):
    """Create a proxy service with mocked dependencies."""
    return ProxyService(mock_model_registry, mock_orchestrator)

@pytest.mark.asyncio
async def test_proxy_to_model(proxy_service, mock_model_registry, mock_orchestrator):
    """Test proxying a request to a model."""
    # Create mock request
    mock_request = AsyncMock()
    mock_request.json = AsyncMock(return_value={"prompt": "test"})
    mock_request.headers = {"content-type": "application/json"}
    
    # Proxy request
    result = await proxy_service.proxy_to_model("test_model", mock_request)
    
    # Verify model was retrieved
    mock_model_registry.get_model_config.assert_called_once_with("test_model")
    
    # Verify request was proxied
    mock_orchestrator.proxy_request.assert_called_once()
    assert mock_orchestrator.proxy_request.call_args[1]["model_id"] == "test_model"
    assert mock_orchestrator.proxy_request.call_args[1]["request_data"] == {"prompt": "test"}
    
    # Verify result
    assert result == {"result": "success"}

@pytest.mark.asyncio
async def test_proxy_service_error_handling(proxy_service, mock_orchestrator):
    """Test error handling in proxy service."""
    # Create mock request
    mock_request = AsyncMock()
    mock_request.json = AsyncMock(return_value={"prompt": "test"})
    mock_request.headers = {"content-type": "application/json"}
    
    # Configure orchestrator to raise an exception
    mock_orchestrator.proxy_request.side_effect = CircuitBreakerError(
        model_id="test_model",
        message="Circuit breaker is open"
    )
    
    # Verify error handling
    with pytest.raises(ModelRequestError) as exc_info:
        await proxy_service.proxy_to_model("test_model", mock_request)
    
    # Check error details
    assert exc_info.value.status_code == 503
    assert "circuit breaker" in exc_info.value.message
```

Key testing patterns:
1. Mock dependencies with `MagicMock` and `AsyncMock`
2. Use pytest fixtures for test setup
3. Use `pytest.mark.asyncio` for async tests
4. Test both success and error paths
5. Verify interactions with dependencies