"""
Global application settings module.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # Application settings
    APP_NAME: str = "ML Orchestrator Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    
    # Config file paths
    CONFIG_DIR: str = os.path.join(os.getcwd(), "config")
    
    # Default service settings
    DEFAULT_TIMEOUT: float = 30.0  # Default timeout in seconds
    DEFAULT_MAX_RETRIES: int = 3   # Default retry count
    
    # Circuit breaker defaults
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RESET_TIMEOUT: float = 30.0  # seconds
    
    # Admin API settings
    ADMIN_API_ENABLED: bool = True
    ADMIN_API_KEY: Optional[str] = None
    
    # Metrics settings
    METRICS_ENABLED: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @field_validator("CONFIG_DIR")
    @classmethod
    def validate_path_exists(cls, value: str, info) -> str:
        """Validate that a path exists or can be created."""
        path = Path(value)
        
        # Get the field name that's being validated
        field_name = info.field_name
        
        # For directory (CONFIG_DIR), create it if it doesn't exist
        if field_name == "CONFIG_DIR" and not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            
        return value
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Initialize settings
settings = AppSettings()