"""
Advanced tests for model configuration management.
"""

import logging
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

# Configure logger for tests
logger = logging.getLogger(__name__)


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
    import tempfile
    import shutil
    
    # Create a temporary directory and then remove it to ensure it doesn't exist
    temp_dir = tempfile.mkdtemp()
    shutil.rmtree(temp_dir)
    
    manager = ModelConfigManager(config_dir=temp_dir)
    
    # The directory should be created and load_configs should not raise an error
    try:
        registry, models = await manager.load_configs()
        assert isinstance(registry, ModelRegistry)
        assert isinstance(models, dict)
        assert len(models) == 0  # No models should be loaded
    finally:
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


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
async def test_load_configs_model_validation_error(caplog):
    """Test loading configs when a model file has validation errors."""
    caplog.set_level(logging.DEBUG)  # Enable debug logging for this test
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the expected directory structure: temp_dir/models/ (ModelConfigManager will append env name)
        temp_path = Path(temp_dir)
        models_dir = temp_path / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Created test directory structure at: {temp_path}")
        logger.debug(f"Base models directory: {models_dir}")
        assert models_dir.exists(), f"Base models directory was not created at {models_dir}"
        
        # Create a valid model config with all required fields
        valid_model = {
            "id": "valid_model",
            "name": "Valid Model",
            "endpoint_url": "http://example.com/valid",
            "active": True,
            "timeout": 30.0,
            "max_retries": 3,
            "health_check": {
                "enabled": True,
                "endpoint": "/health",
                "interval": 30,
                "timeout": 5,
                "failure_threshold": 3,
                "success_threshold": 2
            },
            "headers": {
                "Content-Type": "application/json"
            },
            "platform": {
                "timeout": 30.0,
                "max_retries": 3,
                "health_check": {
                    "interval": 30,
                    "timeout": 5,
                    "failure_threshold": 3,
                    "success_threshold": 2
                },
                "circuit_breaker": {
                    "failure_threshold": 5,
                    "reset_timeout": 30.0,
                    "half_open_timeout": 30.0,
                    "success_threshold": 2
                }
            }
        }
        
        # Create an invalid model config (missing required endpoint_url and other fields)
        invalid_model = {
            "id": "invalid_model",
            "name": "Invalid Model"
            # Missing required fields: endpoint_url, health_check, headers, platform
        }
        
        # Write model files to the environment-specific models directory
        with open(models_dir / "valid_model.yaml", "w") as f:
            yaml.dump(valid_model, f)
        with open(models_dir / "invalid_model.yaml", "w") as f:
            yaml.dump(invalid_model, f)
        
        # Create manager with the base config directory
        logger.debug(f"Creating ModelConfigManager with config_dir={temp_dir}, env=test")
        manager = ModelConfigManager(config_dir=str(temp_dir), env="test")
        
        # Log the actual models directory being used
        logger.debug(f"Manager models directory: {manager.models_dir}")
        
        # Ensure the environment-specific models directory exists
        env_models_dir = Path(manager.models_dir)
        env_models_dir.mkdir(parents=True, exist_ok=True)
        
        # Move the model files to the environment-specific directory
        for src_file in models_dir.glob("*.yaml"):
            dest_file = env_models_dir / src_file.name
            src_file.rename(dest_file)
            logger.debug(f"Moved {src_file} to {dest_file}")
        
        # List files in the models directory for debugging
        model_files = list(env_models_dir.glob("*.yaml"))
        logger.debug(f"Found {len(model_files)} YAML files in models directory: {model_files}")
        
        # Should only load the valid model and log an error for the invalid one
        with patch('app.config.models_config.logger.error') as mock_error:
            try:
                registry, models = await manager.load_configs()
                logger.debug(f"Loaded models: {list(models.keys())}")
                
                # Debug: Log all files in the models directory
                all_files = list(Path(manager.models_dir).rglob("*"))
                logger.debug(f"All files in models directory: {all_files}")
                
                # Verify the valid model was loaded
                assert "valid_model" in models, f"valid_model not found in loaded models: {list(models.keys())}"
                assert models["valid_model"].endpoint_url == "http://example.com/valid"
                
                # Verify the invalid model was not loaded
                assert "invalid_model" not in models
                
                # Verify an error was logged for the invalid model
                error_logged = any("Failed to validate model configuration" in str(call) for call in mock_error.call_args_list)
                if not error_logged:
                    logger.error("Expected error log for invalid model not found in:")
                    for call in mock_error.call_args_list:
                        logger.error(f"Error log: {call}")
                assert error_logged
                
            except Exception as e:
                logger.error(f"Error in load_configs: {str(e)}", exc_info=True)
                raise


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