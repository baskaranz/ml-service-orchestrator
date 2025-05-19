"""
Tests for Pydantic models.
"""

import pytest
from pydantic import ValidationError

from app.models.config_models import (
    ModelConfig,
    CircuitBreakerConfig,
    AuthConfig,
    CacheConfig,
    AuthType,
    AuthLocation
)


def test_model_config_validation():
    """Test ModelConfig validation."""
    from app.models.config_models import BasicCircuitBreakerConfig
    # Test with default values
    config = ModelConfig(
        id="test_model_1",
        name="Test Model",
        endpoint_url="http://localhost:8000/predict",
        active=True,
        circuit_breaker=CircuitBreakerConfig(
            basic=BasicCircuitBreakerConfig(
                failure_threshold=5,
                reset_timeout=30.0
            )
        )
    )
    assert config.name == "Test Model"
    assert config.endpoint_url == "http://localhost:8000/predict"
    # Test with custom values
    config2 = ModelConfig(
        id="test_model_2",
        name="Another Model",
        endpoint_url="http://localhost:8001/predict",
        active=False,
        circuit_breaker=CircuitBreakerConfig(
            basic=BasicCircuitBreakerConfig(
                failure_threshold=3,
                reset_timeout=15.0
            )
        )
    )
    assert config2.name == "Another Model"
    assert config2.active is False
    # Test CircuitBreakerConfig validation
    with pytest.raises(ValidationError):
        BasicCircuitBreakerConfig(
            failure_threshold=-1,
            reset_timeout=30.0
        )
    with pytest.raises(ValidationError):
        BasicCircuitBreakerConfig(
            failure_threshold=5,
            reset_timeout=-1.0
        )


def test_circuit_breaker_settings_validation():
    """Test CircuitBreakerSettings validation."""
    from app.models.config_models import BasicCircuitBreakerConfig
    # Test with default values
    default_settings = CircuitBreakerConfig(
        basic=BasicCircuitBreakerConfig(
            failure_threshold=5,
            reset_timeout=30.0
        )
    )
    assert default_settings.basic.failure_threshold == 5
    assert default_settings.basic.reset_timeout == 30.0
    
    # Test with custom values
    custom_settings = CircuitBreakerConfig(
        basic=BasicCircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout=15.0
        )
    )
    assert custom_settings.basic.failure_threshold == 3
    assert custom_settings.basic.reset_timeout == 15.0
    
    # Test with invalid values
    with pytest.raises(ValidationError):
        BasicCircuitBreakerConfig(
            failure_threshold=-1,
            reset_timeout=30.0
        )
    
    with pytest.raises(ValidationError):
        BasicCircuitBreakerConfig(
            failure_threshold=5,
            reset_timeout=-1.0
        )


def test_auth_config_validation():
    """Test AuthConfig validation."""
    # Test API key auth
    api_key_auth = AuthConfig(
        type=AuthType.API_KEY,
        header_name="X-API-Key",
        value="test-key",
        enabled=True
    )
    assert api_key_auth.type == AuthType.API_KEY
    assert api_key_auth.header_name == "X-API-Key"
    assert api_key_auth.value == "test-key"
    
    # Test bearer token auth
    bearer_auth = AuthConfig(
        type=AuthType.BEARER_TOKEN,
        header_name="Authorization",
        value="Bearer test-token",
        enabled=True
    )
    assert bearer_auth.type == AuthType.BEARER_TOKEN
    assert bearer_auth.header_name == "Authorization"
    assert bearer_auth.value == "Bearer test-token"


def test_cache_config_validation():
    """Test CacheConfig validation."""
    # Test with minimal settings
    minimal_cache = CacheConfig(
        enabled=False,
        ttl=300,
        max_size=100,
        vary_by_headers=[]
    )
    assert not minimal_cache.enabled
    assert minimal_cache.ttl == 300
    assert minimal_cache.max_size == 100
    
    # Test with custom settings
    custom_cache = CacheConfig(
        enabled=True,
        ttl=600,
        max_size=200,
        vary_by_headers=["Content-Type", "Accept"]
    )
    assert custom_cache.enabled
    assert custom_cache.ttl == 600
    assert custom_cache.max_size == 200
    assert custom_cache.vary_by_headers == ["Content-Type", "Accept"]


def test_required_arguments_validation():
    """Test validation of required arguments."""
    # Test ModelConfig required fields (all present)
    ModelConfig(
        id="test_model_3",
        name="Test Model",
        endpoint_url="http://localhost:8000/predict"
    )

    # Now test missing id
    with pytest.raises(ValidationError) as exc_info:
        ModelConfig(
            name="Test Model",
            endpoint_url="http://localhost:8000/predict"
        )
    assert "id" in str(exc_info.value)

    # Now test missing endpoint_url
    with pytest.raises(ValidationError) as exc_info:
        ModelConfig(
            id="test_model_4",
            name="Test Model"
        )
    assert "endpoint_url" in str(exc_info.value)


# SKIP: tests that are missing required arguments for the new models
