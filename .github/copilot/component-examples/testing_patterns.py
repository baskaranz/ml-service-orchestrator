"""
ML Orchestrator Testing Patterns

This example demonstrates the testing patterns used in the ML Orchestrator,
including async testing, mocking, and fixture patterns.
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, Generator, List, Optional

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_mock import MockerFixture
from unittest.mock import AsyncMock, MagicMock, patch

# --- Example Models and Functions to Test ---

class ModelConfig(BaseModel):
    """Example model configuration class."""
    model_id: str
    version: str
    endpoint: str
    timeout_ms: int = 1000
    max_batch_size: int = 1
    enabled: bool = True


class ModelRegistry:
    """Example service class that we want to test."""
    
    def __init__(self, registry_url: str):
        self.registry_url = registry_url
        self._client = None  # This would be an HTTP client in real code
    
    async def get_model_config(self, model_id: str) -> ModelConfig:
        """Get model configuration from the registry."""
        # In real code, this would make an HTTP request
        # For this example, we'll simulate that with a delay
        await asyncio.sleep(0.1)
        
        # Simulate a "not found" scenario for testing
        if model_id == "nonexistent_model":
            raise ValueError(f"Model not found: {model_id}")
        
        # Return a mock config
        return ModelConfig(
            model_id=model_id,
            version="1.0.0",
            endpoint=f"https://models.example.com/{model_id}",
            timeout_ms=2000,
            max_batch_size=16,
            enabled=True
        )
    
    async def list_models(self) -> List[str]:
        """List available models in the registry."""
        # Simulate API call
        await asyncio.sleep(0.1)
        return ["model1", "model2", "model3"]


async def load_model_config(registry: ModelRegistry, model_id: str) -> ModelConfig:
    """Example function that uses the registry service."""
    try:
        config = await registry.get_model_config(model_id)
        if not config.enabled:
            raise ValueError(f"Model {model_id} is disabled")
        return config
    except Exception as e:
        # Re-raise with additional context
        raise RuntimeError(f"Failed to load config for model {model_id}: {str(e)}") from e


# --- Test Fixtures ---

@pytest.fixture
def sample_config_file(tmp_path) -> str:
    """Create a sample YAML config file for testing."""
    config_data = {
        "models": {
            "test_model": {
                "version": "1.0.0",
                "endpoint": "https://models.example.com/test_model",
                "timeout_ms": 3000,
                "max_batch_size": 32,
                "enabled": True
            }
        }
    }
    
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
    
    return str(config_file)


@pytest.fixture
def mock_registry() -> ModelRegistry:
    """Create a ModelRegistry instance with a mock URL."""
    return ModelRegistry(registry_url="https://registry.example.com")


@pytest.fixture
async def patched_registry() -> AsyncGenerator[ModelRegistry, None]:
    """Create a patched ModelRegistry with mocked methods."""
    registry = ModelRegistry(registry_url="https://registry.example.com")
    
    # Create dummy models dictionary
    models = {
        "test_model": ModelConfig(
            model_id="test_model",
            version="1.0.0",
            endpoint="https://models.example.com/test_model",
            timeout_ms=3000,
            max_batch_size=32,
            enabled=True
        ),
        "disabled_model": ModelConfig(
            model_id="disabled_model",
            version="1.0.0",
            endpoint="https://models.example.com/disabled_model",
            timeout_ms=3000,
            max_batch_size=32,
            enabled=False
        )
    }
    
    # Patch the instance methods using AsyncMock
    async def mock_get_model_config(model_id: str) -> ModelConfig:
        if model_id not in models:
            raise ValueError(f"Model not found: {model_id}")
        return models[model_id]
    
    async def mock_list_models() -> List[str]:
        return list(models.keys())
    
    # Use patch to replace the methods
    with (
        patch.object(registry, "get_model_config", side_effect=mock_get_model_config),
        patch.object(registry, "list_models", side_effect=mock_list_models)
    ):
        yield registry


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app for testing."""
    from fastapi import FastAPI, Depends, HTTPException
    
    app = FastAPI()
    
    # Simple dependency to get a registry
    def get_registry():
        return ModelRegistry(registry_url="https://registry.example.com")
    
    @app.get("/models")
    async def list_models(registry: ModelRegistry = Depends(get_registry)):
        return {"models": await registry.list_models()}
    
    @app.get("/models/{model_id}")
    async def get_model(model_id: str, registry: ModelRegistry = Depends(get_registry)):
        try:
            return await registry.get_model_config(model_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    return app


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


# --- Test Cases ---

# 1. Unit Tests for Synchronous Functions
def test_model_config_validation():
    """Test that ModelConfig validates correctly."""
    # Valid config
    config = ModelConfig(
        model_id="test_model",
        version="1.0.0",
        endpoint="https://models.example.com/test"
    )
    assert config.model_id == "test_model"
    assert config.timeout_ms == 1000  # Default value
    
    # Create with all fields
    config = ModelConfig(
        model_id="test_model",
        version="1.0.0",
        endpoint="https://models.example.com/test",
        timeout_ms=5000,
        max_batch_size=64,
        enabled=False
    )
    assert config.timeout_ms == 5000
    assert config.max_batch_size == 64
    assert config.enabled is False


def test_load_config_from_file(sample_config_file):
    """Test loading configuration from a YAML file."""
    with open(sample_config_file, "r") as f:
        config_data = yaml.safe_load(f)
    
    assert "models" in config_data
    assert "test_model" in config_data["models"]
    
    model_data = config_data["models"]["test_model"]
    config = ModelConfig(model_id="test_model", **model_data)
    
    assert config.version == "1.0.0"
    assert config.endpoint == "https://models.example.com/test_model"
    assert config.timeout_ms == 3000
    assert config.max_batch_size == 32
    assert config.enabled is True


# 2. Unit Tests for Asynchronous Functions
@pytest.mark.asyncio
async def test_registry_get_model_config(mock_registry):
    """Test getting a model config from the registry."""
    # Patch the method for this test only
    with patch.object(
        mock_registry, 
        "get_model_config", 
        new_callable=AsyncMock
    ) as mock_get_config:
        # Set up the mock to return a specific value
        mock_get_config.return_value = ModelConfig(
            model_id="test_model",
            version="1.0.0",
            endpoint="https://models.example.com/test"
        )
        
        # Call the method
        config = await mock_registry.get_model_config("test_model")
        
        # Verify the result
        assert config.model_id == "test_model"
        assert config.version == "1.0.0"
        
        # Verify the mock was called correctly
        mock_get_config.assert_called_once_with("test_model")


@pytest.mark.asyncio
async def test_load_model_config_success(patched_registry):
    """Test successfully loading a model config."""
    # Use the patched registry fixture
    config = await load_model_config(patched_registry, "test_model")
    
    assert config.model_id == "test_model"
    assert config.version == "1.0.0"
    assert config.enabled is True


@pytest.mark.asyncio
async def test_load_model_config_disabled(patched_registry):
    """Test loading a disabled model config."""
    # Should raise an error for disabled models
    with pytest.raises(RuntimeError) as excinfo:
        await load_model_config(patched_registry, "disabled_model")
    
    assert "is disabled" in str(excinfo.value)


@pytest.mark.asyncio
async def test_load_model_config_not_found(patched_registry):
    """Test loading a nonexistent model config."""
    # Should raise an error for nonexistent models
    with pytest.raises(RuntimeError) as excinfo:
        await load_model_config(patched_registry, "nonexistent_model")
    
    assert "Model not found" in str(excinfo.value)


# 3. API Tests with TestClient
def test_list_models_endpoint(test_client, monkeypatch):
    """Test the list models API endpoint."""
    # Monkeypatch the async method in the registry
    async def mock_list_models():
        return ["model1", "model2"]
    
    # Apply the patch
    monkeypatch.setattr(ModelRegistry, "list_models", mock_list_models)
    
    # Make the request
    response = test_client.get("/models")
    
    # Verify the response
    assert response.status_code == 200
    assert response.json() == {"models": ["model1", "model2"]}


def test_get_model_endpoint(test_client, monkeypatch):
    """Test the get model API endpoint."""
    # Monkeypatch the async method in the registry
    async def mock_get_model_config(self, model_id: str):
        if model_id == "test_model":
            return ModelConfig(
                model_id=model_id,
                version="1.0.0",
                endpoint="https://models.example.com/test"
            )
        raise ValueError(f"Model not found: {model_id}")
    
    # Apply the patch
    monkeypatch.setattr(ModelRegistry, "get_model_config", mock_get_model_config)
    
    # Test successful request
    response = test_client.get("/models/test_model")
    assert response.status_code == 200
    assert response.json()["model_id"] == "test_model"
    
    # Test 404 for nonexistent model
    response = test_client.get("/models/nonexistent_model")
    assert response.status_code == 404
    assert "Model not found" in response.json()["detail"]


# 4. Mock Tests with pytest-mock
def test_registry_with_pytest_mock(mocker: MockerFixture):
    """Test using pytest-mock for more complex mocking."""
    # Create a registry instance
    registry = ModelRegistry(registry_url="https://registry.example.com")
    
    # Create an AsyncMock for the get_model_config method
    mock_get_config = mocker.patch.object(
        registry, 
        "get_model_config",
        new_callable=AsyncMock
    )
    
    # Set up return value
    mock_config = ModelConfig(
        model_id="test_model",
        version="1.0.0",
        endpoint="https://models.example.com/test"
    )
    mock_get_config.return_value = mock_config
    
    # Create an AsyncMock for load_model_config
    mock_load_config = mocker.patch(
        "builtins.load_model_config",  # In real code, use the correct module path
        new_callable=AsyncMock
    )
    mock_load_config.return_value = mock_config
    
    # In a real test, we would call functions that use these mocks
    # and then make assertions about how they were called


# 5. Parametrized Tests
@pytest.mark.parametrize(
    "model_id,expected_status", 
    [
        ("test_model", 200),
        ("nonexistent_model", 404),
        ("disabled_model", 200),
    ]
)
def test_get_model_parametrized(test_client, monkeypatch, model_id, expected_status):
    """Parametrized test for the get model endpoint."""
    # Define models
    models = {
        "test_model": ModelConfig(
            model_id="test_model",
            version="1.0.0",
            endpoint="https://models.example.com/test",
            enabled=True
        ),
        "disabled_model": ModelConfig(
            model_id="disabled_model",
            version="1.0.0",
            endpoint="https://models.example.com/disabled",
            enabled=False
        ),
    }
    
    # Monkeypatch the method
    async def mock_get_model_config(self, model_id: str):
        if model_id not in models:
            raise ValueError(f"Model not found: {model_id}")
        return models[model_id]
    
    monkeypatch.setattr(ModelRegistry, "get_model_config", mock_get_model_config)
    
    # Make the request
    response = test_client.get(f"/models/{model_id}")
    
    # Check status code
    assert response.status_code == expected_status
    
    # For successful responses, check the model ID
    if expected_status == 200:
        assert response.json()["model_id"] == model_id


# --- Integration Test Example ---

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_model_loading_flow():
    """
    Integration test for the full model loading flow.
    
    This test requires actual services to be running and is marked
    with the 'integration' marker to be skipped in regular test runs.
    """
    # Check if integration tests are enabled
    if not os.environ.get("ENABLE_INTEGRATION_TESTS"):
        pytest.skip("Integration tests disabled")
    
    # Create a real registry client (would point to a test instance in CI)
    registry = ModelRegistry(
        registry_url=os.environ.get("TEST_REGISTRY_URL", "https://test-registry.example.com")
    )
    
    # Test with a known model in the test environment
    test_model_id = os.environ.get("TEST_MODEL_ID", "integration_test_model")
    
    # Load the model config
    config = await load_model_config(registry, test_model_id)
    
    # Verify expected properties
    assert config.model_id == test_model_id
    assert config.enabled is True
    assert isinstance(config.timeout_ms, int)


# --- Test Helpers ---

def assert_models_equal(actual: ModelConfig, expected: ModelConfig) -> None:
    """Helper function to assert that two ModelConfig objects are equal."""
    assert actual.model_id == expected.model_id
    assert actual.version == expected.version
    assert actual.endpoint == expected.endpoint
    assert actual.timeout_ms == expected.timeout_ms
    assert actual.max_batch_size == expected.max_batch_size
    assert actual.enabled == expected.enabled


def mock_config_response(model_id: str) -> Dict[str, Any]:
    """Generate a mock registry response for testing."""
    return {
        "model_id": model_id,
        "version": "1.0.0",
        "endpoint": f"https://models.example.com/{model_id}",
        "timeout_ms": 2000,
        "max_batch_size": 16,
        "enabled": True
    }


async def run_with_timeout(coro, timeout=1.0):
    """Helper to run a coroutine with a timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
"""