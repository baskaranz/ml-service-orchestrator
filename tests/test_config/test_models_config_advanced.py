"""
Advanced tests for model configuration management.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock, mock_open

import pytest
import yaml
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.models.config_models import ModelConfig, ModelRegistry, CircuitBreakerConfig, LLMProviderConfig
from app.config.models_config import ModelConfigManager
from app.core.exceptions import ModelAlreadyExistsError, ModelNotFoundError


@pytest.fixture
def llm_provider_config() -> LLMProviderConfig:
    """Create a test LLM provider configuration."""
    return LLMProviderConfig(
        type="huggingface",
        model_name="test-model",
        timeout=30,
        max_retries=3,
        api_key="test-key"
    )


@pytest.mark.asyncio
async def test_load_configs_directory_not_found():
    """Test loading configs when directory doesn't exist."""
    # Create a manager with a non-existent directory
    manager = ModelConfigManager(config_dir="/tmp/nonexistent")
    
    # Try to load configurations and expect FileNotFoundError
    with pytest.raises(FileNotFoundError):
        await manager.load_configs()


@pytest.mark.asyncio
async def test_load_configs_invalid_yaml():
    """Test loading configs with invalid YAML format."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create an invalid YAML file
        model_file = Path(temp_dir) / "invalid_model.yaml"
        with open(model_file, "w") as f:
            f.write("invalid: yaml: [unclosed")
        
        # Create a manager with the invalid file
        manager = ModelConfigManager(config_dir=temp_dir)
        
        # Should not raise, but should skip invalid file
        registry, models = await manager.load_configs()
        assert len(models) == 0


@pytest.mark.asyncio
async def test_load_configs_validation_error():
    """Test loading configs with invalid model schema."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a model file with missing required fields
        model_file = Path(temp_dir) / "invalid_model.yaml"
        with open(model_file, "w") as f:
            yaml.dump({"invalid_field": "value"}, f)
        
        # Create a manager with the invalid file
        manager = ModelConfigManager(config_dir=temp_dir)
        
        # Should not raise, but should skip invalid file
        registry, models = await manager.load_configs()
        assert len(models) == 0


@pytest.mark.asyncio
async def test_load_configs_model_validation_error():
    """Test loading configs when a model file has validation errors."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a valid model config
        valid_model = {
            "id": "valid_model",
            "name": "Valid Model",
            "description": "A valid model for testing",
            "endpoint_url": "http://example.com/valid",
            "version": "1.0.0",
            "active": True,
            "timeout": 30.0,
            "max_retries": 3,
            "circuit_breaker": {
                "failure_threshold": 5,
                "reset_timeout": 30.0
            }
        }
        
        # Create an invalid model config (missing required endpoint_url)
        invalid_model = {
            "id": "invalid_model",
            "name": "Invalid Model",
            "description": "An invalid model for testing"
            # Missing required fields: endpoint_url, version
        }
        
        # Write model files
        with open(Path(temp_dir) / "valid_model.yaml", "w") as f:
            yaml.dump(valid_model, f)
        with open(Path(temp_dir) / "invalid_model.yaml", "w") as f:
            yaml.dump(invalid_model, f)
        
        # Create manager
        manager = ModelConfigManager(config_dir=temp_dir)
        
        # Should only load the valid model
        registry, models = await manager.load_configs()
        assert "valid_model" in models
        assert "invalid_model" not in models


@pytest.mark.asyncio
async def test_load_configs_model_id_mismatch():
    """Test loading configs when model ID in file doesn't match filename."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a model config with mismatched ID
        model_dict = {
            "id": "file_id",  # Different from filename
            "name": "Mismatched Model",
            "description": "A mismatched model",
            "endpoint_url": "http://example.com/mismatch",
            "version": "1.0.0",
            "active": True,
            "timeout": 30.0,
            "max_retries": 3,
            "circuit_breaker": {
                "failure_threshold": 5,
                "reset_timeout": 30.0
            }
        }
        
        # Write model file with different name
        with open(Path(temp_dir) / "different_name.yaml", "w") as f:
            yaml.dump(model_dict, f)
        
        # Create manager
        manager = ModelConfigManager(config_dir=temp_dir)
        
        # Should skip the mismatched file
        registry, models = await manager.load_configs()
        assert len(models) == 0


def test_should_reload_no_registry():
    """Test reload detection when registry is not loaded yet."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ModelConfigManager(config_dir=temp_dir)
        
        # Ensure registry is None
        manager.registry = None
        
        changed_files = {Path(temp_dir) / "test_model_1.yaml"}
        
        result = manager.should_reload(changed_files)
        
        # Should not reload since registry is None
        assert result is False


@pytest.mark.asyncio
async def test_update_model_config_not_found(llm_provider_config):
    """Test updating a model when it doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ModelConfigManager(config_dir=temp_dir)
        # First load configurations
        await manager.load_configs()
        # Try to update a non-existent model
        model = ModelConfig(
            id="nonexistent_model",
            name="Nonexistent Model",
            description="A model that doesn't exist",
            endpoint_url="http://example.com/nonexistent",
            version="1.0.0",
            active=True,
            timeout=30.0,
            max_retries=3,
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=5,
                reset_timeout=30.0
            ),
            llm_provider=llm_provider_config
        )
        with pytest.raises(ModelNotFoundError):
            manager.update_model_config("nonexistent_model", model)


@pytest.mark.asyncio
async def test_delete_model_config_not_found():
    """Test deleting a model when it doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ModelConfigManager(config_dir=temp_dir)
        
        # First load configurations
        await manager.load_configs()
        
        # Try to delete a non-existent model
        with pytest.raises(ModelNotFoundError):
            manager.delete_model_config("nonexistent_model")