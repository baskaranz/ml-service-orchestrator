"""Model-related fixtures for testing the ML Service Orchestrator."""

from typing import Dict, List, Optional

import pytest

from app.models.config_models import ErrorHandlingConfig, ModelConfig, PlatformConfig, RequestConfig


def create_model_config(
    model_id: str = "test_model_1",
    name: str = "Test Model",
    endpoint_url: str = "http://localhost:8888/predict",
    active: bool = True,
    timeout: float = 30.0,
    max_retries: int = 3,
) -> ModelConfig:
    """Factory function to create model configs with different parameters.

    Args:
        model_id: Unique identifier for the model
        name: Display name of the model
        endpoint_url: URL for the model endpoint
        active: Whether the model is active
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts

    Returns:
        A configured ModelConfig instance
    """
    return ModelConfig(
        id=model_id,
        name=name,
        description="A test model for unit tests",
        version="1.0.0",
        endpoint_url=endpoint_url,
        active=active,
        platform=PlatformConfig(
            timeout=timeout,
            max_retries=max_retries,
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
        error_handling=ErrorHandlingConfig(
            retry_policy={
                "max_retries": max_retries,
                "backoff_factor": 0.1,
                "status_codes": [500, 502, 503, 504],
            },
            fallback_strategy="default_response",
        ),
        circuit_breaker={
            "failure_threshold": 5,
            "reset_timeout": 30.0,
            "half_open_timeout": 15.0,
            "success_threshold": 3,
        },
        request=RequestConfig(
            timeout=timeout,
            headers={"Content-Type": "application/json"},
            max_retries=max_retries,
            retry_delay=1.0,
        ),
        health_check={
            "enabled": True,
            "interval": 60,
            "timeout": 10,
            "failure_threshold": 5,
            "success_threshold": 3,
        },
        logging={"level": "INFO", "format": "json"},
        auth={
            "enabled": False,
            "type": "api_key",
            "header_name": "X-API-Key",
            "value": "${API_KEY}",
        },
    )


@pytest.fixture(scope="function")
def model_config_instance() -> ModelConfig:
    """Create a sample model configuration for testing.

    Returns:
        A standard model configuration for testing
    """
    return create_model_config()


@pytest.fixture(scope="function")
def inactive_model_config() -> ModelConfig:
    """Create an inactive model configuration for testing.

    Returns:
        An inactive model configuration
    """
    return create_model_config(model_id="inactive_model", active=False)


@pytest.fixture(scope="function")
def model_configs(model_config_instance: ModelConfig) -> Dict[str, ModelConfig]:
    """Create a dictionary of model configurations for testing.

    Args:
        model_config_instance: The base model configuration

    Returns:
        A dictionary mapping model IDs to their configurations
    """
    return {model_config_instance.id: model_config_instance}


@pytest.fixture(scope="function")
def multiple_model_configs() -> Dict[str, ModelConfig]:
    """Create multiple model configurations for testing.

    Returns:
        A dictionary with multiple model configurations
    """
    return {
        "model1": create_model_config(
            model_id="model1", endpoint_url="http://localhost:8001/predict"
        ),
        "model2": create_model_config(
            model_id="model2", endpoint_url="http://localhost:8002/predict"
        ),
        "inactive_model": create_model_config(model_id="inactive_model", active=False),
    }
