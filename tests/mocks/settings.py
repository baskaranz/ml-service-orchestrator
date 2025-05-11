"""Mock settings for tests."""

import os
from typing import Dict, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # Application settings
    APP_NAME: str = "Test ML Orchestrator"
    APP_VERSION: str = "test-1.0.0"
    DEBUG: bool = True
    
    # Server settings
    HOST: str = "localhost"
    PORT: int = 8000
    WORKERS: int = 1
    
    # Config file paths
    CONFIG_DIR: str = "/tmp/test_config"
    MODELS_REGISTRY_FILE: str = "/tmp/test_config/models_registry.yaml"
    
    # Default service settings
    DEFAULT_TIMEOUT: float = 30.0  # Default timeout in seconds
    DEFAULT_MAX_RETRIES: int = 3   # Default retry count
    
    # Circuit breaker defaults
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RESET_TIMEOUT: float = 30.0  # seconds
    
    # Admin API settings
    ADMIN_API_ENABLED: bool = True
    ADMIN_API_KEY: Optional[str] = "test-admin-key"
    
    # Metrics settings
    METRICS_ENABLED: bool = False
    
    # Logging
    LOG_LEVEL: str = "ERROR"
    
    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Initialize settings
settings = AppSettings()