"""Tests for model registry dependency injection."""

from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import FastAPI, Depends, APIRouter
from fastapi.testclient import TestClient
from fastapi.routing import APIRouter

from app.services.model_registry import (
    ModelRegistryService,
    get_model_registry_service,
    setup_model_registry
)
from app.config.models_config import ModelConfigManager
from app.config.settings import settings


def test_get_model_registry_service():
    """Test the get_model_registry_service dependency."""
    # Create a mock ModelConfigManager
    with patch("app.services.model_registry.ModelConfigManager", autospec=True) as mock_manager_cls:
        # Mock the instance returned by the constructor
        mock_manager = MagicMock(spec=ModelConfigManager)
        mock_manager_cls.return_value = mock_manager
        
        # Call the dependency
        service = get_model_registry_service()
        
        # Verify ModelConfigManager was constructed with the right parameters
        mock_manager_cls.assert_called_once_with(
            config_dir=settings.CONFIG_DIR,
            registry_file=settings.MODELS_REGISTRY_FILE
        )
        
        # Verify a ModelRegistryService was returned
        assert isinstance(service, ModelRegistryService)
        assert service.config_manager is mock_manager


def test_setup_model_registry():
    """Test setting up the model registry with FastAPI app events."""
    # Create a FastAPI app
    app = FastAPI()
    
    # Mock ModelRegistryService and ModelConfigManager
    with patch("app.services.model_registry.ModelRegistryService", autospec=True) as mock_service_cls, \
         patch("app.services.model_registry.ModelConfigManager", autospec=True) as mock_manager_cls:
        
        # Mock the instances
        mock_manager = MagicMock(spec=ModelConfigManager)
        mock_manager_cls.return_value = mock_manager
        
        mock_service = MagicMock(spec=ModelRegistryService)
        mock_service_cls.return_value = mock_service
        
        # Mock the async methods
        mock_service.startup = AsyncMock()
        mock_service.shutdown = AsyncMock()
        
        # Call setup_model_registry
        setup_model_registry(app)
        
        # Verify ModelConfigManager was constructed
        mock_manager_cls.assert_called_once_with(settings.CONFIG_DIR, settings.MODELS_REGISTRY_FILE)
        
        # Verify ModelRegistryService was constructed
        mock_service_cls.assert_called_once_with(mock_manager)
        
        # Verify event handlers were registered
        assert len(app.router.on_startup) == 1
        assert len(app.router.on_shutdown) == 1


def test_model_registry_dependency_in_router():
    """Test using the model registry dependency in a router."""
    # Create a test API router
    router = APIRouter()
    
    @router.get("/test")
    def test_endpoint(registry: ModelRegistryService = Depends(get_model_registry_service)):
        return {"model_count": len(registry.list_models())}
    
    # Create a FastAPI app with the router
    app = FastAPI()
    app.include_router(router)
    
    # Mock the model registry service
    with patch("app.services.model_registry.get_model_registry_service") as mock_get_service:
        # Create a mock service
        mock_service = MagicMock(spec=ModelRegistryService)
        mock_service.list_models.return_value = [MagicMock(), MagicMock()]
        mock_get_service.return_value = mock_service
        
        # Create a test client
        client = TestClient(app)
        
        # Call the test endpoint
        response = client.get("/test")
        
        # Verify the response
        assert response.status_code == 200
        assert response.json() == {"model_count": 2}
        
        # Verify the mock was used
        mock_get_service.assert_called_once()
        mock_service.list_models.assert_called_once()


@pytest.mark.asyncio
async def test_registry_service_events():
    """Test registry service startup/shutdown events execution."""
    # Create a test app
    app = FastAPI()
    
    # Set up registry with real service but mocked methods
    with patch.object(ModelRegistryService, "startup", new_callable=AsyncMock) as mock_startup, \
         patch.object(ModelRegistryService, "shutdown", new_callable=AsyncMock) as mock_shutdown:
        
        # Set up the registry
        setup_model_registry(app)
        
        # Manually trigger startup event
        for startup_handler in app.router.on_startup:
            await startup_handler()
        
        # Verify startup was called
        mock_startup.assert_called_once()
        
        # Manually trigger shutdown event
        for shutdown_handler in app.router.on_shutdown:
            await shutdown_handler()
        
        # Verify shutdown was called
        mock_shutdown.assert_called_once()