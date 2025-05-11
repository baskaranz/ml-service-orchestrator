"""Test fixtures for pytest."""

import os
import sys
import asyncio
import yaml
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.config.models_config import ModelConfigManager
from app.core.models import ModelConfig, CircuitBreakerSettings, AuthConfig, CacheConfig
from app.core.orchestrator import Orchestrator
from app.services.model_registry import ModelRegistryService
from app.services.proxy import ProxyService
from app.main import create_app
from tests.mocks.settings import settings

# Add the application to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return settings


@pytest.fixture
def app():
    """Create a test FastAPI app instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def model_config_instance():
    """Create a sample ModelConfig instance for testing."""
    return ModelConfig(
        id="test_model_1",
        name="Test Model",
        description="A test model for unit tests",
        endpoint_url="http://localhost:8888/test",
        version="1.0.0",
        timeout=10.0,
        max_retries=2,
        circuit_breaker=CircuitBreakerSettings(
            failure_threshold=3,
            reset_timeout=15.0
        ),
        auth=AuthConfig(
            type="api_key",
            key_name="X-API-Key",
            key_value="test_api_key",
            location="header"
        ),
        cache=CacheConfig(
            enabled=True,
            ttl=300,
            max_size=100
        ),
        headers={"X-Source": "test"},
        active=True
    )


@pytest.fixture
def model_configs(model_config_instance):
    """Create a list of model configs for testing."""
    model_2 = ModelConfig(
        id="test_model_2",
        name="Test Model 2",
        description="Another test model for unit tests",
        endpoint_url="http://localhost:8889/test2",
        version="1.0.0",
        timeout=15.0,
        max_retries=3,
        circuit_breaker=CircuitBreakerSettings(
            failure_threshold=4,
            reset_timeout=20.0
        ),
        auth=AuthConfig(
            type="bearer_token",
            key_value="test_token"
        ),
        headers={"X-Source": "test2"},
        active=True
    )
    return [model_config_instance, model_2]


@pytest.fixture
def mock_config_dir():
    """Get the mock config directory path."""
    return "/tmp/test_config"


@pytest.fixture
def test_models_registry():
    """Load the test models registry from file."""
    with open("/tmp/test_config/models_registry.yaml", "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def test_model_config_1():
    """Load the test model 1 config from file."""
    with open("/tmp/test_config/models/test_model_1.yaml", "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def mock_config_manager():
    """Create a mock ModelConfigManager for testing."""
    manager = ModelConfigManager(
        config_dir="/tmp/test_config",
        registry_file="/tmp/test_config/models_registry.yaml"
    )
    return manager


@pytest.fixture
def mock_model_registry():
    """Create a mock ModelRegistryService for testing."""
    config_manager = ModelConfigManager(
        config_dir="/tmp/test_config",
        registry_file="/tmp/test_config/models_registry.yaml"
    )
    service = ModelRegistryService(config_manager)
    
    # Load models into the registry
    service._models = {
        "test_model_1": ModelConfig(
            id="test_model_1",
            name="Test Model",
            description="A test model for unit tests",
            endpoint_url="http://localhost:8888/test",
            version="1.0.0",
            timeout=10.0,
            max_retries=2,
            auth=AuthConfig(type="api_key", key_name="X-API-Key", key_value="test_api_key"),
            active=True
        ),
        "test_model_2": ModelConfig(
            id="test_model_2",
            name="Test Model 2",
            description="Another test model for unit tests",
            endpoint_url="http://localhost:8889/test2",
            version="1.0.0",
            auth=AuthConfig(type="bearer_token", key_value="test_token"),
            active=True
        )
    }
    return service


@pytest.fixture
def mock_orchestrator():
    """Create a mock Orchestrator for testing."""
    return Orchestrator()


@pytest.fixture
def mock_proxy_service(mock_model_registry, mock_orchestrator):
    """Create a mock ProxyService for testing."""
    return ProxyService(mock_model_registry, mock_orchestrator)


@pytest.fixture
async def async_client(app):
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client