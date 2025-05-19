"""Mock settings for tests."""

import os
from typing import Dict, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.settings import BaseAppSettings

class TestSettings(BaseAppSettings):
    """Test environment settings."""
    model_config = SettingsConfigDict(
        env_file="config/env/test.cfg",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Test admin API key
    ADMIN_API_KEY: str = "dev-admin-key"

# Initialize settings
settings = TestSettings()

def get_settings() -> BaseAppSettings:
    """Get the global settings instance."""
    return settings