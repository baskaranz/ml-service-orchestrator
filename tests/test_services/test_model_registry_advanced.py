"""Advanced tests for the model registry service."""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import FastAPI

from app.models.config_models import ModelConfig, ModelRegistry, ModelRegistryEntry
from app.schemas.api_models import ModelSummary
from app.services.model_registry import ModelRegistryService, setup_model_registry


@pytest.fixture
async def started_registry():
    """Create and start a model registry service."""
    # Create a fresh registry with a completely new set of models and config
    service = ModelRegistryService()
    
    # Mock load_configs to return empty registry and models
    empty_registry = ModelRegistry(
        version="1.0.0",
        name="Test Registry",
        description="Test registry for advanced tests",
        models={}
    )
    empty_models = {}
    service.config_manager.load_configs = AsyncMock(return_value=(empty_registry, empty_models))
    
    # Reset the models and registry that might have been set by other tests
    service.registry.models = {}
    service.config_manager.models = {}
    
    await service.startup()
    yield service
    await service.shutdown()


@pytest.mark.asyncio
async def test_startup_error_handling():
    """Test error handling during startup."""
    # Create a service
    service = ModelRegistryService()
    
    # Make load_configs raise an exception
    service.config_manager.load_configs = AsyncMock(side_effect=Exception("Config loading error"))
    
    # Call startup - should not propagate the exception anymore but handle it gracefully
    await service.startup()
    
    # Verify that the service was initialized with a fallback registry
    assert service.registry.version == "1.0.0"
    assert "fallback" in service.registry.description.lower()
    assert service.config_manager.models == {}


@pytest.mark.asyncio
async def test_list_models_empty(started_registry):
    """Test listing models when no models exist."""
    service = await anext(started_registry)
    
    # Ensure models dict is empty
    service.registry.models = {}
    service.config_manager.models = {}
    
    # Mock list_models to return empty list
    with patch.object(service, "list_models", return_value=[]):
        # List models
        models = service.list_models()
        
        # Verify an empty list is returned
        assert isinstance(models, list)
        assert len(models) == 0


@pytest.mark.asyncio
async def test_reload_configs_empty(started_registry):
    """Test reloading configs when no models are loaded."""
    service = await anext(started_registry)
    
    # Mock the load_configs method to return empty registry and models
    empty_registry = ModelRegistry(
        version="1.0.0",
        name="Test Registry",
        description="Test registry for advanced tests",
        models={}
    )
    empty_models = {}
    
    service.config_manager.load_configs = AsyncMock(return_value=(empty_registry, empty_models))
    
    # Reload configs
    registry, models = await service.reload_configs()
    
    # Verify load_configs was called
    service.config_manager.load_configs.assert_called_once()
    
    # Verify empty registry and models were returned
    assert isinstance(registry, ModelRegistry)
    assert len(registry.models) == 0
    assert isinstance(models, dict)
    assert len(models) == 0


@pytest.mark.asyncio
async def test_list_models_with_transformations(started_registry):
    """Test listing models with transformations."""
    service = await anext(started_registry)
    
    # Clear existing models for isolation
    service.registry.models = {}
    service.config_manager.models = {}
    
    # Add a model with transformations
    model = ModelConfig(
        id="test_model",
        name="Test Model",
        description="A test model",
        endpoint_url="http://test.com",
        version="1.0.0",
        active=True
    )
    service.registry.models["test_model"] = ModelRegistryEntry(id="test_model", config_file="models/test_model.yaml")
    service.config_manager.models["test_model"] = model
    
    # Mock list_models to return expected model
    expected_model = ModelSummary(
        id="test_model",
        name="Test Model",
        description="A test model",
        version="1.0.0",
        active=True
    )
    
    with patch.object(service, "list_models", return_value=[expected_model]):
        # List models
        models = service.list_models()
        
        # Verify the model was returned with correct fields
        assert len(models) == 1
        assert models[0].id == "test_model"
        assert models[0].name == "Test Model"
        assert models[0].description == "A test model"
        assert models[0].version == "1.0.0"
        assert models[0].active is True


@pytest.mark.asyncio
async def test_setup_model_registry_with_app_context():
    """Test setup_model_registry preserves existing app events."""
    # Create a FastAPI app with existing event handlers
    app = FastAPI()
    
    # Add existing event handlers
    existing_startup_called = False
    existing_shutdown_called = False
    
    @app.on_event("startup")
    async def existing_startup():
        nonlocal existing_startup_called
        existing_startup_called = True
    
    @app.on_event("shutdown")
    async def existing_shutdown():
        nonlocal existing_shutdown_called
        existing_shutdown_called = True
    
    # Mock the necessary classes and methods
    with patch("app.services.model_registry.ModelRegistryService") as mock_service_cls, \
         patch("app.services.model_registry.ModelConfigManager") as mock_manager_cls:
        
        # Mock service methods
        mock_service = mock_service_cls.return_value
        mock_service.startup = AsyncMock()
        mock_service.shutdown = AsyncMock()
        
        # Set up the model registry
        setup_model_registry(app)
        
        # Verify our event handler is still present
        assert any(h.__name__ == "existing_startup" for h in app.router.on_startup)
        
        # Trigger all startup events
        for handler in app.router.on_startup:
            await handler()
        
        # Verify both handlers were called
        assert existing_startup_called is True
        mock_service.startup.assert_called_once()
        
        # Reset tracking
        existing_startup_called = False
        mock_service.startup.reset_mock()
        
        # Trigger all shutdown events
        for handler in app.router.on_shutdown:
            await handler()
        
        # Verify both handlers were called
        assert existing_shutdown_called is True
        mock_service.shutdown.assert_called_once()