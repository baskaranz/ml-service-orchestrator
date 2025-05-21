"""Main test configuration and fixtures for the ML Service Orchestrator.

This file imports and re-exports fixtures from specialized fixture modules
and defines additional fixtures that don't fit into those categories.

Imported fixtures:
- From fixtures.models: model_config_instance, model_configs, multiple_model_configs, etc.
- From fixtures.clients: app, client, async_client, admin_headers
- From fixtures.settings: mock_settings, test_env, override_settings
- From fixtures.services: orchestrator_service, proxy_service
"""

import os
import sys
from typing import Dict, List, Optional

import pytest
import pytest_asyncio
import yaml

from app.config.models_config import ModelConfigManager
from app.models.config_models import ModelConfig

# Import fixtures from specialized modules
from tests.fixtures.models import (
    model_config_instance,
    inactive_model_config,
    model_configs,
    multiple_model_configs,
    create_model_config,
)

from tests.fixtures.clients import (
    app,
    client,
    async_client,
    admin_headers,
)

from tests.fixtures.settings import (
    test_env,
    mock_settings,
    override_settings,
)

from tests.fixtures.services import (
    orchestrator_service,
    proxy_service,
)

# Make sure the application is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Additional fixtures that don't fit into specialized modules
@pytest.fixture(scope="function")
def yaml_config_file(tmp_path, model_config_instance: ModelConfig):
    """Create a temporary YAML config file for testing.
    
    Args:
        tmp_path: Pytest fixture for temporary directory
        model_config_instance: A model configuration instance
        
    Returns:
        Path to the temporary YAML file
    """
    # Create a config directory in the temporary path
    config_dir = tmp_path / "config" / "test" / "models"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert the model config to a dictionary
    config_dict = model_config_instance.dict()
    
    # Write the config to a YAML file
    config_file = config_dir / f"{model_config_instance.id}.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_dict, f)
    
    return config_file


@pytest.fixture(scope="function")
def config_manager(tmp_path):
    """Create a model config manager for testing.
    
    Args:
        tmp_path: Pytest fixture for temporary directory
        
    Returns:
        An initialized ModelConfigManager
    """
    # Create a config directory in the temporary path
    config_dir = tmp_path / "config" / "test"
    models_dir = config_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Create and return the config manager
    return ModelConfigManager(config_dir=str(config_dir), models_dir=str(models_dir))


@pytest.fixture(scope="function")
def mock_response():
    """Create a mock response object for testing.
    
    Returns:
        A function that creates a mock response with specified status and content
    """
    class MockResponse:
        def __init__(self, status_code=200, json_data=None, content=None, headers=None):
            self.status_code = status_code
            self._json_data = json_data or {}
            self.content = content or b""
            self.headers = headers or {"Content-Type": "application/json"}
            
        async def json(self):
            return self._json_data
            
        async def text(self):
            return str(self.content, "utf-8") if isinstance(self.content, bytes) else str(self.content)
            
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    def _create_mock_response(status_code=200, json_data=None, content=None, headers=None):
        return MockResponse(status_code, json_data, content, headers)
    
    return _create_mock_response
# The following fixtures were moved to tests/fixtures/models.py
# Keeping this comment as a reference for anyone looking at git history

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
            "test_model_1": {"id": "test_model_1", "config_file": "models/test_model_1.yaml"},
            "test_model_2": {"id": "test_model_2", "config_file": "models/test_model_2.yaml"},
        },
    }


@pytest.fixture
def test_model_config_1():
    """Create a test model configuration."""
    return {
        "id": "test_model_1",
        "name": "Test Model",
        "endpoint_url": "http://localhost:8888/predict",
        "active": True,
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
    return Orchestrator(config_dir="config/models")


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
