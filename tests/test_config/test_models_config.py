"""
Tests for model configuration management.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock, mock_open

import pytest
import yaml

from app.models.config_models import ModelConfig, ModelRegistry, CircuitBreakerConfig, LLMProviderConfig
from app.config.models_config import ModelConfigManager
from app.core.exceptions import ModelAlreadyExistsError, ModelNotFoundError


@pytest.fixture
def test_model_configs():
    """Create test model configurations."""
    return {
        "test_model_1": {
            "id": "test_model_1",
            "name": "Test Model",
            "description": "Test model 1",
            "version": "1.0.0",
            "endpoint_url": "http://localhost:8001/predict",
            "active": True,
            "circuit_breaker": {
                "failure_threshold": 5,
                "reset_timeout": 30.0
            },
            "max_retries": 3,
            "timeout": 30.0,
            "type": "classification",
            "metadata": {
                "framework": "pytorch",
                "tags": ["test", "dummy"]
            }
        },
        "test_model_2": {
            "id": "test_model_2",
            "name": "Test Model 2",
            "description": "Test model 2",
            "version": "1.0.0",
            "endpoint_url": "http://localhost:8002/predict",
            "active": True,
            "circuit_breaker": {
                "failure_threshold": 5,
                "reset_timeout": 30.0
            },
            "max_retries": 3,
            "timeout": 30.0,
            "type": "regression",
            "metadata": {
                "framework": "tensorflow",
                "tags": ["test", "dummy"]
            }
        }
    }


@pytest.fixture
def mock_config_manager(test_model_configs):
    """Create a mock configuration manager."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create model config files
        for model_id, config in test_model_configs.items():
            config_file = Path(temp_dir) / f"{model_id}.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config, f)
        
        # Create manager with temp directory
        manager = ModelConfigManager(config_dir=temp_dir)
        
        # Mock file operations
        def mock_read_yaml(file_path):
            model_id = Path(file_path).stem
            if model_id in test_model_configs:
                return test_model_configs[model_id]
            raise FileNotFoundError(f"File not found: {file_path}")
        
        manager._read_yaml_file = mock_read_yaml
        yield manager


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


@pytest.fixture
def model_config_instance(llm_provider_config):
    """Create a model configuration instance."""
    return ModelConfig(
        id="test_model_1",
        name="Test Model",
        description="Test model 1",
        version="1.0.0",
        endpoint_url="http://localhost:8001/predict",
        active=True,
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=5,
            reset_timeout=30.0
        ),
        max_retries=3,
        timeout=30.0,
        llm_provider=llm_provider_config
    )


@pytest.mark.asyncio
async def test_load_configs(mock_config_manager):
    """Test loading all model configurations."""
    registry, models = await mock_config_manager.load_configs()
    
    assert registry is not None
    assert registry.version == "1.0.0"
    assert registry.name == "Model Registry"
    assert len(registry.models) == 2
    assert len(models) == 2
    
    # Check model 1
    assert "test_model_1" in models
    model1 = models["test_model_1"]
    assert model1.name == "Test Model"
    assert model1.type == "classification"
    assert model1.metadata["framework"] == "pytorch"
    
    # Check model 2
    assert "test_model_2" in models
    model2 = models["test_model_2"]
    assert model2.name == "Test Model 2"
    assert model2.type == "regression"
    assert model2.metadata["framework"] == "tensorflow"
    
    # Check registry entries
    registry_model1 = registry.models["test_model_1"]
    assert registry_model1["name"] == "Test Model"
    assert registry_model1["type"] == "classification"
    assert registry_model1["metadata"]["framework"] == "pytorch"
    assert registry_model1["config_file"] == "models/test_model_1.yaml"


def test_read_yaml_file(mock_config_manager, test_model_configs):
    """Test reading a YAML file."""
    file_path = Path(mock_config_manager.config_dir) / "test_model_1.yaml"
    result = mock_config_manager._read_yaml_file(file_path)
    
    assert result == test_model_configs["test_model_1"]
    assert result["name"] == "Test Model"
    assert result["type"] == "classification"
    assert result["metadata"]["framework"] == "pytorch"


@pytest.mark.asyncio
async def test_get_model_config_not_found(mock_config_manager):
    """Test getting a model configuration that doesn't exist."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    # Try to get a non-existent model
    with pytest.raises(ModelNotFoundError):
        mock_config_manager.get_model_config("nonexistent_model")


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
async def test_add_model_config_already_exists(mock_config_manager, model_config_instance, llm_provider_config):
    """Test adding a model configuration that already exists."""
    await mock_config_manager.load_configs()
    # Try to add a model that already exists
    duplicate_model = model_config_instance.model_copy()
    with pytest.raises(ModelAlreadyExistsError):
        mock_config_manager.add_model_config(duplicate_model)


@pytest.mark.asyncio
async def test_add_model_config(mock_config_manager, llm_provider_config):
    """Test adding a new model configuration."""
    new_model = ModelConfig(
        id="test_model_3",
        name="Test Model 3",
        description="Test model 3",
        version="1.0.0",
        endpoint_url="http://localhost:8003/predict",
        active=True,
        type="classification",
        metadata={"framework": "sklearn"},
        llm_provider=llm_provider_config
    )
    
    mock_config_manager.add_model_config(new_model)
    
    assert "test_model_3" in mock_config_manager.models
    assert mock_config_manager.models["test_model_3"].name == "Test Model 3"
    assert mock_config_manager.registry is not None
    assert "test_model_3" in mock_config_manager.registry.models
    assert mock_config_manager.registry.models["test_model_3"]["name"] == "Test Model 3"


@pytest.mark.asyncio
async def test_update_model_config_not_found(mock_config_manager, model_config_instance, llm_provider_config):
    """Test updating a model configuration that doesn't exist."""
    await mock_config_manager.load_configs()
    # Try to update a non-existent model
    update_model = model_config_instance.model_copy()
    with pytest.raises(ModelNotFoundError):
        mock_config_manager.update_model_config("nonexistent_model", update_model)


@pytest.mark.asyncio
async def test_update_model_config(mock_config_manager, llm_provider_config):
    """Test updating an existing model configuration."""
    # First load the configs
    await mock_config_manager.load_configs()
    
    # Update model 1
    updated_model = ModelConfig(
        id="test_model_1",
        name="Updated Test Model",
        description="Updated test model 1",
        version="1.0.0",
        endpoint_url="http://localhost:8001/predict",
        active=True,
        type="classification",
        metadata={"framework": "pytorch", "tags": ["updated"]},
        llm_provider=llm_provider_config
    )
    
    mock_config_manager.update_model_config("test_model_1", updated_model)
    
    assert mock_config_manager.models["test_model_1"].name == "Updated Test Model"
    assert mock_config_manager.registry is not None
    assert mock_config_manager.registry.models["test_model_1"]["name"] == "Updated Test Model"
    assert mock_config_manager.registry.models["test_model_1"]["metadata"]["tags"] == ["updated"]


@pytest.mark.asyncio
async def test_delete_model_config_not_found(mock_config_manager):
    """Test deleting a model configuration that doesn't exist."""
    # First load configurations
    await mock_config_manager.load_configs()
    
    # Try to delete a non-existent model
    with pytest.raises(ModelNotFoundError):
        mock_config_manager.delete_model_config("nonexistent_model")


@pytest.mark.asyncio
async def test_delete_model_config(mock_config_manager):
    """Test deleting a model configuration."""
    # First load the configs
    await mock_config_manager.load_configs()
    
    # Delete model 1
    mock_config_manager.delete_model_config("test_model_1")
    
    assert "test_model_1" not in mock_config_manager.models
    assert mock_config_manager.registry is not None
    assert "test_model_1" not in mock_config_manager.registry.models
    assert "test_model_2" in mock_config_manager.models  # Other model should still exist