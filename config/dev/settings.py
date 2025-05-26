"""Development settings and configuration."""

import os
from typing import List

from app.core.settings.base import AppBaseSettings


class AppSettings(AppBaseSettings):
    """Development settings with debug features but secure for cloud."""

    # Core Settings
    DEBUG: bool = True
    ENVIRONMENT: str = "dev"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALLOWED_HOSTS: List[str] = ["*"]  # Restrict in production
    CORS_ORIGINS: List[str] = ["*"]  # Restrict in production

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

    # Logging
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # API Settings
    API_PREFIX: str = "/api/v1"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"

    # Model Configuration
    MODEL_CONFIG_DIR: str = "/app/config/dev/models"

    # Worker Configuration
    WORKERS: int = 2
    WORKER_CLASS: str = "uvicorn.workers.UvicornWorker"
    WORKER_TIMEOUT: int = 120

    # Development-specific settings
    RELOAD: bool = True
    RELOAD_DIRS: List[str] = ["/app/app"]
    LOG_SQL_QUERIES: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env.dev"


settings = AppSettings()
