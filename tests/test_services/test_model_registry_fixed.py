"""Tests for the model registry service."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.core.exceptions import ModelNotFoundError
from app.models.config_models import ModelConfig, ModelRegistry, PlatformConfig
from app.services.model_registry import ModelRegistryService


# Mock the ModelConfigManager class to avoid file system operations
class MockModelConfigManager:
    def __init__(self, config_dir: str = "config/models"):
        self.config_dir = config_dir
        self.models = {}
        self.registry = None
        self.platform_config = PlatformConfig()

    async def load_configs(self):
        self.registry = ModelRegistry(
            name="Test Registry", description="Test registry for unit tests", models=self.models
        )
        return self.registry, self.models

    def get_model_config(self, model_id: str):
        if model_id in self.models:
            return self.models[model_id]
        raise ModelNotFoundError(f"Model {model_id} not found")

    async def update_platform_config(self, config: PlatformConfig):
        self.platform_config = config
        return config

    async def get_platform_config(self):
        return self.platform_config

    async def update_model_config(self, model_id: str, model_config: ModelConfig):
        if model_id not in self.models:
            raise ModelNotFoundError(f"Model {model_id} not found")
        self.models[model_id] = model_config
        return model_config


# Mock the ModelRegistry class
class MockModelRegistry:
    def __init__(self, name: str = "", description: str = "", models: dict = None):
        self.name = name
        self.description = description
        self.models = models or {}

    def dict(self):
        return {"name": self.name, "description": self.description, "models": self.models}


@pytest.fixture
def test_model():
    """Create a test model configuration."""
    return ModelConfig(
        id="test_model_1",
        name="Test Model",
        endpoint_url="http://test-model:8000/predict",
        active=True,
        platform=PlatformConfig(
            timeout=30.0,
            max_retries=3,
            health_check={
                "interval": 60,
                "timeout": 10,
                "failure_threshold": 5,
                "success_threshold": 3,
            },
            circuit_breaker={
                "failure_threshold": 10,
                "reset_timeout": 60.0,
                "half_open_timeout": 60.0,
                "success_threshold": 4,
            },
        ),
    )


@pytest.fixture
def mock_model_config():
    """Create a mock model config."""
    return ModelConfig(
        id="test_model_1", name="Test Model 1", endpoint_url="http://test1.com/predict", active=True
    )


@pytest.fixture
async def started_registry():
    """Create and start a model registry service."""
    # Create a service with mocks
    with (
        patch("app.services.model_registry.ModelConfigManager") as mock_config_manager_cls,
        patch("app.services.model_registry.ModelRegistry") as mock_registry_cls,
    ):

        # Set up mocks
        mock_config_manager = AsyncMock()
        mock_registry = AsyncMock()

        # Configure the mocks
        mock_config_manager_cls.return_value = mock_config_manager
        mock_registry_cls.return_value = mock_registry

        # Set up test data
        test_registry_data = {
            "name": "Test Registry",
            "description": "Test registry for unit tests",
        }

        test_models = {
            "test_model_1": ModelConfig(
                id="test_model_1",
                name="Test Model 1",
                endpoint_url="http://test_model_1:8000",
                active=True,
            ),
            "test_model_2": ModelConfig(
                id="test_model_2",
                name="Test Model 2",
                endpoint_url="http://test_model_2:8000",
                active=False,
            ),
        }

        # Configure the mocks
        async def mock_load_configs():
            return test_registry_data, test_models

        mock_config_manager.load_configs = mock_load_configs

        # Create and start the service
        service = ModelRegistryService()
        await service.startup()

        # Add test models to the registry
        for model_id, model in test_models.items():
            service.registry.models[model_id] = model

        yield service

        # Clean up
        await service.shutdown()


@pytest.mark.asyncio
async def test_model_registry_startup():
    """Test starting the model registry service."""
    # Create a service with mocks
    with (
        patch("app.services.model_registry.ModelConfigManager") as mock_config_manager_cls,
        patch("app.services.model_registry.ModelRegistry") as mock_registry_cls,
    ):

        # Set up mocks
        mock_config_manager = AsyncMock()
        mock_registry = AsyncMock()

        # Configure the mocks
        mock_config_manager_cls.return_value = mock_config_manager
        mock_registry_cls.return_value = mock_registry

        # Set up test data
        test_registry_data = {
            "name": "Test Registry",
            "description": "Test registry for unit tests",
        }

        test_models = {
            "test_model_1": ModelConfig(
                id="test_model_1",
                name="Test Model 1",
                endpoint_url="http://test_model_1:8000",
                active=True,
            )
        }

        # Configure the mocks
        async def mock_load_configs():
            return test_registry_data, test_models

        mock_config_manager.load_configs = mock_load_configs

        # Create and start the service
        service = ModelRegistryService()
        await service.startup()

        # Verify the service was started
        assert hasattr(service, "registry")
        assert hasattr(service, "config_manager")

        # Clean up
        await service.shutdown()


@pytest.mark.asyncio
async def test_platform_config():
    """Test platform configuration functionality."""
    # Create a service with mocks
    with (
        patch("app.services.model_registry.ModelConfigManager") as mock_config_manager_cls,
        patch("app.services.model_registry.ModelRegistry") as mock_registry_cls,
    ):

        # Set up mocks
        mock_config_manager = AsyncMock()
        mock_registry = AsyncMock()

        # Configure the mocks
        mock_config_manager_cls.return_value = mock_config_manager
        mock_registry_cls.return_value = mock_registry

        # Set up test data
        test_registry_data = {
            "name": "Test Registry",
            "description": "Test registry for unit tests",
        }

        test_models = {}

        # Configure the mocks
        async def mock_load_configs():
            return test_registry_data, test_models

        mock_config_manager.load_configs = mock_load_configs

        # Mock platform config methods
        test_platform_config = PlatformConfig(
            timeout=30.0,
            max_retries=3,
            health_check={
                "interval": 60,
                "timeout": 10,
                "failure_threshold": 5,
                "success_threshold": 3,
            },
            circuit_breaker={
                "failure_threshold": 10,
                "reset_timeout": 60.0,
                "half_open_timeout": 60.0,
                "success_threshold": 4,
            },
        )

        async def mock_get_platform_config():
            return test_platform_config

        async def mock_update_platform_config(config):
            nonlocal test_platform_config
            test_platform_config = config
            return config

        mock_config_manager.get_platform_config = mock_get_platform_config
        mock_config_manager.update_platform_config = mock_update_platform_config

        # Create and start the service
        service = ModelRegistryService()
        await service.startup()

        # Test getting platform config
        config = await service.get_platform_config()
        assert config.timeout == 30.0
        assert config.max_retries == 3

        # Test updating platform config
        new_config = PlatformConfig(
            timeout=60.0,
            max_retries=5,
            health_check={
                "interval": 30,
                "timeout": 5,
                "failure_threshold": 3,
                "success_threshold": 2,
            },
            circuit_breaker={
                "failure_threshold": 5,
                "reset_timeout": 30.0,
                "half_open_timeout": 30.0,
                "success_threshold": 2,
            },
        )

        updated_config = await service.update_platform_config(new_config)
        assert updated_config.timeout == 60.0
        assert updated_config.max_retries == 5

        # Verify the config was updated
        current_config = await service.get_platform_config()
        assert current_config.timeout == 60.0
        assert current_config.max_retries == 5
        assert current_config.health_check.interval == 30
        assert current_config.health_check.timeout == 5
        assert current_config.health_check.failure_threshold == 3
        assert current_config.health_check.success_threshold == 2
        assert current_config.circuit_breaker.failure_threshold == 5
        assert current_config.circuit_breaker.reset_timeout == 30.0
        assert current_config.circuit_breaker.half_open_timeout == 30.0
        assert current_config.circuit_breaker.success_threshold == 2

        # Clean up
        await service.shutdown()


@pytest_asyncio.fixture
async def model_registry_service(test_model):
    """Create a model registry service with test data."""
    # Create a mock config manager with test data
    config_manager = MockModelConfigManager()
    config_manager.models["test_model_1"] = test_model

    # Create the service with the mock config manager
    service = ModelRegistryService()
    service.config_manager = config_manager
    service.registry = MockModelRegistry(
        name="Test Registry",
        description="Test registry for unit tests",
        models={"test_model_1": test_model},
    )

    # Start the service
    await service.startup()

    yield service

    # Clean up
    await service.shutdown()


@pytest.mark.asyncio
async def test_model_registry_startup(model_registry_service):
    """Test that the model registry starts up correctly."""
    service = model_registry_service

    # Verify the service was initialized correctly
    assert service is not None
    assert service.config_manager is not None
    assert service.registry is not None
    assert "test_model_1" in service.config_manager.models

    # Test getting a model (synchronous call)
    model = service.get_model("test_model_1")
    assert model is not None
    assert model.id == "test_model_1"
    assert model.name == "Test Model"


@pytest.mark.asyncio
async def test_get_model_config(model_registry_service):
    """Test getting a model configuration."""
    service = model_registry_service

    # Test getting an existing model (synchronous call)
    model = service.get_model("test_model_1")
    assert model is not None
    assert model.id == "test_model_1"
    assert model.name == "Test Model"

    # Test getting a non-existent model (synchronous call)
    with pytest.raises(ModelNotFoundError):
        service.get_model("non_existent_model")


@pytest.mark.asyncio
async def test_platform_config(model_registry_service):
    """Test platform configuration functionality."""
    service = model_registry_service

    # Set up platform config
    platform_config = PlatformConfig(timeout=30.0, max_retries=3)
    service.config_manager.platform_config = platform_config

    # Test getting platform config
    config = await service.get_platform_config()
    assert isinstance(config, PlatformConfig)
    assert config.timeout == 30.0
    assert config.max_retries == 3

    # Test updating platform config
    new_config = PlatformConfig(
        timeout=60.0,
        max_retries=5,
        health_check={
            "interval": 60,
            "timeout": 10,
            "failure_threshold": 5,
            "success_threshold": 3,
        },
        circuit_breaker={
            "failure_threshold": 10,
            "reset_timeout": 60.0,
            "half_open_timeout": 60.0,
            "success_threshold": 4,
        },
    )

    # Update platform config
    updated_config = await service.update_platform_config(new_config)
    assert updated_config.timeout == 60.0
    assert updated_config.max_retries == 5
