import pytest
from pydantic import ValidationError

from app.core.models import (
    ModelConfig, 
    CircuitBreakerSettings,
    AuthConfig,
    CacheConfig,
    RequestContext
)


def test_model_config_validation():
    """Test ModelConfig validation."""
    # Test with minimal required fields
    minimal_config = ModelConfig(
        id="test_model",
        endpoint_url="http://example.com"
    )
    
    assert minimal_config.id == "test_model"
    assert minimal_config.endpoint_url == "http://example.com"
    assert minimal_config.name == "test_model"  # Default to ID
    assert minimal_config.version == "1.0.0"  # Default version
    
    # Test with invalid endpoint URL
    with pytest.raises(ValidationError):
        ModelConfig(
            id="test_model",
            endpoint_url="not-a-url"
        )


def test_circuit_breaker_config():
    """Test CircuitBreakerConfig validation."""
    # Test with defaults
    cb_config = CircuitBreakerConfig()
    
    assert cb_config.failure_threshold == 5
    assert cb_config.reset_timeout == 30.0
    assert cb_config.exclude_exceptions == []
    
    # Test with custom values
    custom_cb = CircuitBreakerConfig(
        failure_threshold=10,
        reset_timeout=60.0,
        exclude_exceptions=["ConnectionError"]
    )
    
    assert custom_cb.failure_threshold == 10
    assert custom_cb.reset_timeout == 60.0
    assert custom_cb.exclude_exceptions == ["ConnectionError"]


def test_auth_config():
    """Test AuthConfig validation."""
    # Test API key auth
    api_key_auth = AuthConfig(
        type="api_key",
        key_name="X-API-Key",
        key_value="test-key",
        location="header"
    )
    
    assert api_key_auth.type == "api_key"
    assert api_key_auth.key_name == "X-API-Key"
    assert api_key_auth.key_value == "test-key"
    assert api_key_auth.location == "header"
    
    # Test basic auth
    basic_auth = AuthConfig(
        type="basic",
        username="user",
        password="pass"
    )
    
    assert basic_auth.type == "basic"
    assert basic_auth.username == "user"
    assert basic_auth.password == "pass"
    
    # Test invalid auth type
    with pytest.raises(ValidationError):
        AuthConfig(
            type="invalid_type"
        )


def test_cache_config():
    """Test CacheConfig validation."""
    # Test with defaults
    cache_config = CacheConfig()
    
    assert cache_config.enabled is False
    assert cache_config.ttl == 300
    assert cache_config.max_size == 100
    
    # Test with custom values
    custom_cache = CacheConfig(
        enabled=True,
        ttl=600,
        max_size=200,
        vary_by_headers=["Content-Type", "Accept"]
    )
    
    assert custom_cache.enabled is True
    assert custom_cache.ttl == 600
    assert custom_cache.max_size == 200
    assert custom_cache.vary_by_headers == ["Content-Type", "Accept"]


def test_model_registry():
    """Test ModelRegistry initialization and operations."""
    registry = ModelRegistry()
    
    # Should start empty
    assert len(registry.models) == 0
    
    # Add a model
    model = ModelConfig(
        id="test_model",
        endpoint_url="http://example.com"
    )
    registry.add_model(model)
    
    # Check model was added
    assert len(registry.models) == 1
    assert "test_model" in registry.models
    assert registry.models["test_model"] == model
    
    # Get model by ID
    retrieved_model = registry.get_model("test_model")
    assert retrieved_model == model
    
    # Get nonexistent model
    assert registry.get_model("nonexistent") is None
    
    # Update model
    updated_model = ModelConfig(
        id="test_model",
        endpoint_url="http://updated.example.com",
        name="Updated Model"
    )
    registry.update_model("test_model", updated_model)
    
    # Check model was updated
    assert registry.get_model("test_model").name == "Updated Model"
    assert registry.get_model("test_model").endpoint_url == "http://updated.example.com"
    
    # Delete model
    registry.delete_model("test_model")
    
    # Check model was deleted
    assert len(registry.models) == 0
    assert registry.get_model("test_model") is None


def test_request_context():
    """Test RequestContext model."""
    context = RequestContext(
        model_id="test_model",
        path_suffix="predict",
        query_params={"param1": "value1"},
        headers={"Content-Type": "application/json"},
        body=b'{"input": "test"}',
        method="POST"
    )
    
    assert context.model_id == "test_model"
    assert context.path_suffix == "predict"
    assert context.query_params == {"param1": "value1"}
    assert context.headers == {"Content-Type": "application/json"}
    assert context.body == b'{"input": "test"}'
    assert context.method == "POST"
