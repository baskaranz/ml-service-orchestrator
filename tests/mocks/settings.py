"""Mock settings for tests."""


from pydantic_settings import SettingsConfigDict

from app.config.settings import BaseAppSettings


class TestSettings(BaseAppSettings):
    """Test environment settings."""

    model_config = SettingsConfigDict(
        env_file="config/env/test.cfg",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Test admin API settings
    ADMIN_API_ENABLED: bool = True
    ADMIN_API_KEY: str = "dev-admin-key"


# Initialize settings
settings = TestSettings()


def get_settings() -> BaseAppSettings:
    """Get the global settings instance."""
    return settings
