"""Test fixtures for pytest."""

import os
import sys
import asyncio
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator, Union
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import create_app
from app.config.settings import settings as app_settings
from app.models.config_models import (
    ModelConfig,
    PlatformConfig,
    AuthConfig,
    CircuitBreakerConfig,
    LLMProviderConfig,
    ErrorHandlingConfig,
    RequestConfig,
    HealthCheckConfig,
    LoggingConfig,
    BasicErrorHandlingConfig,
    LLMErrorHandlingConfig,
    BasicCircuitBreakerConfig,
    LLMCircuitBreakerConfig
)
from app.config.models_config import ModelConfigManager
from app.services.orchestrator import Orchestrator
from app.services.model_registry import ModelRegistryService
from app.services.proxy import ProxyService

# Add the application to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return app_settings


@pytest.fixture
def app():
    """Create a test FastAPI app instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)

@pytest_asyncio.fixture
async def async_client(app):
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def model_config_instance():
    """Create a sample model configuration for testing."""
    return ModelConfig(
        id="test_model_1",
        name="Test Model",
        description="A test model for unit tests",
        version="1.0.0",
        endpoint_url="http://localhost:8888/predict",
        active=True,
        platform=PlatformConfig(
            timeout=30.0,
            max_retries=3,
            health_check={
                "interval": 60,
                "timeout": 10,
                "failure_threshold": 5,
                "success_threshold": 3
            },
            circuit_breaker={
                "failure_threshold": 10,
                "reset_timeout": 60.0,
                "half_open_timeout": 60.0,
                "success_threshold": 4
            }
        ),
        error_handling=ErrorHandlingConfig(
            retry_policy={
                "max_retries": 3,
                "backoff_factor": 0.1,
                "status_codes": [500, 502, 503, 504]
            },
            fallback_strategy="default_response"
        ),
        circuit_breaker={
            "failure_threshold": 5,
            "reset_timeout": 30.0,
            "half_open_timeout": 15.0,
            "success_threshold": 3
        },

        request=RequestConfig(
            timeout=30.0,
            headers={"Content-Type": "application/json"},
            max_retries=3,
            retry_delay=1.0
        ),
        health_check={
            "enabled": True,
            "interval": 60,
            "timeout": 10,
            "failure_threshold": 5,
            "success_threshold": 3
        },

        logging={
            "level": "INFO",
            "format": "json"
        },
        auth={
            "enabled": False,
            "type": "api_key",
            "header_name": "X-API-Key",
            "value": "${API_KEY}"
        }
    )


@pytest.fixture
def model_configs(model_config_instance):
    """Create a list of model configs for testing."""
    model_2 = ModelConfig(
        id="test_model_2",
        name="Test Model 2",
        endpoint_url="http://localhost:8889/predict",
        active=True
    )
    return [model_config_instance, model_2]


@pytest.fixture
def mock_config_dir(tmp_path):
    """Create and return a temporary config directory for testing.
    
    Creates the following structure:
    tmp_path/
    └── test_config/
        ├── dev/
        │   └── models/
        ├── stg/
        │   └── models/
        └── prod/
            └── models/
    """
    config_dir = tmp_path / "test_config"
    
    # Create environment-specific model directories
    for env in ["dev", "stg", "prod"]:
        env_dir = config_dir / env / "models"
        env_dir.mkdir(parents=True, exist_ok=True)
    
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
        "endpoint_url": "http://localhost:8888/predict",
        "active": True
    }


@pytest.fixture
def mock_config_manager(mock_config_dir, test_models_registry, test_model_config_1):
    """Create a mock ModelConfigManager with test data.
    
    Writes test data to the dev environment by default.
    """
    # Use dev environment for testing
    env = "dev"
    env_dir = mock_config_dir / env
    models_dir = env_dir / "models"
    
    # Ensure directories exist
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Write test registry file
    registry_file = models_dir / "registry.yaml"
    with open(registry_file, "w") as f:
        yaml.dump(test_models_registry, f)
    
    # Write test model config
    model_file = models_dir / "test_model_1.yaml"
    with open(model_file, "w") as f:
        yaml.dump(test_model_config_1, f)
    
    # Create a mock ModelConfigManager pointing to the environment directory
    manager = ModelConfigManager(config_dir=str(env_dir))
    
    # Load the test data
    manager.load_configs()
    return manager


@pytest.fixture
def mock_orchestrator():
    """Create a mock Orchestrator for testing."""
    return Orchestrator(config_path="config/models")


@pytest.fixture
def mock_proxy_service():
    """Create a mock ProxyService for testing."""
    return ProxyService()


@pytest_asyncio.fixture
async def async_client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(base_url="http://test") as client:
        yield client


@pytest.fixture
def llm_provider_config():
    """Global dummy fixture for llm_provider_config."""
    return None