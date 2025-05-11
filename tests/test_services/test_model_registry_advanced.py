"""Advanced tests for the model registry service."""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call

import pytest
from fastapi import FastAPI

from app.core.models import ModelConfig, ModelSummary
from app.services.model_registry import ModelRegistryService, setup_model_registry


@pytest.mark.asyncio
async def test_startup_error_handling(mock_config_manager):
    """Test error handling during startup."""
    # Create a service with a mock config manager
    service = ModelRegistryService(mock_config_manager)
    
    # Make load_configs raise an exception
    mock_config_manager.load_configs = AsyncMock(side_effect=Exception("Config loading error"))
    
    # Call startup and expect the exception to propagate
    with pytest.raises(Exception) as exc_info:
        await service.startup()
    
    assert "Config loading error" in str(exc_info.value)
    
    # Verify the watch task wasn't created
    assert service._watch_task is None


@pytest.mark.asyncio
async def test_shutdown_with_no_watch_task():
    """Test shutdown when no watch task exists."""
    # Create a service with a mock config manager
    mock_config_manager = MagicMock()
    service = ModelRegistryService(mock_config_manager)
    
    # Ensure _watch_task is None
    service._watch_task = None
    
    # Shutdown should complete without errors
    await service.shutdown()


@pytest.mark.asyncio
async def test_shutdown_with_cancelled_task():
    """Test shutdown when the watch task is already cancelled."""
    # Create a service with a mock config manager
    mock_config_manager = MagicMock()
    service = ModelRegistryService(mock_config_manager)
    
    # Create a task that's already cancelled
    task = asyncio.create_task(asyncio.sleep(0.1))
    task.cancel()
    
    # Try to await it to consume the CancelledError
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Set it as the watch task
    service._watch_task = task
    
    # Shutdown should complete without errors
    await service.shutdown()


@pytest.mark.asyncio
async def test_shutdown_with_task_exception():
    """Test shutdown when the watch task raises an exception."""
    # Create a service with a mock config manager
    mock_config_manager = MagicMock()
    service = ModelRegistryService(mock_config_manager)
    
    # Create a real task that will raise an exception
    async def error_task():
        await asyncio.sleep(0.01)
        raise RuntimeError("Task error")
    
    task = asyncio.create_task(error_task())
    
    # Set it as the watch task
    service._watch_task = task
    
    # Shutdown should handle the exception gracefully
    await service.shutdown()
    
    # The test passes if shutdown doesn't propagate the exception


def test_list_models_empty(mock_model_registry):
    """Test listing models when no models exist."""
    # Ensure models dict is empty
    mock_model_registry.config_manager.models = {}
    
    # List models
    models = mock_model_registry.list_models()
    
    # Verify an empty list is returned
    assert isinstance(models, list)
    assert len(models) == 0


def test_list_models_with_transformations(mock_model_registry):
    """Test listing models with complex attributes like transformations."""
    # Add a test model with transformations
    mock_model_registry.config_manager.models = {
        "test_model": ModelConfig(
            id="test_model",
            name="Test Model",
            endpoint_url="http://test.com",
            version="1.0.0",
            active=True,
            transformations={
                "input": {"type": "normalize", "params": {"mean": 0, "std": 1}},
                "output": {"type": "softmax", "params": {}}
            }
        )
    }
    
    # List models
    models = mock_model_registry.list_models()
    
    # Verify the model was properly converted to a ModelSummary
    assert len(models) == 1
    assert isinstance(models[0], ModelSummary)
    assert models[0].id == "test_model"
    assert models[0].name == "Test Model"
    assert models[0].active is True
    # ModelSummary doesn't include transformations, so we're just checking the basic fields


@pytest.mark.asyncio
async def test_reload_configs_empty(mock_model_registry):
    """Test reloading configs when no models are loaded."""
    # Mock the load_configs method to return empty dicts
    mock_model_registry.config_manager.load_configs = AsyncMock(return_value=(
        {},  # Registry dict
        {}   # Models dict
    ))
    
    # Reload configs
    result = await mock_model_registry.reload_configs()
    
    # Verify load_configs was called
    mock_model_registry.config_manager.load_configs.assert_called_once()
    
    # Verify an empty dict was returned
    assert isinstance(result, dict)
    assert len(result) == 0


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
        
        # Verify our event handlers were added without removing existing ones
        assert len(app.router.on_startup) == 2
        assert len(app.router.on_shutdown) == 2
        
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