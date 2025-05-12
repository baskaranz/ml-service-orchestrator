"""Test fixtures for pytest."""

import os
import sys
import asyncio
import yaml
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Generator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.models.config_models import ModelConfig, CircuitBreakerConfig, AuthConfig, CacheConfig, AuthType, AuthLocation
from app.config.models_config import ModelConfigManager
from app.services.orchestrator import Orchestrator
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
    """Create a sample model configuration for testing."""
    return ModelConfig(
        id="test_model_1",
        name="Test Model",
        description="A test model for unit tests",
        endpoint_url="http://localhost:8888/test",
        version="1.0.0",
        active=True,
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout=15.0
        ),
        timeout=30.0,
        max_retries=3
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
        active=True,
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=4,
            reset_timeout=20.0
        ),
        timeout=30.0,
        max_retries=3
    )
    return [model_config_instance, model_2]


@pytest.fixture
def mock_config_dir(tmp_path):
    """Create and return a temporary config directory for testing."""
    config_dir = tmp_path / "test_config"
    models_dir = config_dir / "models"
    models_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def test_models_registry():
    """Create a test models registry."""
    return {
        "id": "models_registry",
        "version": "1.0.0",
        "name": "Test Registry",
        "description": "Test registry for unit tests",
        "models": {
            "test_model_1": {
                "id": "test_model_1",
                "config_file": "models/test_model_1.yaml"
            },
            "test_model_2": {
                "id": "test_model_2",
                "config_file": "models/test_model_2.yaml"
            }
        }
    }


@pytest.fixture
def test_model_config_1():
    """Create a test model configuration."""
    return {
        "id": "test_model_1",
        "name": "Test Model",
        "description": "A test model for unit tests",
        "endpoint_url": "http://localhost:8888/test",
        "version": "1.0.0",
        "active": True,
        "circuit_breaker": {
            "failure_threshold": 3,
            "reset_timeout": 15.0
        },
        "max_retries": 3,
        "timeout": 30.0
    }


@pytest.fixture
def mock_config_manager(mock_config_dir, test_models_registry, test_model_config_1):
    """Create a mock ModelConfigManager with test data."""
    # Write test registry file
    registry_file = mock_config_dir / "models" / "registry.yaml"
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_file, "w") as f:
        yaml.dump(test_models_registry, f)
    
    # Write test model config
    model_file = mock_config_dir / "models" / "test_model_1.yaml"
    with open(model_file, "w") as f:
        yaml.dump(test_model_config_1, f)
    
    # Create and return config manager
    manager = ModelConfigManager(
        config_dir=str(mock_config_dir)
    )
    return manager


@pytest.fixture
def mock_orchestrator():
    """Create a mock Orchestrator for testing."""
    return Orchestrator()


@pytest.fixture
def mock_proxy_service():
    """Create a mock ProxyService for testing."""
    return ProxyService()


@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(base_url="http://test") as client:
        yield client