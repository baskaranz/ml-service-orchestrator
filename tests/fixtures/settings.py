"""Settings fixtures for testing the ML Service Orchestrator."""

import os
from typing import Any, Dict

import pytest

from app.config.settings import settings as app_settings


@pytest.fixture(scope="session")
def test_env():
    """Set up the test environment.

    This fixture ensures that the APP_ENV is set to 'test' for all tests.

    Returns:
        The current APP_ENV value
    """
    original_env = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "test"
    yield "test"

    # Restore original environment if it existed
    if original_env is not None:
        os.environ["APP_ENV"] = original_env
    else:
        del os.environ["APP_ENV"]


@pytest.fixture(scope="function")
def mock_settings(test_env):
    """Create mock settings for testing.

    Args:
        test_env: The test environment fixture

    Returns:
        The application settings configured for testing
    """
    # Ensure we're using test settings
    assert os.environ.get("APP_ENV") == "test"

    # Return the app settings
    return app_settings


@pytest.fixture(scope="function")
def override_settings():
    """Create a context for temporarily overriding settings.

    This fixture allows tests to temporarily modify settings and have them
    automatically restored after the test completes.

    Yields:
        A function that can be used to override settings
    """
    original_values: Dict[str, Any] = {}

    def _override_settings(**kwargs):
        """Override settings with the provided values.

        Args:
            **kwargs: Settings to override as keyword arguments
        """
        for key, value in kwargs.items():
            if hasattr(app_settings, key):
                original_values[key] = getattr(app_settings, key)
                setattr(app_settings, key, value)
            else:
                raise AttributeError(f"Setting '{key}' does not exist")

    yield _override_settings

    # Restore original values
    for key, value in original_values.items():
        setattr(app_settings, key, value)
