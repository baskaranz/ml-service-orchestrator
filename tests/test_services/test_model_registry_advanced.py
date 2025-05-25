"""Advanced tests for the model registry service."""

import shutil
import tempfile
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI

from app.core.exceptions import ModelAlreadyExistsError
from app.models.config_models import LLMProviderConfig, ModelConfig, ModelRegistry, PlatformConfig
from app.services.model_registry import (
    ModelRegistryService,
    get_model_registry_service,
    setup_model_registry,
)


@pytest_asyncio.fixture
async def started_registry():
    """Create and start a model registry service with isolated config directory."""
    # Reset the singleton instance
    ModelRegistryService._instance = None

    # Create a temporary directory for configs
    temp_dir = tempfile.mkdtemp()
    service = ModelRegistryService()
    # Patch the config_dir to the temp directory
    service.config_manager.config_dir = temp_dir
    # Mock load_configs to return empty registry and models
    empty_registry = ModelRegistry(
        name="Test Registry", description="Test registry for advanced tests", models={}
    )
    empty_models = {}
    service.config_manager.load_configs = AsyncMock(return_value=(empty_registry, empty_models))
    # Reset the models and registry that might have been set by other tests
    service.registry = empty_registry
    service.config_manager.models = empty_models
    await service.startup()
    yield service
    await service.shutdown()
    shutil.rmtree(temp_dir)


@pytest.fixture
def llm_provider_config() -> LLMProviderConfig:
    """Create a test LLM provider configuration."""
    return LLMProviderConfig(
        type="huggingface", model_name="test-model", timeout=30, max_retries=3, api_key="test-key"
    )


@pytest.fixture
def app():
    """Create a FastAPI application for testing."""
    app = FastAPI()
    setup_model_registry(app)
    return app


@pytest.mark.asyncio
async def test_startup_error_handling():
    """Test error handling during startup."""
    # Create a service
    service = ModelRegistryService()

    # Make load_configs raise an exception
    service.config_manager.load_configs = AsyncMock(side_effect=Exception("Config loading error"))

    # Call startup - should not propagate the exception anymore but handle it gracefully
    await service.startup()

    # Verify that the service was initialized with a fallback registry
    assert "fallback" in service.registry.description.lower()


@pytest.mark.asyncio
async def test_list_models_empty(started_registry):
    """Test listing models when no models exist."""
    # List models
    models = started_registry.list_models()
    # Verify the list is empty
    assert isinstance(models, list)
    assert len(models) == 0


@pytest.mark.asyncio
async def test_reload_configs_empty(started_registry):
    """Test reloading configs when no models are loaded."""
    # Mock the config manager's load_configs method
    empty_registry = ModelRegistry(
        name="Empty Registry", description="Registry with no models", models={}
    )
    empty_models = {}
    started_registry.config_manager.load_configs = AsyncMock(
        return_value=(empty_registry, empty_models)
    )

    # Reload configs
    await started_registry.reload_configs()

    # Verify the registry is empty
    assert len(started_registry.registry.models) == 0
    assert len(started_registry.config_manager.models) == 0

    # Verify the load_configs method was called
    started_registry.config_manager.load_configs.assert_called_once()


@pytest.mark.asyncio
async def test_list_models_with_transformations(started_registry, llm_provider_config):
    """Test listing models with transformations."""
    # Add a model with transformations
    model = ModelConfig(
        id="test_model",
        name="Test Model",
        endpoint_url="http://test.com",
        active=True,
        platform=PlatformConfig(type="huggingface", config=llm_provider_config),
    )
    started_registry.config_manager.models["test_model"] = model

    # List models
    models = started_registry.list_models()

    # Verify the model was returned
    assert len(models) == 1
    assert models[0].id == "test_model"
    assert models[0].name == "Test Model"
    assert models[0].active is True


@pytest.mark.asyncio
async def test_add_model(started_registry, llm_provider_config):
    """Test adding a new model."""
    # Create a model
    model = ModelConfig(
        id="test_model", name="Test Model", endpoint_url="http://test.com", active=True
    )
    # Add the model
    await started_registry.add_model("test_model", model)
    # Verify the model was added
    assert "test_model" in started_registry.config_manager.models
    assert started_registry.config_manager.models["test_model"].name == "Test Model"


@pytest.mark.asyncio
async def test_add_model_already_exists(started_registry, llm_provider_config):
    """Test adding a model that already exists."""
    # Create a model
    model = ModelConfig(
        id="existing_model", name="Existing Model", endpoint_url="http://existing.com", active=True
    )
    # Add the model
    started_registry.config_manager.models["existing_model"] = model
    started_registry.registry.models["existing_model"] = model
    # Try to add it again
    with pytest.raises(ModelAlreadyExistsError):
        await started_registry.add_model("existing_model", model)


@pytest.mark.asyncio
async def test_get_model_not_found(started_registry):
    """Test getting a model that doesn't exist."""
    # Try to get a non-existent model
    with pytest.raises(Exception):
        started_registry.get_model("nonexistent_model")


@pytest.mark.asyncio
async def test_get_model_found(started_registry, llm_provider_config):
    """Test getting a model that exists."""
    # Create a model
    model = ModelConfig(
        id="test_model", name="Test Model", endpoint_url="http://test.com", active=True
    )
    # Add the model
    started_registry.config_manager.models["test_model"] = model
    # Get the model
    retrieved_model = started_registry.get_model("test_model")
    # Verify the model was retrieved
    assert retrieved_model.id == "test_model"
    assert retrieved_model.name == "Test Model"
    assert retrieved_model.active is True


@pytest.mark.asyncio
async def test_setup_model_registry_with_app_context(app):
    """Test setting up model registry with FastAPI application context."""
    # Create a test model config
    model_config = ModelConfig(
        id="test-model", name="Test Model", endpoint_url="http://example.com/model", active=True
    )

    # Get the registry service
    registry = get_model_registry_service()

    # Register the model
    await registry.add_model("test-model", model_config)

    # Verify the model is registered
    assert "test-model" in registry.config_manager.models
    assert registry.config_manager.models["test-model"].id == "test-model"

    # Test the lifespan context manager
    async with app.router.lifespan_context(app):
        # Verify the registry is accessible through app state
        assert hasattr(app.state, "model_registry")
        assert app.state.model_registry is registry

        # Verify the model is still registered
        assert "test-model" in app.state.model_registry.config_manager.models
        assert app.state.model_registry.config_manager.models["test-model"].id == "test-model"

    # Verify the registry is cleared after shutdown
    assert len(registry.config_manager.models) == 0
