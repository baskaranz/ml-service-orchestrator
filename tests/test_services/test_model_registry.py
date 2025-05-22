"""Tests for the model registry service."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.core.exceptions import ModelAlreadyExistsError, ModelNotFoundError
from app.models.config_models import ModelConfig, ModelRegistry, PlatformConfig
from app.services.model_registry import ModelRegistryService


@pytest_asyncio.fixture
async def started_registry():
    """Create and start a model registry service."""
    service = ModelRegistryService()
    await service.startup()

    # Initialize test models
    test_model = ModelConfig(
        id="test_model_1",
        name="Test Model 1",
        description="Test model for unit tests",
        version="1.0.0",
        endpoint_url="http://test_model_1:8000",
        active=True,
    )
    service.config_manager.models["test_model_1"] = test_model
    service.registry.models["test_model_1"] = test_model

    yield service
    await service.shutdown()


@pytest.mark.asyncio
async def test_model_registry_startup():
    """Test starting the model registry service."""
    # Create a service with a mock config manager and registry
    with (
        patch("app.services.model_registry.ModelConfigManager") as mock_config_manager_cls,
        patch("app.services.model_registry.ModelRegistry") as mock_registry_cls,
    ):

        # Create mock instances
        mock_config_manager = AsyncMock()
        mock_registry = AsyncMock()

        # Set up the mocks
        mock_config_manager_cls.return_value = mock_config_manager
        mock_registry_cls.return_value = mock_registry

        # Set up test data
        test_models = {
            "test_model_1": ModelConfig(
                id="test_model_1",
                name="Test Model 1",
                endpoint_url="http://test1.com/predict",
                active=True,
            )
        }

        # Create a proper ModelConfig for the test model
        test_model_config = ModelConfig(
            id="test_model_1",
            name="Test Model 1",
            endpoint_url="http://test1.com/predict",
            active=True,
        )

        # Create the registry with the proper model config
        test_registry_data = ModelRegistry(
            name="Test Registry",
            description="Test registry",
            models={"test_model_1": test_model_config},
        )

        # Configure the mocks
        mock_config_manager.load_configs = AsyncMock(return_value=(test_registry_data, test_models))

        # Create and start the service
        service = ModelRegistryService()

        # Mock the _watch_configs method to avoid background tasks
        async def mock_watch_configs():
            pass

        service._watch_configs = mock_watch_configs

        # Set up the config manager and registry
        service.config_manager = mock_config_manager
        service.registry = mock_registry

        # Start the service
        await service.startup()

        # Verify load_configs was called
        mock_config_manager.load_configs.assert_awaited_once()

        # Test shutdown
        await service.shutdown()

        # Verify cleanup
        assert service.registry is not None
        assert service.config_manager is not None


@pytest.mark.asyncio
async def test_get_model_config():
    """Test getting a model configuration."""
    # Create a test model
    test_model = ModelConfig(
        id="test_model_1", name="Test Model 1", endpoint_url="http://test1.com/predict", active=True
    )

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

        # Set up the test model in the mocks
        mock_config_manager.models = {"test_model_1": test_model}
        mock_config_manager.get_model_config.return_value = test_model

        # Create and start the service
        service = ModelRegistryService()
        service.config_manager = mock_config_manager
        service.registry = mock_registry

        # Test getting an existing model
        model_config = service.get_model_config("test_model_1")

        # Verify the model config
        assert model_config is not None
        assert model_config.id == "test_model_1"
        assert model_config.name == "Test Model 1"
        assert model_config.endpoint_url == "http://test1.com/predict"
        assert model_config.active is True

        # Test with non-existent model
        mock_config_manager.get_model_config.side_effect = ModelNotFoundError("Model not found")
        with pytest.raises(ModelNotFoundError):
            service.get_model_config("non_existent_model")

        # Test with None model_id
        with pytest.raises(ModelNotFoundError):
            service.get_model_config(None)

        # Clean up
        await service.shutdown()


@pytest.mark.asyncio
async def test_list_models(started_registry):
    """Test listing all models."""
    # Add test models to the registry
    test_model_1 = ModelConfig(
        id="test_model_1", name="Test Model 1", endpoint_url="http://test1.com/predict", active=True
    )
    test_model_2 = ModelConfig(
        id="test_model_2", name="Test Model 2", endpoint_url="http://test2.com/predict", active=True
    )

    started_registry.config_manager.models = {
        "test_model_1": test_model_1,
        "test_model_2": test_model_2,
    }

    # List models
    models = started_registry.list_models()

    # Verify the models
    assert isinstance(models, list)
    assert len(models) == 2
    model_ids = [model.id for model in models]
    assert "test_model_1" in model_ids
    assert "test_model_2" in model_ids


@pytest.mark.asyncio
async def test_update_model():
    """Test updating an existing model."""
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

        # Create the service
        service = ModelRegistryService()
        service.config_manager = mock_config_manager
        service.registry = mock_registry

        # Set up test data
        test_model = ModelConfig(
            id="test_model_1",
            name="Test Model 1",
            endpoint_url="http://test1.com/predict",
            active=True,
        )

        updated_model = ModelConfig(
            id="test_model_1",
            name="Updated Test Model",
            endpoint_url="http://updated-test-model.com/predict",
            active=False,
        )

        # Mock the update_model_config method
        mock_config_manager.update_model_config = AsyncMock(return_value=updated_model)
        mock_config_manager.models = {"test_model_1": test_model}
        mock_config_manager.get_model_config = AsyncMock(return_value=test_model)

        # Update the model
        await service.update_model("test_model_1", updated_model)

        # Verify the model was updated
        mock_config_manager.update_model_config.assert_awaited_once_with(
            "test_model_1", updated_model
        )


@pytest.mark.asyncio
async def test_delete_model():
    """Test deleting a model."""
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

        # Set up the test model
        test_model = ModelConfig(
            id="test_model_to_delete",
            name="Test Model To Delete",
            endpoint_url="http://test-delete.com/predict",
            active=True,
        )

        # Set up the test model in the mocks
        mock_config_manager.models = {"test_model_to_delete": test_model}
        mock_config_manager.get_model_config = AsyncMock(return_value=test_model)
        mock_config_manager.delete_model_config = AsyncMock()

        # Mock the registry's delete_model method
        mock_registry.delete_model = AsyncMock()

        # Create and start the service
        service = ModelRegistryService()
        service.config_manager = mock_config_manager
        service.registry = mock_registry

        # Mock the _watch_configs method to avoid background tasks
        async def mock_watch_configs():
            pass

        service._watch_configs = mock_watch_configs

        # Start the service without the watcher
        service._watch_task = None

        # Test deleting an existing model
        await service.delete_model("test_model_to_delete")

        # Verify the delete methods were called
        mock_config_manager.delete_model_config.assert_awaited_once_with("test_model_to_delete")

        # Test with non-existent model
        mock_config_manager.get_model_config.side_effect = ModelNotFoundError("Model not found")
        with pytest.raises(ModelNotFoundError):
            await service.delete_model("non_existent_model")

        # Clean up
        await service.shutdown()


@pytest.mark.asyncio
async def test_activate_model(started_registry):
    """Test activating a model."""
    # Deactivate the model first
    model = started_registry.get_model_config("test_model_1")
    model.active = False
    # Activate the model
    await started_registry.activate_model("test_model_1")
    # Verify the model is active
    assert started_registry.get_model_config("test_model_1").active is True


@pytest.mark.asyncio
async def test_deactivate_model(started_registry):
    """Test deactivating a model."""
    # Deactivate the model
    await started_registry.deactivate_model("test_model_1")
    # Verify the model is inactive
    assert started_registry.get_model_config("test_model_1").active is False


def test_get_model_config_not_found(started_registry):
    """Test getting a model configuration that doesn't exist."""
    # Try to get a model that doesn't exist
    with pytest.raises(Exception):
        started_registry.get_model_config("nonexistent_model")


@pytest.mark.asyncio
async def test_add_model():
    """Test adding a new model."""
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

        # Create the service
        service = ModelRegistryService()
        service.config_manager = mock_config_manager
        service.registry = mock_registry

        # Set up test data
        new_model = ModelConfig(
            id="new_model",
            name="New Model",
            endpoint_url="http://new-model.com/predict",
            active=True,
        )

        # Mock the add_model_config method
        async def mock_add_model_config(config):
            return new_model

        mock_config_manager.add_model_config = AsyncMock(side_effect=mock_add_model_config)
        mock_config_manager.models = {}

        # Add the model
        await service.add_model("new_model", new_model)

        # Verify the model was added
        mock_config_manager.add_model_config.assert_awaited_once_with(new_model)


@pytest.mark.asyncio
async def test_model_not_found(started_registry):
    """Test handling of non-existent model."""
    # Try to get a non-existent model
    with pytest.raises(ModelNotFoundError):
        started_registry.get_model_config("non_existent_model")


@pytest.mark.asyncio
async def test_add_model_duplicate(started_registry):
    """Test adding a model with a duplicate ID."""
    # Try to add a model with an existing ID
    duplicate_model = ModelConfig(
        id="test_model_1", name="Duplicate Model", endpoint_url="http://duplicate:8000", active=True
    )
    with pytest.raises(ModelAlreadyExistsError):
        await started_registry.add_model("test_model_1", duplicate_model)


@pytest.mark.asyncio
async def test_model_update_not_found(started_registry):
    """Test updating non-existent model."""
    # Try to update a non-existent model
    model = ModelConfig(
        id="non_existent_model",
        name="Non Existent Model",
        endpoint_url="http://nonexistent:8000",
        active=True,
    )
    with pytest.raises(ModelNotFoundError):
        await started_registry.update_model("non_existent_model", model)


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

        # Create the service
        service = ModelRegistryService()
        service.config_manager = mock_config_manager
        service.registry = mock_registry

        # Set up platform config
        platform_config = PlatformConfig(timeout=30.0, max_retries=3)
        mock_config_manager.get_platform_config.return_value = platform_config

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

        # Mock the update_platform_config method
        async def mock_update_platform_config(config):
            return new_config

        # Mock the models property
        mock_config_manager.models = {}

        mock_config_manager.update_platform_config = mock_update_platform_config

        # Update the platform config
        updated_config = await service.update_platform_config(new_config)
        assert updated_config.timeout == 60.0
        assert updated_config.max_retries == 5

        # Test model-specific platform config
        model_id = "test_model_platform_config"
        model_config = ModelConfig(
            id=model_id,
            name="Test Model Platform Config",
            endpoint_url="http://test-platform.com/predict",
            active=True,
        )

        # Set up the model in the mocks
        mock_config_manager.models = {model_id: model_config}

        # Mock the get_model_config method
        async def mock_get_model_config(m_id):
            if m_id in mock_config_manager.models:
                return mock_config_manager.models[m_id]
            raise ModelNotFoundError(f"Model {m_id} not found")

        mock_config_manager.get_model_config = mock_get_model_config

        # Mock the get_model_platform_config method
        async def mock_get_model_platform_config(m_id):
            return {"timeout": 60.0, "max_retries": 5}

        mock_config_manager.get_model_platform_config = mock_get_model_platform_config

        # Get model platform config
        model_platform_config = await service.get_model_platform_config(model_id)
        assert model_platform_config["timeout"] == 60.0
        assert model_platform_config["max_retries"] == 5

        # Update model platform config
        new_model_config = {
            "timeout": 45.0,
            "max_retries": 4,
            "health_check": {
                "interval": 30,
                "timeout": 5,
                "failure_threshold": 2,
                "success_threshold": 1,
            },
            "circuit_breaker": {
                "failure_threshold": 3,
                "reset_timeout": 20.0,
                "half_open_timeout": 10.0,
                "success_threshold": 1,
            },
        }

        # Mock the update_model_platform_config method
        mock_config_manager.update_model_platform_config.return_value = {
            **new_model_config,
            "timeout": 45.0,
            "max_retries": 4,
        }

        updated_model_config = await service.update_model_platform_config(
            model_id, new_model_config
        )
        assert updated_model_config["timeout"] == 45.0
        assert updated_model_config["max_retries"] == 4

        # Test non-existent model
        mock_config_manager.get_model_platform_config.side_effect = ModelNotFoundError(
            "Model not found"
        )
        with pytest.raises(ModelNotFoundError):
            await service.get_model_platform_config("non_existent_model")

        mock_config_manager.update_model_platform_config.side_effect = ModelNotFoundError(
            "Model not found"
        )
        with pytest.raises(ModelNotFoundError):
            await service.update_model_platform_config("non_existent_model", new_model_config)
