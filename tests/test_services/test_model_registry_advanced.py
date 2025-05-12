"""Advanced tests for the model registry service."""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import shutil

import pytest
from fastapi import FastAPI

from app.models.config_models import ModelConfig, ModelRegistry, CircuitBreakerConfig, LLMProviderConfig
from app.schemas.api_models import ModelSummary
from app.services.model_registry import ModelRegistryService, setup_model_registry
from app.core.exceptions import ModelAlreadyExistsError


@pytest.fixture
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
        version="1.0.0",
        name="Test Registry",
        description="Test registry for advanced tests",
        models={}
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
        type="huggingface",
        model_name="test-model",
        timeout=30,
        max_retries=3,
        api_key="test-key"
    )


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
    assert service.registry.version == "1.0.0"
    assert "fallback" in service.registry.description.lower()


@pytest.mark.asyncio
async def test_list_models_empty(started_registry):
    """Test listing models when no models exist."""
    service = await anext(started_registry)
    # Ensure models dict is empty and is a real dict
    service.registry = ModelRegistry(
        version="1.0.0",
        name="Test Registry",
        description="Test registry for advanced tests",
        models={}
    )
    service.config_manager.models = {}
    # List models
    models = service.list_models()
    # Verify an empty list is returned
    assert isinstance(models, list)
    assert len(models) == 0


@pytest.mark.asyncio
async def test_reload_configs_empty(started_registry):
    """Test reloading configs when no models are loaded."""
    service = await anext(started_registry)
    
    # Mock the load_configs method to return empty registry and models
    empty_registry = ModelRegistry(
        version="1.0.0",
        name="Test Registry",
        description="Test registry for advanced tests",
        models={}
    )
    empty_models = {}
    
    service.config_manager.load_configs = AsyncMock(return_value=(empty_registry, empty_models))
    
    # Reload configs
    registry, models = await service.reload_configs()
    
    # Verify load_configs was called
    service.config_manager.load_configs.assert_called_once()
    
    # Verify empty registry and models were returned
    assert isinstance(registry, ModelRegistry)
    assert len(registry.models) == 0
    assert isinstance(models, dict)
    assert len(models) == 0


@pytest.mark.asyncio
async def test_list_models_with_transformations(started_registry, llm_provider_config):
    """Test listing models with transformations."""
    service = await anext(started_registry)
    # Clear existing models for isolation and ensure real dicts
    service.registry = ModelRegistry(
        version="1.0.0",
        name="Test Registry",
        description="Test registry for advanced tests",
        models={}
    )
    service.config_manager.models = {}
    # Add a model with transformations
    model = ModelConfig(
        id="test_model",
        name="Test Model",
        description="A test model",
        endpoint_url="http://test.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3,
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=5,
            reset_timeout=30.0
        ),
        llm_provider=llm_provider_config
    )
    service.config_manager.models["test_model"] = model
    # List models
    models = service.list_models()
    # Verify the model was returned with correct fields
    assert len(models) == 1
    assert models[0].id == "test_model"
    assert models[0].name == "Test Model"
    assert models[0].description == "A test model"
    assert models[0].version == "1.0.0"
    assert models[0].active is True


@pytest.mark.asyncio
async def test_add_model(started_registry, llm_provider_config):
    """Test adding a new model."""
    service = await anext(started_registry)
    # Create a new model
    model = ModelConfig(
        id="new_model",
        name="New Model",
        description="A new model",
        endpoint_url="http://new.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3,
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=5,
            reset_timeout=30.0
        ),
        llm_provider=llm_provider_config
    )
    # Add the model
    added_model = await service.add_model("new_model", model)
    # Verify the model was added
    assert added_model.id == "new_model"
    assert "new_model" in service.config_manager.models
    assert service.config_manager.models["new_model"].name == "New Model"


@pytest.mark.asyncio
async def test_add_model_already_exists(started_registry, llm_provider_config):
    """Test adding a model that already exists."""
    service = await anext(started_registry)
    # Create a model
    model = ModelConfig(
        id="existing_model",
        name="Existing Model",
        description="An existing model",
        endpoint_url="http://existing.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3,
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=5,
            reset_timeout=30.0
        ),
        llm_provider=llm_provider_config
    )
    # Add the model
    service.config_manager.models["existing_model"] = model
    service.registry.models["existing_model"] = model
    # Try to add it again
    with pytest.raises(ModelAlreadyExistsError):
        await service.add_model("existing_model", model)


@pytest.mark.asyncio
async def test_get_model_not_found(started_registry):
    """Test getting a model that doesn't exist."""
    service = await anext(started_registry)
    
    # Try to get a non-existent model
    with pytest.raises(Exception):
        service.get_model("nonexistent_model")


@pytest.mark.asyncio
async def test_get_model_found(started_registry, llm_provider_config):
    """Test getting a model that exists."""
    service = await anext(started_registry)
    # Create a model
    model = ModelConfig(
        id="test_model",
        name="Test Model",
        description="A test model",
        endpoint_url="http://test.com",
        version="1.0.0",
        active=True,
        timeout=30.0,
        max_retries=3,
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=5,
            reset_timeout=30.0
        ),
        llm_provider=llm_provider_config
    )
    # Add the model
    service.config_manager.models["test_model"] = model
    # Get the model
    retrieved_model = service.get_model("test_model")
    # Verify the model was retrieved
    assert retrieved_model.id == "test_model"
    assert retrieved_model.name == "Test Model"


@pytest.mark.asyncio
async def test_setup_model_registry_with_app_context():
    """Test setup_model_registry preserves existing app events."""
    # Create a FastAPI app with existing event handlers
    app = FastAPI()
    
    # Add existing event handlers
    existing_startup_called = False
    existing_shutdown_called = False
    
    @app.on_event("startup")
    async def existing_startup():
        nonlocal existing_startup_called
        existing_startup_called = True
    
    @app.on_event("shutdown")
    async def existing_shutdown():
        nonlocal existing_shutdown_called
        existing_shutdown_called = True
    
    # Mock the necessary classes and methods
    with patch("app.services.model_registry.ModelRegistryService") as mock_service_cls, \
         patch("app.services.model_registry.ModelConfigManager") as mock_manager_cls:
        
        # Mock service methods
        mock_service = mock_service_cls.return_value
        mock_service.startup = AsyncMock()
        mock_service.shutdown = AsyncMock()
        
        # Set up the model registry
        setup_model_registry(app)
        
        # Verify our event handler is still present
        assert any(h.__name__ == "existing_startup" for h in app.router.on_startup)
        
        # Trigger all startup events
        for handler in app.router.on_startup:
            await handler()
        
        # Verify both handlers were called
        assert existing_startup_called is True
        mock_service.startup.assert_called_once()
        
        # Reset tracking
        existing_startup_called = False
        mock_service.startup.reset_mock()
        
        # Trigger all shutdown events
        for handler in app.router.on_shutdown:
            await handler()
        
        # Verify both handlers were called
        assert existing_shutdown_called is True
        mock_service.shutdown.assert_called_once()