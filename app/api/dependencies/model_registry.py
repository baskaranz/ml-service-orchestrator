"""
Dependency injection for model registry.
"""

from typing import Generator

from app.services.model_registry import ModelRegistryService, get_model_registry_service


def get_model_registry() -> Generator[ModelRegistryService, None, None]:
    """
    Get the model registry service instance.

    This is a dependency that can be used with FastAPI's Depends() to get
    the model registry service instance.

    Yields:
        ModelRegistryService: The model registry service instance
    """
    registry = get_model_registry_service()
    try:
        yield registry
    finally:
        # Cleanup code if needed
        pass
