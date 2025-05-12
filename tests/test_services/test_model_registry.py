"""Tests for the model registry service."""

import os
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.models.config_models import ModelConfig, CircuitBreakerConfig, ModelRegistry
from app.schemas.api_models import ModelSummary
from app.services.model_registry import ModelRegistryService
from fastapi import HTTPException
from app.core.exceptions import ModelNotFoundError, ModelAlreadyExistsError


@pytest.fixture
async def started_registry():
    """Create and start a model registry service."""
    # Create a fresh registry with a completely new set of models and config
    service = ModelRegistryService()
    
    # Mock the reload_configs method to avoid file system operations
    empty_registry = ModelRegistry(
        version="1.0.0",
        name="Test Registry",
        description="Test registry for unit tests",
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
async def test_model_registry_startup():
    """Test starting the model registry service."""
    # Create a service
    service = ModelRegistryService()
    
    # Mock the config manager's load_configs method
    test_models = {
        "test1": ModelConfig(
            id="test1",
            name="Test Model 1",
            description="Test model 1",
            endpoint_url="http://test1.com",
            version="1.0.0",
            active=True,
            timeout=30.0,
            max_retries=3,
            type="classification",
            metadata={"framework": "pytorch"}
        ),
        "test2": ModelConfig(
            id="test2",
            name="Test Model 2",
            description="Test model 2",
            endpoint_url="http://test2.com",
            version="1.0.0",
            active=True,
            timeout=30.0,
            max_retries=3,
            type="regression",
            metadata={"framework": "tensorflow"}
        )
    }
    
    # Create registry from models
    registry_models = {
        "test1": {
            "id": "test1",
            "name": "Test Model 1",
            "description": "Test model 1",
            "version": "1.0.0",
            "endpoint": "http://test1.com",
            "config_file": "models/test1.yaml",
            "active": True,
            "type": "classification",
            "metadata": {"framework": "pytorch"}
        },
        "test2": {
            "id": "test2",
            "name": "Test Model 2",
            "description": "Test model 2",
            "version": "1.0.0",
            "endpoint": "http://test2.com",
            "config_file": "models/test2.yaml",
            "active": True,
            "type": "regression",
            "metadata": {"framework": "tensorflow"}
        }
    }
    
    test_registry = ModelRegistry(
        version="1.0.0",
        name="Test Registry",
        description="Test registry for unit tests",
        models=registry_models
    )
    
    service.config_manager.load_configs = AsyncMock(return_value=(test_registry, test_models))
    
    # Call startup
    await service.startup()
    
    # Verify load_configs was called
    service.config_manager.load_configs.assert_called_once()
    
    # Verify models were loaded
    assert len(service.registry.models) == 2
    assert "test1" in service.registry.models
    assert "test2" in service.registry.models
    
    # Verify model details
    assert service.registry.models["test1"]["type"] == "classification"
    assert service.registry.models["test1"]["metadata"]["framework"] == "pytorch"
    assert service.registry.models["test2"]["type"] == "regression"
    assert service.registry.models["test2"]["metadata"]["framework"] == "tensorflow"


@pytest.mark.asyncio
async def test_get_model_config(started_registry):
    """Test getting a model configuration."""
    service = await anext(started_registry)
    
    # Add test model to registry and config manager
    model_config = ModelConfig(
        id="test_model_1",
        name="Test Model 1",
        description="Test model 1",
        endpoint_url="http://test1.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3,
        type="classification",
        metadata={"framework": "pytorch"}
    )
    
    registry_model = {
        "id": "test_model_1",
        "name": "Test Model 1",
        "description": "Test model 1",
        "version": "1.0.0",
        "endpoint": "http://test1.com",
        "config_file": "models/test_model_1.yaml",
        "active": True,
        "type": "classification",
        "metadata": {"framework": "pytorch"}
    }
    
    service.registry.models = {"test_model_1": registry_model}
    service.config_manager.models = {"test_model_1": model_config}
    
    # Get a model that exists
    model = service.get_model_config("test_model_1")
    assert model is not None
    assert model.name == "Test Model 1"
    assert model.endpoint_url == "http://test1.com"
    assert model.type == "classification"
    assert model.metadata["framework"] == "pytorch"


@pytest.mark.asyncio
async def test_list_models(started_registry):
    """Test listing all models."""
    # Reset singleton to avoid state leakage
    from app.services.model_registry import ModelRegistryService
    ModelRegistryService._instance = None
    service = await anext(started_registry)
    
    # Clear existing models
    service.registry.models = {}
    service.config_manager.models = {}
    
    # Add test models
    model_config_1 = ModelConfig(
        id="test_model_1",
        name="Test Model 1",
        description="Test model 1",
        endpoint_url="http://test1.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3,
        type="classification",
        metadata={"framework": "pytorch"}
    )
    
    model_config_2 = ModelConfig(
        id="test_model_2",
        name="Test Model 2",
        description="Test model 2",
        endpoint_url="http://test2.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3,
        type="regression",
        metadata={"framework": "tensorflow"}
    )
    
    # Only set config_manager.models, not registry.models
    service.config_manager.models = {
        "test_model_1": model_config_1,
        "test_model_2": model_config_2
    }
    
    # List models
    models = service.list_models()
    
    # Debug print for types
    print('DEBUG: Model types in summaries:', [getattr(m, 'type', None) for m in models])
    
    # Verify results
    assert len(models) == 2
    assert any(m.id == "test_model_1" and m.type == "classification" for m in models)
    assert any(m.id == "test_model_2" and m.type == "regression" for m in models)


@pytest.mark.asyncio
async def test_update_model(started_registry):
    """Test updating a model configuration."""
    service = await anext(started_registry)
    
    # Clear existing models
    service.registry.models = {}
    service.config_manager.models = {}
    
    # Mock the config_manager methods
    service.config_manager.add_model_config = MagicMock()
    service.config_manager.update_model_config = MagicMock()
    
    # Add a model
    model = ModelConfig(
        id="test_model",
        name="Test Model",
        description="A test model",
        endpoint_url="http://test.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3,
        type="classification",
        metadata={"framework": "pytorch"}
    )
    
    await service.add_model("test_model", model)
    
    # Update the model
    updated_model = model.model_copy(update={
        "name": "Updated Model",
        "type": "regression",
        "metadata": {"framework": "tensorflow"}
    })
    
    result = await service.update_model("test_model", updated_model)
    
    # Verify result
    assert result.name == "Updated Model"
    assert result.type == "regression"
    assert result.metadata["framework"] == "tensorflow"


@pytest.mark.asyncio
async def test_delete_model(started_registry):
    """Test deleting a model configuration."""
    service = await anext(started_registry)
    
    # Clear existing models
    service.registry.models = {}
    service.config_manager.models = {}
    
    # Mock the config_manager methods
    service.config_manager.add_model_config = MagicMock()
    service.config_manager.delete_model_config = MagicMock()
    
    # Add a model
    model = ModelConfig(
        id="test_model",
        name="Test Model",
        description="A test model",
        endpoint_url="http://test.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3,
        type="classification",
        metadata={"framework": "pytorch"}
    )
    
    await service.add_model("test_model", model)
    
    # Delete the model
    await service.delete_model("test_model")
    
    # Verify it was removed
    with pytest.raises(ModelNotFoundError):
        service.get_model("test_model")


def test_get_model_config_not_found(started_registry):
    """Test getting a model configuration that doesn't exist."""
    # Try to get a model that doesn't exist
    with pytest.raises(Exception):
        started_registry.get_model_config("nonexistent_model")


@pytest.mark.asyncio
async def test_add_model(started_registry):
    service = await anext(started_registry)
    # Create a new model
    new_model = ModelConfig(
        id="new_model",
        name="New Model",
        description="A new model",
        endpoint_url="http://new.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3
    )
    # Add the model
    added_model = await service.add_model("new_model", new_model)
    # Verify it was added
    assert "new_model" in service.registry.models
    # Compare dicts, not ModelConfig instance
    assert service.registry.models["new_model"] == {
        "id": new_model.id,
        "name": new_model.name,
        "description": new_model.description,
        "version": new_model.version,
        "endpoint": new_model.endpoint_url,
        "config_file": f"models/{new_model.id}.yaml",
        "active": new_model.active,
        "type": new_model.type,
        "metadata": new_model.metadata
    }
    assert added_model == new_model


@pytest.mark.asyncio
async def test_add_model_duplicate(started_registry):
    service = await anext(started_registry)
    # Clear existing models
    service.registry.models = {}
    service.config_manager.models = {}
    
    # Add a model
    model = ModelConfig(
        id="test_model",
        name="Test Model",
        description="A test model",
        endpoint_url="http://test.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3
    )
    await service.add_model("test_model", model)
    
    # Try to add it again, expect ModelAlreadyExistsError
    with pytest.raises(ModelAlreadyExistsError):
        await service.add_model("test_model", model)


def test_update_model_not_found(started_registry):
    """Test updating a model that doesn't exist."""
    model = ModelConfig(
        id="test_model",
        name="Test Model",
        description="A test model",
        endpoint_url="http://test.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3
    )
    
    with pytest.raises(Exception):
        started_registry.update_model("nonexistent_model", model)


def test_delete_model_not_found(started_registry):
    """Test deleting a model that doesn't exist."""
    with pytest.raises(Exception):
        started_registry.delete_model("nonexistent_model")


@pytest.mark.asyncio
async def test_delete_model_registry_entry_not_found(mock_config_manager):
    """Test deleting a model when the registry entry is not found."""
    # First load configurations
    test_models = {
        "test1": ModelConfig(
            id="test1",
            name="Test Model 1",
            description="Test model 1",
            endpoint_url="http://test1.com",
            version="1.0.0",
            active=True,
            timeout=30.0,
            max_retries=3
        )
    }
    test_registry = ModelRegistry(
        version="1.0.0",
        name="Test Registry",
        description="Test registry for unit tests",
        models={}
    )
    mock_config_manager.load_configs = AsyncMock(return_value=(test_registry, test_models))
    await mock_config_manager.load_configs()
    
    # Try to delete a model that doesn't exist in the registry
    with pytest.raises(ModelNotFoundError):
        mock_config_manager.delete_model_config("nonexistent_model")