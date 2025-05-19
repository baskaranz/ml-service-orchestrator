import pytest
import asyncio
import logging
import json
import yaml
from fastapi import Request
from starlette.datastructures import Headers
from app.services.orchestrator import Orchestrator
from app.models.config_models import ModelConfig, PlatformConfig
from app.core.exceptions import ModelRequestError

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def test_config_path(tmp_path):
    """Create a temporary config directory with model YAMLs in the correct structure."""
    # Create the models directory structure that ModelConfigManager expects
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Model 1 (active)
    model1 = {
        "id": "test-model-1",
        "name": "Test Model 1",
        "endpoint_url": "http://localhost:8001",
        "active": True,
        "platform": {
            "timeout": 30,
            "max_retries": 3,
            "circuit_breaker": {
                "failure_threshold": 5,
                "reset_timeout": 60,
                "half_open_timeout": 30,
                "success_threshold": 2
            }
        }
    }
    with open(models_dir / "test-model-1.yaml", "w") as f:
        yaml.dump(model1, f)
    
    # Model 2 (inactive)
    model2 = {
        "id": "test-model-2",
        "name": "Test Model 2",
        "endpoint_url": "http://localhost:8002",
        "active": False,
        "platform": {
            "timeout": 30,
            "max_retries": 3,
            "circuit_breaker": {
                "failure_threshold": 5,
                "reset_timeout": 60,
                "half_open_timeout": 30,
                "success_threshold": 2
            }
        }
    }
    with open(models_dir / "test-model-2.yaml", "w") as f:
        yaml.dump(model2, f)
    
    return str(tmp_path)

@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request object."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [
            (b"content-type", b"application/json"),
        ]
    }
    request = Request(scope)
    request._body = json.dumps({"test": "data"}).encode()
    return request

@pytest.mark.asyncio
async def test_async_config_loading(test_config_path):
    """Test that the orchestrator loads configurations asynchronously."""
    # Create orchestrator instance
    orchestrator = Orchestrator(test_config_path)
    
    # Verify initial state
    assert len(orchestrator._models) == 0
    
    # Load configurations
    await orchestrator.reload_configs()
    
    # Verify loaded models
    assert len(orchestrator._models) == 1  # Only one active model
    assert "test-model-1" in orchestrator._models
    assert "test-model-2" not in orchestrator._models  # Inactive model should not be loaded
    
    # Verify model configuration
    model_config = orchestrator._models["test-model-1"]
    assert model_config.id == "test-model-1"
    assert model_config.name == "Test Model 1"
    assert model_config.endpoint_url == "http://localhost:8001"
    assert model_config.active is True

@pytest.mark.asyncio
async def test_error_handlers_initialization(test_config_path):
    """Test that error handlers are properly initialized for loaded models."""
    orchestrator = Orchestrator(test_config_path)
    await orchestrator.reload_configs()
    
    # Verify error handlers
    assert "test-model-1" in orchestrator._error_handlers
    assert "test-model-2" not in orchestrator._error_handlers

@pytest.mark.asyncio
async def test_config_reload(test_config_path):
    """Test that configurations can be reloaded."""
    orchestrator = Orchestrator(test_config_path)
    
    # Initial load
    await orchestrator.reload_configs()
    initial_models = orchestrator._models.copy()
    
    # Reload configurations
    await orchestrator.reload_configs()
    
    # Verify models are still the same
    assert orchestrator._models == initial_models

@pytest.mark.asyncio
async def test_model_not_found(test_config_path, mock_request):
    """Test that requesting a non-existent model raises appropriate error."""
    orchestrator = Orchestrator(test_config_path)
    await orchestrator.reload_configs()
    
    # Create a model config for a non-existent model
    non_existent_model = ModelConfig(
        id="non-existent-model",
        name="Non Existent Model",
        endpoint_url="http://localhost:8003",
        active=True
    )
    
    # The model should not be found in the orchestrator's models
    assert non_existent_model.id not in orchestrator._models
    
    # Try to proxy a request to the non-existent model
    with pytest.raises(ModelRequestError) as exc_info:
        await orchestrator.proxy_request(
            model_config=non_existent_model,
            request=mock_request,
            path_suffix=""
        )
    
    # Verify the error message
    error_message = str(exc_info.value)
    assert "not found" in error_message.lower(), f"Expected 'not found' in error message, got: {error_message}" 