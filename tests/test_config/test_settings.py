import os
from pathlib import Path
from typing import Optional

import pytest

from app.config.settings import BaseAppSettings, TestSettings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    # Set test environment
    os.environ["APP_ENV"] = "test"
    
    # Create and return settings
    return TestSettings()


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch, mock_settings):
    """Patch the global settings with mock settings."""
    from app.config import settings as settings_module
    monkeypatch.setattr(settings_module, "settings", mock_settings)
    monkeypatch.setattr(settings_module, "get_settings", lambda: mock_settings)
    return mock_settings
