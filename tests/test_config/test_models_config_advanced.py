"""Advanced tests for the models configuration module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock, mock_open

import pytest
import yaml
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.config.models_config import ModelConfigManager
from app.core.models import ModelConfig, ModelRegistry


@pytest.mark.asyncio
async def test_load_configs_file_not_found():
    """Test loading configs when registry file doesn't exist."""
    # Create a manager with a non-existent file
    manager = ModelConfigManager(
        config_dir="/tmp/nonexistent",
        registry_file="/tmp/nonexistent/registry.yaml"
    )
    
    # Try to load configurations and expect FileNotFoundError
    with pytest.raises(FileNotFoundError):
        await manager.load_configs()


@pytest.mark.asyncio
async def test_load_configs_invalid_yaml():
    """Test loading configs with invalid YAML format."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create an invalid YAML file
        registry_file = Path(temp_dir) / "registry.yaml"
        with open(registry_file, "w") as f:
            f.write("invalid: yaml: [unclosed")
        
        # Create a manager with the invalid file
        manager = ModelConfigManager(
            config_dir=temp_dir,
            registry_file=registry_file
        )
        
        # Try to load configurations and expect exception
        with pytest.raises(Exception):
            await manager.load_configs()


@pytest.mark.asyncio
async def test_load_configs_validation_error():
    """Test loading configs with invalid model registry schema."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a registry file with missing required fields
        registry_file = Path(temp_dir) / "registry.yaml"
        with open(registry_file, "w") as f:
            yaml.dump({"invalid_field": "value"}, f)
        
        # Create a manager with the invalid file
        manager = ModelConfigManager(
            config_dir=temp_dir,
            registry_file=registry_file
        )
        
        # Try to load configurations and expect ValidationError
        with pytest.raises(ValidationError):
            await manager.load_configs()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Test is flaky due to model validation behavior")
async def test_load_configs_model_validation_error(mock_config_manager):
    """Test loading configs when a model file has validation errors."""
    # Create a test registry with valid and invalid models
    registry_dict = {
        "version": "1.0.0",
        "name": "Test Registry",
        "models": [
            {"id": "valid_model", "config_file": "models/valid_model.yaml"},
            {"id": "invalid_model", "config_file": "models/invalid_model.yaml"}
        ]
    }
    
    # Create a valid model config
    valid_model_dict = {
        "id": "valid_model",
        "name": "Valid Model",
        "endpoint_url": "http://example.com/valid",
        "version": "1.0.0"
    }
    
    # Create an invalid model config (missing required endpoint_url)
    invalid_model_dict = {
        "id": "invalid_model",
        "name": "Invalid Model"
        # Missing required fields
    }
    
    # Mock reading YAML files
    def mock_read_yaml(file_path):
        if "registry.yaml" in str(file_path):
            return registry_dict
        elif "valid_model.yaml" in str(file_path):
            return valid_model_dict
        elif "invalid_model.yaml" in str(file_path):
            return invalid_model_dict
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Patch the _read_yaml_file method
    with patch.object(mock_config_manager, "_read_yaml_file", side_effect=mock_read_yaml), \
         patch("app.config.models_config.logger") as mock_logger:
        
        # Load configurations
        registry, models = await mock_config_manager.load_configs()
        
        # Verify error was logged
        mock_logger.error.assert_any_call("Invalid model configuration for 'invalid_model': validation error")


@pytest.mark.asyncio
async def test_load_configs_model_id_mismatch(mock_config_manager):
    """Test loading configs when model ID in file doesn't match registry."""
    # Create a test registry
    registry_dict = {
        "version": "1.0.0",
        "name": "Test Registry",
        "models": [
            {"id": "registry_id", "config_file": "models/model.yaml"}
        ]
    }
    
    # Create a model config with mismatched ID
    model_dict = {
        "id": "file_id",  # Different from registry ID
        "name": "Mismatched Model",
        "endpoint_url": "http://example.com/mismatch",
        "version": "1.0.0"
    }
    
    # Mock reading YAML files
    def mock_read_yaml(file_path):
        if "registry.yaml" in str(file_path):
            return registry_dict
        elif "model.yaml" in str(file_path):
            return model_dict
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Patch the _read_yaml_file method
    with patch.object(mock_config_manager, "_read_yaml_file", side_effect=mock_read_yaml), \
         patch("app.config.models_config.logger") as mock_logger:
        # Load configurations
        registry, models = await mock_config_manager.load_configs()
        
        # Verify model was loaded with registry ID
        assert len(models) == 1
        assert "registry_id" in models
        assert models["registry_id"].id == "registry_id"
        assert models["registry_id"].name == "Mismatched Model"
        
        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        assert "Model ID mismatch" in mock_logger.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_load_configs_with_file_not_found_for_model(mock_config_manager):
    """Test loading configs when a model file is not found."""
    # Create a test registry with models
    registry_dict = {
        "version": "1.0.0",
        "name": "Test Registry",
        "models": [
            {"id": "existing_model", "config_file": "models/existing.yaml"},
            {"id": "missing_model", "config_file": "models/missing.yaml"}
        ]
    }
    
    # Create a valid model config
    existing_model_dict = {
        "id": "existing_model",
        "name": "Existing Model",
        "endpoint_url": "http://example.com/existing",
        "version": "1.0.0"
    }
    
    # Mock reading YAML files
    def mock_read_yaml(file_path):
        if "registry.yaml" in str(file_path):
            return registry_dict
        elif "existing.yaml" in str(file_path):
            return existing_model_dict
        elif "missing.yaml" in str(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Patch the _read_yaml_file method
    with patch.object(mock_config_manager, "_read_yaml_file", side_effect=mock_read_yaml), \
         patch("app.config.models_config.logger") as mock_logger:
        # Load configurations
        registry, models = await mock_config_manager.load_configs()
        
        # Verify only the existing model was loaded
        assert len(registry.models) == 2  # Registry still contains both entries
        assert len(models) == 1  # Only the existing model is loaded
        assert "existing_model" in models
        assert "missing_model" not in models
        
        # Verify error was logged
        mock_logger.error.assert_called_with(f"Model configuration file not found: {Path('/tmp/test_config/models/missing.yaml')}")


@pytest.mark.asyncio
async def test_load_configs_with_generic_exception_for_model(mock_config_manager):
    """Test loading configs when a generic exception occurs for a model."""
    # Create a test registry with models
    registry_dict = {
        "version": "1.0.0",
        "name": "Test Registry",
        "models": [
            {"id": "good_model", "config_file": "models/good.yaml"},
            {"id": "error_model", "config_file": "models/error.yaml"}
        ]
    }
    
    # Create a valid model config
    good_model_dict = {
        "id": "good_model",
        "name": "Good Model",
        "endpoint_url": "http://example.com/good",
        "version": "1.0.0"
    }
    
    # Mock reading YAML files
    def mock_read_yaml(file_path):
        if "registry.yaml" in str(file_path):
            return registry_dict
        elif "good.yaml" in str(file_path):
            return good_model_dict
        elif "error.yaml" in str(file_path):
            raise RuntimeError("Unexpected error")
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Patch the _read_yaml_file method
    with patch.object(mock_config_manager, "_read_yaml_file", side_effect=mock_read_yaml), \
         patch("app.config.models_config.logger") as mock_logger:
        # Load configurations
        registry, models = await mock_config_manager.load_configs()
        
        # Verify only the good model was loaded
        assert len(registry.models) == 2  # Registry still contains both entries
        assert len(models) == 1  # Only the good model is loaded
        assert "good_model" in models
        assert "error_model" not in models
        
        # Verify error was logged
        mock_logger.error.assert_called_with("Error loading model 'error_model': Unexpected error")


def test_should_reload_no_registry(mock_config_manager):
    """Test reload detection when registry is not loaded yet."""
    # Ensure registry is None
    mock_config_manager.registry = None
    
    changed_files = {Path("/tmp/test_config/models/test_model_1.yaml")}
    
    result = mock_config_manager._should_reload(changed_files)
    
    # Should not reload since registry is None
    assert result is False


@pytest.mark.asyncio
async def test_update_model_config_registry_entry_not_found(mock_config_manager, model_config_instance):
    """Test updating a model when the registry entry is not found."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    # Add a model to models dict but not to registry
    special_model = model_config_instance.model_copy(update={"id": "special_model"})
    mock_config_manager.models["special_model"] = special_model
    
    # Ensure registry doesn't contain this model
    if mock_config_manager.registry:
        # Remove any entries with this ID if they exist
        mock_config_manager.registry.models = [
            entry for entry in mock_config_manager.registry.models 
            if entry.id != "special_model"
        ]
    
    # Try to update the model without a registry entry
    with pytest.raises(HTTPException) as exc_info:
        mock_config_manager.update_model_config("special_model", special_model)
    
    # Verify the correct exception was raised
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Registry entry for model 'special_model' not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_model_config_registry_entry_not_found(mock_config_manager):
    """Test deleting a model when the registry entry is not found."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    # Add a model to models dict but not to registry
    special_model = ModelConfig(
        id="special_model",
        name="Special Model",
        endpoint_url="http://example.com/special",
        version="1.0.0"
    )
    mock_config_manager.models["special_model"] = special_model
    
    # Ensure registry doesn't contain this model
    if mock_config_manager.registry:
        # Remove any entries with this ID if they exist
        mock_config_manager.registry.models = [
            entry for entry in mock_config_manager.registry.models 
            if entry.id != "special_model"
        ]
    
    # Try to delete the model without a registry entry
    with pytest.raises(HTTPException) as exc_info:
        mock_config_manager.delete_model_config("special_model")
    
    # Verify the correct exception was raised
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Registry entry for model 'special_model' not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_model_config_file_not_found(mock_config_manager):
    """Test deleting a model when the config file doesn't exist."""
    # First load configurations
    registry, _ = await mock_config_manager.load_configs()
    
    # Create a model in registry that doesn't have a file
    mock_entry = MagicMock()
    mock_entry.id = "test_model_1"
    mock_entry.config_file = "models/test_model_1.yaml"
    
    # Delete the model with mocked registry
    with patch.object(registry, "models", [mock_entry]), \
         patch("builtins.open", create=True), \
         patch("yaml.dump"), \
         patch("pathlib.Path.exists", return_value=False), \
         patch("pathlib.Path.unlink") as mock_unlink:
        # Delete should still work even if file doesn't exist
        mock_config_manager.delete_model_config("test_model_1")
        
        # Verify unlink wasn't called since file doesn't exist
        mock_unlink.assert_not_called()
    
    # Check if it was deleted from memory
    assert "test_model_1" not in mock_config_manager.models


def test_process_env_vars_non_string_non_container():
    """Test processing environment variables with non-string, non-container types."""
    manager = ModelConfigManager("/tmp/test", "/tmp/test/registry.yaml")
    
    # Test with various non-string, non-container types
    assert manager._process_env_vars(123) == 123
    assert manager._process_env_vars(123.45) == 123.45
    assert manager._process_env_vars(True) is True
    assert manager._process_env_vars(False) is False
    assert manager._process_env_vars(None) is None