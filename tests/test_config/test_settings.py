import os
from pathlib import Path
from typing import Optional

import pytest

from app.config.settings import AppSettings


class MockSettings(AppSettings):
    """Mock settings for testing."""
    
    @classmethod
    def validate_path_exists(cls, v: str, field: str) -> str:
        """Override path validation for testing."""
        return v


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    # Override environment variables for testing
    os.environ["APP_NAME"] = "Test ML Orchestrator"
    os.environ["APP_VERSION"] = "test-1.0.0"
    os.environ["CONFIG_DIR"] = "/tmp/test_config"
    os.environ["REGISTRY_FILE"] = "/tmp/test_config/models_registry.yaml"
    os.environ["ADMIN_API_KEY"] = "test-admin-key"
    os.environ["LOG_LEVEL"] = "ERROR"
    
    # Create and return settings
    return MockSettings()


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch, mock_settings):
    """Patch the global settings with mock settings."""
    from app.config import settings as settings_module
    monkeypatch.setattr(settings_module, "settings", mock_settings)
    monkeypatch.setattr(settings_module, "get_settings", lambda: mock_settings)
    return mock_settings
