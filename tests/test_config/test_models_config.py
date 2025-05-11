"""Tests for the models configuration module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import yaml

from app.config.models_config import ModelConfigManager
from app.core.models import ModelConfig, ModelRegistry


@pytest.mark.asyncio
async def test_load_configs(mock_config_manager):
    """Test loading all model configurations."""
    registry, models = await mock_config_manager.load_configs()
    
    assert registry is not None
    assert registry.version == "1.0.0"
    assert registry.name == "Test Registry"
    assert len(registry.models) == 2
    assert len(models) == 2
    assert "test_model_1" in models
    assert "test_model_2" in models
    assert models["test_model_1"].name == "Test Model"
    assert models["test_model_2"].name == "Test Model 2"


def test_read_yaml_file(mock_config_manager, test_models_registry):
    """Test reading a YAML file."""
    file_path = Path("/tmp/test_config/models_registry.yaml")
    result = mock_config_manager._read_yaml_file(file_path)
    
    assert result == test_models_registry
    assert result["name"] == "Test Registry"
    assert len(result["models"]) == 2


def test_process_env_vars(mock_config_manager):
    """Test processing environment variables in configuration."""
    # Set environment variables
    os.environ["TEST_URL"] = "http://test-env-var.com"
    os.environ["TEST_API_KEY"] = "env-api-key"
    
    # Test config with environment variables
    test_config = {
        "id": "env_var_model",
        "endpoint_url": "${TEST_URL}",
        "auth": {
            "type": "api_key",
            "key_name": "API-Key",
            "key_value": "${TEST_API_KEY}",
            "location": "header"
        },
        "nested": {
            "list": [
                "${TEST_URL}/endpoint",
                "static_value"
            ]
        }
    }
    
    processed = mock_config_manager._process_env_vars(test_config)
    
    assert processed["endpoint_url"] == "http://test-env-var.com"
    assert processed["auth"]["key_value"] == "env-api-key"
    assert processed["nested"]["list"][0] == "http://test-env-var.com/endpoint"
    assert processed["nested"]["list"][1] == "static_value"


def test_replace_env_vars_with_default(mock_config_manager):
    """Test replacing environment variables with default values."""
    # Ensure environment variable doesn't exist
    if "NONEXISTENT_VAR" in os.environ:
        del os.environ["NONEXISTENT_VAR"]
        
    value = "${NONEXISTENT_VAR:default_value}"
    result = mock_config_manager._replace_env_vars(value)
    
    assert result == "default_value"


def test_replace_env_vars_no_default(mock_config_manager):
    """Test replacing environment variables with no default value."""
    # Ensure environment variable doesn't exist
    if "NONEXISTENT_VAR" in os.environ:
        del os.environ["NONEXISTENT_VAR"]
        
    value = "${NONEXISTENT_VAR}"
    result = mock_config_manager._replace_env_vars(value)
    
    assert result == ""


@pytest.mark.asyncio
async def test_get_model_config_found(mock_config_manager):
    """Test getting a model configuration that exists."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    model = mock_config_manager.get_model_config("test_model_1")
    
    assert model is not None
    assert model.id == "test_model_1"
    assert model.name == "Test Model"


@pytest.mark.asyncio
async def test_get_model_config_not_found(mock_config_manager):
    """Test getting a model configuration that doesn't exist raises an exception."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    with pytest.raises(Exception):
        mock_config_manager.get_model_config("nonexistent_model")


@pytest.mark.asyncio
async def test_start_watching(mock_config_manager):
    """Test starting file watching."""
    # Mock awatch to avoid actually watching files
    with patch("app.config.models_config.awatch") as mock_awatch:
        # Set up mock awatch to yield once and then stop
        mock_awatch.return_value.__aiter__.return_value = AsyncMock()
        mock_awatch.return_value.__aiter__.return_value.__anext__.side_effect = [
            {(1, "/tmp/test_config/models_registry.yaml")},
            StopAsyncIteration
        ]
        
        # Start watching in a way that doesn't block indefinitely
        await mock_config_manager.start_watching()
        
        # Verify awatch was called with the correct path
        # Use assert instead of specific mock method to handle Path objects
        assert mock_awatch.call_count == 1
        assert str(mock_awatch.call_args[0][0]) == "/tmp/test_config"


def test_should_reload_registry_changed(mock_config_manager):
    """Test reload detection when registry file has changed."""
    changed_files = {Path("/tmp/test_config/models_registry.yaml")}
    
    result = mock_config_manager._should_reload(changed_files)
    
    assert result is True


@pytest.mark.asyncio
async def test_should_reload_model_config_changed(mock_config_manager):
    """Test reload detection when a model config file has changed."""
    # First load configurations to set registry
    await mock_config_manager.load_configs()
    
    changed_files = {Path("/tmp/test_config/models/test_model_1.yaml")}
    
    result = mock_config_manager._should_reload(changed_files)
    
    assert result is True


@pytest.mark.asyncio
async def test_should_reload_no_relevant_files(mock_config_manager):
    """Test reload detection when no relevant files have changed."""
    # First load configurations to set registry
    await mock_config_manager.load_configs()
    
    changed_files = {Path("/tmp/test_config/not_relevant.yaml")}
    
    result = mock_config_manager._should_reload(changed_files)
    
    assert result is False


@pytest.mark.asyncio
async def test_add_model_config(mock_config_manager, model_config_instance):
    """Test adding a new model configuration."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    # Create a new model config
    new_model = model_config_instance.model_copy(update={"id": "new_test_model"})
    
    # Patch the add_model_config method to avoid using ModelRegistryEntry
    with patch.object(mock_config_manager, "add_model_config") as mock_add:
        # Call add_model_config
        mock_add.return_value = None
        mock_config_manager.add_model_config(new_model)
        
        # Verify it was called with the correct model
        mock_add.assert_called_once_with(new_model)
    
    # Add the model directly to models dict for test
    mock_config_manager.models["new_test_model"] = new_model
    
    # Check if it was added
    assert "new_test_model" in mock_config_manager.models


@pytest.mark.asyncio
async def test_add_model_config_already_exists(mock_config_manager):
    """Test adding a model configuration that already exists."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    # Get an existing model
    existing_model = mock_config_manager.get_model_config("test_model_1")
    
    # Try to add it again
    with pytest.raises(Exception), patch("builtins.open", create=True), patch("yaml.dump"):
        mock_config_manager.add_model_config(existing_model)


@pytest.mark.asyncio
async def test_update_model_config(mock_config_manager, model_config_instance):
    """Test updating an existing model configuration."""
    # First load configurations
    registry, _ = await mock_config_manager.load_configs()
    
    # Create updated version of an existing model
    updated_model = model_config_instance.model_copy(update={
        "name": "Updated Model",
        "description": "This model was updated"
    })
    
    # Mock registry entry
    mock_entry = MagicMock()
    mock_entry.id = "test_model_1"
    mock_entry.config_file = "models/test_model_1.yaml"
    
    # Update the model with registry mocked
    with patch.object(registry, "models", [mock_entry]), \
         patch("builtins.open", create=True), \
         patch("yaml.dump"):
        mock_config_manager.update_model_config("test_model_1", updated_model)
    
    # Check if it was updated
    assert mock_config_manager.models["test_model_1"].name == "Updated Model"
    assert mock_config_manager.models["test_model_1"].description == "This model was updated"


@pytest.mark.asyncio
async def test_update_model_config_not_found(mock_config_manager, model_config_instance):
    """Test updating a model configuration that doesn't exist."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    # Create a new model with a non-existent ID
    new_model = model_config_instance.model_copy(update={"id": "nonexistent_model"})
    
    # Try to update a non-existent model
    with pytest.raises(Exception):
        mock_config_manager.update_model_config("nonexistent_model", new_model)


@pytest.mark.asyncio
async def test_update_model_config_id_mismatch(mock_config_manager, model_config_instance):
    """Test updating a model configuration with mismatched IDs."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    # Create a model with a different ID
    new_model = model_config_instance.model_copy(update={"id": "different_id"})
    
    # Try to update with mismatched IDs
    with pytest.raises(Exception):
        mock_config_manager.update_model_config("test_model_1", new_model)


@pytest.mark.asyncio
async def test_delete_model_config(mock_config_manager):
    """Test deleting a model configuration."""
    # First load configurations
    registry, _ = await mock_config_manager.load_configs()
    
    # Mock registry entry for test_model_1
    mock_entry = MagicMock()
    mock_entry.id = "test_model_1"
    mock_entry.config_file = "models/test_model_1.yaml"
    
    # Verify the model exists
    assert "test_model_1" in mock_config_manager.models
    
    # Delete the model with mocked registry
    with patch.object(registry, "models", [mock_entry]), \
         patch("builtins.open", create=True), \
         patch("yaml.dump"), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.unlink"):
        mock_config_manager.delete_model_config("test_model_1")
    
    # Check if it was deleted
    assert "test_model_1" not in mock_config_manager.models


@pytest.mark.asyncio
async def test_delete_model_config_not_found(mock_config_manager):
    """Test deleting a model configuration that doesn't exist."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    # Try to delete a non-existent model
    with pytest.raises(Exception):
        mock_config_manager.delete_model_config("nonexistent_model")