"""Tests for the model registry service."""

import os
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.core.models import ModelConfig
from app.services.model_registry import ModelRegistryService


@pytest.fixture
async def started_registry(mock_model_registry):
    """Create and start a model registry service."""
    await mock_model_registry.startup()
    yield mock_model_registry
    await mock_model_registry.shutdown()


@pytest.mark.asyncio
async def test_model_registry_startup(mock_config_manager):
    """Test starting the model registry service."""
    # Create a service with a mock config manager
    service = ModelRegistryService(mock_config_manager)
    
    # Mock the load_configs method to return some test data
    mock_config_manager.load_configs = AsyncMock(return_value=(MagicMock(), {"test1": MagicMock(), "test2": MagicMock()}))
    
    # Call startup
    await service.startup()
    
    # Verify load_configs was called
    mock_config_manager.load_configs.assert_called_once()
    
    # Verify watch task was created
    assert service._watch_task is not None
    
    # Clean up
    await service.shutdown()


@pytest.mark.asyncio
async def test_model_registry_shutdown(mock_config_manager):
    """Test shutting down the model registry service."""
    # Create a service with a mock config manager
    service = ModelRegistryService(mock_config_manager)
    
    # Mock the load_configs method
    mock_config_manager.load_configs = AsyncMock(return_value=(MagicMock(), {}))
    
    # Mock the start_watching method to do nothing
    mock_config_manager.start_watching = AsyncMock()
    
    # First start up
    await service.startup()
    
    # Verify watch task was created
    assert service._watch_task is not None
    
    # Now shut down
    await service.shutdown()
    
    # Verify watch task was cancelled
    assert service._watch_task.cancelled()


def test_get_model_config(mock_model_registry):
    """Test getting a model configuration by ID."""
    # Add test models to registry
    mock_model_registry.config_manager.models = {
        "test_model_1": ModelConfig(
            id="test_model_1",
            name="Test Model",
            endpoint_url="http://test.com",
            version="1.0.0"
        )
    }
    
    # Get a model that exists
    model = mock_model_registry.get_model_config("test_model_1")
    
    assert model is not None
    assert model.id == "test_model_1"
    assert model.name == "Test Model"
    assert model.endpoint_url == "http://test.com"


def test_get_model_config_not_found(mock_model_registry):
    """Test getting a model configuration that doesn't exist."""
    # Add test models to registry
    mock_model_registry.config_manager.models = {
        "test_model_1": ModelConfig(
            id="test_model_1",
            name="Test Model",
            endpoint_url="http://test.com",
            version="1.0.0"
        )
    }
    
    # Try to get a model that doesn't exist
    with pytest.raises(Exception):
        mock_model_registry.get_model_config("nonexistent_model")


def test_list_models(mock_model_registry):
    """Test listing all model configurations."""
    # Add test models to registry
    mock_model_registry.config_manager.models = {
        "test_model_1": ModelConfig(
            id="test_model_1",
            name="Test Model 1",
            endpoint_url="http://test1.com",
            version="1.0.0",
            active=True
        ),
        "test_model_2": ModelConfig(
            id="test_model_2",
            name="Test Model 2",
            endpoint_url="http://test2.com",
            version="1.0.0",
            active=False
        )
    }
    
    # List models
    models = mock_model_registry.list_models()
    
    assert len(models) == 2
    assert models[0].id == "test_model_1"
    assert models[0].name == "Test Model 1"
    assert models[0].active is True
    assert models[1].id == "test_model_2"
    assert models[1].name == "Test Model 2"
    assert models[1].active is False


def test_add_model(mock_model_registry, model_config_instance):
    """Test adding a new model."""
    # Create a new model
    new_model = model_config_instance.model_copy(update={"id": "new_model"})
    
    # Patch the config manager's add_model_config method
    with patch.object(mock_model_registry.config_manager, "add_model_config") as mock_add:
        # Add the model
        added_model = mock_model_registry.add_model(new_model)
        
        # Verify it was added to the config manager
        mock_add.assert_called_once_with(new_model)
        
        # Verify it was returned
        assert added_model == new_model


def test_update_model(mock_model_registry, model_config_instance):
    """Test updating an existing model."""
    # Create an updated model
    updated_model = model_config_instance.model_copy(update={
        "name": "Updated Model",
        "description": "This model was updated"
    })
    
    # Patch the config manager's update_model_config method
    with patch.object(mock_model_registry.config_manager, "update_model_config") as mock_update:
        # Update the model
        updated = mock_model_registry.update_model("test_model_1", updated_model)
        
        # Verify it was updated in the config manager
        mock_update.assert_called_once_with("test_model_1", updated_model)
        
        # Verify it was returned
        assert updated == updated_model


def test_delete_model(mock_model_registry):
    """Test deleting a model."""
    # Patch the config manager's delete_model_config method
    with patch.object(mock_model_registry.config_manager, "delete_model_config") as mock_delete:
        # Delete a model
        mock_model_registry.delete_model("test_model_1")
        
        # Verify it was deleted from the config manager
        mock_delete.assert_called_once_with("test_model_1")


@pytest.mark.asyncio
async def test_reload_configs(mock_model_registry):
    """Test reloading configurations."""
    # Mock the load_configs method
    mock_model_registry.config_manager.load_configs = AsyncMock(return_value=(
        MagicMock(),
        {
            "new_model_1": ModelConfig(id="new_model_1", name="New Model 1", endpoint_url="http://new1.com"),
            "new_model_2": ModelConfig(id="new_model_2", name="New Model 2", endpoint_url="http://new2.com")
        }
    ))
    
    # Set current models
    mock_model_registry.config_manager.models = {
        "old_model_1": ModelConfig(id="old_model_1", name="Old Model 1", endpoint_url="http://old1.com"),
        "old_model_2": ModelConfig(id="old_model_2", name="Old Model 2", endpoint_url="http://old2.com")
    }
    
    # Reload configs
    result = await mock_model_registry.reload_configs()
    
    # Verify load_configs was called
    mock_model_registry.config_manager.load_configs.assert_called_once()
    
    # Verify models were updated
    assert list(result.keys()) == ["new_model_1", "new_model_2"]