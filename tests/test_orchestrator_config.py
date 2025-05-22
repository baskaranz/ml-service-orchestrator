import json
import logging

import pytest
import yaml
from fastapi import Request

from app.core.exceptions import ModelRequestError
from app.models.config_models import ModelConfig
from app.services.orchestrator import Orchestrator

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def test_config_path(tmp_path):
    """Create a temporary config directory with model YAMLs in the correct structure."""
    # Create the models directory structure that ModelConfigManager expects
    # The structure should be: {tmp_path}/models/test/ for the test environment
    models_dir = tmp_path / "models" / "test"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Set the APP_ENV environment variable to 'test' for this test
    import os

    os.environ["APP_ENV"] = "test"

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
                "success_threshold": 2,
            },
        },
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
                "success_threshold": 2,
            },
        },
    }
    with open(models_dir / "test-model-2.yaml", "w") as f:
        yaml.dump(model2, f)

    # Return the base config directory (tmp_path)
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
        ],
    }
    request = Request(scope)
    request._body = json.dumps({"test": "data"}).encode()
    return request


@pytest.mark.asyncio
async def test_async_config_loading(test_config_path, monkeypatch):
    """Test that the orchestrator loads configurations asynchronously."""
    # Patch the ModelConfigManager to use our test directory
    from app.config.models_config import ModelConfigManager

    # Create a custom ModelConfigManager that uses our test directory
    class TestModelConfigManager(ModelConfigManager):
        def __init__(self, config_dir: str = None, env: str = None):
            # Use the test config directory
            super().__init__(config_dir=test_config_path, env=env)

    # Create orchestrator instance with our test config manager
    orchestrator = Orchestrator(test_config_path)
    orchestrator._model_config_manager = TestModelConfigManager()

    # Verify initial state
    assert len(orchestrator.models) == 0

    # Load configurations
    await orchestrator._load_models()

    # Verify loaded models - should only have test-model-1 which is active
    assert len(orchestrator.models) == 1  # Only one active model
    assert "test-model-1" in orchestrator.models
    assert "test-model-2" not in orchestrator.models  # Inactive model should not be loaded

    # Verify model configuration
    model_config = orchestrator.models["test-model-1"]
    assert model_config.id == "test-model-1"
    assert model_config.name == "Test Model 1"
    assert model_config.endpoint_url == "http://localhost:8001"
    assert model_config.active is True


@pytest.mark.asyncio
async def test_error_handlers_initialization(test_config_path):
    """Test that error handlers are properly initialized for loaded models."""
    orchestrator = Orchestrator(test_config_path)
    await orchestrator.startup()

    # Log the actual error handlers for debugging
    logger.info(f"Available error handlers: {list(orchestrator._error_handlers.keys())}")

    # Verify error handlers for the test models
    assert "test_model" in orchestrator._error_handlers  # From test_model.yaml
    assert "test-model" in orchestrator._error_handlers  # From test-model.yaml
    assert "mock-model-1" in orchestrator._error_handlers  # From mock-model-1.yaml
    assert "mock-model-2" in orchestrator._error_handlers  # From mock-model-2.yaml
    assert "mock-model-3" in orchestrator._error_handlers  # From mock-model-3.yaml


@pytest.mark.asyncio
async def test_config_reload(test_config_path):
    """Test that configurations can be reloaded."""
    orchestrator = Orchestrator(test_config_path)

    # Initial load
    await orchestrator.startup()
    initial_models = orchestrator.models
    initial_model_count = len(initial_models)

    # Verify we loaded some models
    assert initial_model_count > 0, "No models were loaded during startup"

    # Get the first model ID from the loaded models
    test_model_id = next(iter(initial_models.keys()))
    test_model = initial_models[test_model_id]
    test_model_name = test_model.name

    # Verify the test model has the expected attributes
    assert hasattr(test_model, "name"), f"Test model {test_model_id} is missing 'name' attribute"
    assert hasattr(
        test_model, "endpoint_url"
    ), f"Test model {test_model_id} is missing 'endpoint_url' attribute"

    # Store the initial model IDs for comparison
    initial_model_ids = set(initial_models.keys())

    # Use reload_configs to reload configurations
    reload_success = await orchestrator.reload_configs()
    assert reload_success is True, "Failed to reload configurations"

    # Get the models after reload
    reloaded_models = orchestrator.models
    reloaded_model_count = len(reloaded_models)

    # Verify we still have the same number of models after reload
    assert (
        reloaded_model_count == initial_model_count
    ), f"Model count changed after reload. Expected {initial_model_count}, got {reloaded_model_count}"

    # Verify the same model IDs are present
    assert (
        set(reloaded_models.keys()) == initial_model_ids
    ), f"Model IDs changed after reload. Expected {initial_model_ids}, got {set(reloaded_models.keys())}"

    # Verify the test model's name is still the same
    reloaded_test_model = reloaded_models.get(test_model_id)
    assert reloaded_test_model is not None, f"Test model {test_model_id} missing after reload"
    assert (
        reloaded_test_model.name == test_model_name
    ), f"Test model name changed after reload. Expected {test_model_name}, got {reloaded_test_model.name}"


@pytest.mark.asyncio
async def test_model_not_found(test_config_path, mock_request):
    """Test that requesting a non-existent model raises appropriate error."""
    orchestrator = Orchestrator(test_config_path)
    await orchestrator.startup()  # Use startup instead of reload_configs for initial load

    # Create a model config for a non-existent model
    non_existent_model = ModelConfig(
        id="non-existent-model",
        name="Non Existent Model",
        endpoint_url="http://localhost:8003",
        active=True,
        platform={
            "name": "mock",
            "timeout": 30.0,
            "max_retries": 3,
            "health_check": {"enabled": True, "endpoint": "/health"},
            "circuit_breaker": {
                "failure_threshold": 5,
                "reset_timeout_seconds": 60,
                "half_open_timeout_seconds": 30,
                "success_threshold": 2,
            },
        },
        version="1.0.0",
    )

    # Verify the model is not in the orchestrator's models
    assert (
        non_existent_model.id not in orchestrator.models
    ), f"Model {non_existent_model.id} should not be in the orchestrator's models"

    # Try to proxy a request to the non-existent model
    with pytest.raises(ModelRequestError) as exc_info:
        await orchestrator.proxy_request(
            model_config=non_existent_model, request=mock_request, path_suffix=""
        )

    # Verify the error message contains information about the model not being found or not active
    error_message = str(exc_info.value).lower()
    expected_phrases = ["not found", "not available", "not active"]
    assert any(
        phrase in error_message for phrase in expected_phrases
    ), f"Expected error message to contain one of {expected_phrases}, got: {error_message}"
