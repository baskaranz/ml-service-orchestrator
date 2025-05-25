"""Service fixtures for testing the ML Service Orchestrator."""

import asyncio
from typing import Dict, List, Optional

import pytest
import pytest_asyncio

from app.models.config_models import ModelConfig
from app.services.orchestrator import Orchestrator
from app.services.proxy import ProxyService
from tests.fixtures.models import model_config_instance, model_configs, multiple_model_configs


@pytest_asyncio.fixture(scope="function")
async def orchestrator_service(model_configs: Dict[str, ModelConfig]):
    """Create an orchestrator service instance for testing.

    Args:
        model_configs: Dictionary of model configurations

    Returns:
        An initialized Orchestrator instance
    """
    # Create the orchestrator with the provided model configs
    orchestrator = Orchestrator()

    # Initialize the orchestrator with the model configs
    for model_id, config in model_configs.items():
        orchestrator.register_model(config)

    # Yield the orchestrator for testing
    yield orchestrator

    # Clean up
    await orchestrator.shutdown()


@pytest_asyncio.fixture(scope="function")
async def proxy_service(model_config_instance: ModelConfig):
    """Create a proxy service instance for testing.

    Args:
        model_config_instance: A model configuration

    Returns:
        An initialized ProxyService instance
    """
    # Create and initialize the proxy service
    proxy = ProxyService()

    # Yield the proxy for testing
    yield proxy

    # Clean up
    await proxy.close()
