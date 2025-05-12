"""
Application settings configuration.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class BaseAppSettings(BaseSettings):
    """Base application settings with common configuration."""
    
    # Application settings
    APP_NAME: str = Field(default="ML Orchestrator")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=False)
    
    # Server settings
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    WORKERS: int = Field(default=1)
    
    # Config file paths
    CONFIG_DIR: str = Field(default="config")
    MODELS_DIR: str = Field(default="config/models")
    
    # Default service settings
    DEFAULT_TIMEOUT: float = Field(default=30.0)
    DEFAULT_MAX_RETRIES: int = Field(default=3)
    
    # Circuit breaker defaults
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5)
    CIRCUIT_BREAKER_RESET_TIMEOUT: float = Field(default=30.0)
    
    # Admin API settings
    ADMIN_API_ENABLED: bool = Field(default=True)
    ADMIN_API_KEY: Optional[str] = Field(default=None)
    
    # Metrics settings
    METRICS_ENABLED: bool = Field(default=False)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    
    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    @field_validator("PORT")
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    @field_validator("WORKERS")
    def validate_workers(cls, v: int) -> int:
        """Validate number of workers."""
        if v < 1:
            raise ValueError("Number of workers must be at least 1")
        return v
    
    @field_validator("DEFAULT_TIMEOUT")
    def validate_timeout(cls, v: float) -> float:
        """Validate default timeout."""
        if v <= 0:
            raise ValueError("Default timeout must be greater than 0")
        return v
    
    @field_validator("DEFAULT_MAX_RETRIES")
    def validate_retries(cls, v: int) -> int:
        """Validate default max retries."""
        if v < 0:
            raise ValueError("Default max retries must be non-negative")
        return v

class DevelopmentSettings(BaseAppSettings):
    """Development environment settings."""
    model_config = SettingsConfigDict(
        env_file="config/env/development.cfg",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

class ProductionSettings(BaseAppSettings):
    """Production environment settings."""
    model_config = SettingsConfigDict(
        env_file="config/env/production.cfg",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

class TestSettings(BaseAppSettings):
    """Test environment settings."""
    model_config = SettingsConfigDict(
        env_file="config/env/test.cfg",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

def get_settings() -> BaseAppSettings:
    """Get the appropriate settings instance based on environment."""
    env = os.getenv("APP_ENV", "development").lower()
    
    settings_map = {
        "development": DevelopmentSettings,
        "production": ProductionSettings,
        "test": TestSettings
    }
    
    settings_class = settings_map.get(env, DevelopmentSettings)
    return settings_class()

# Global settings instance
settings = get_settings() 