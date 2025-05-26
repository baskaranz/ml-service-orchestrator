"""
Configuration loader for model configurations.

This module provides utilities to load and manage model configurations
from YAML files in the specified directory.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ModelConfigLoader:
    """Load and manage model configurations from YAML files."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize the config loader with an optional config directory.

        Args:
            config_dir: Directory containing model YAML configurations.
                       Defaults to value of MODEL_CONFIG_DIR environment variable.
        """
        self.config_dir = config_dir or os.getenv("MODEL_CONFIG_DIR", "/app/config/models")
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """Load all YAML configuration files from the config directory."""
        try:
            config_path = Path(self.config_dir)
            if not config_path.exists():
                logger.warning(f"Config directory not found: {self.config_dir}")
                return

            for config_file in config_path.glob("*.yaml"):
                try:
                    with open(config_file, "r") as f:
                        config = yaml.safe_load(f)
                        if config and "id" in config:
                            self._configs[config["id"]] = config
                            logger.debug(f"Loaded config for model: {config['id']}")
                except Exception as e:
                    logger.error(f"Error loading config file {config_file}: {str(e)}")
                    continue

            logger.info(f"Loaded {len(self._configs)} model configurations from {self.config_dir}")

        except Exception as e:
            logger.error(f"Failed to load model configurations: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to load model configurations: {str(e)}"
            )

    def get_config(self, model_id: str) -> Dict[str, Any]:
        """Get configuration for a specific model.

        Args:
            model_id: The ID of the model to get configuration for.

        Returns:
            Dict containing the model configuration.

        Raises:
            HTTPException: If the model configuration is not found.
        """
        config = self._configs.get(model_id)
        if not config:
            raise HTTPException(
                status_code=404, detail=f"Configuration not found for model: {model_id}"
            )
        return config

    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded model configurations.

        Returns:
            Dict mapping model IDs to their configurations.
        """
        return self._configs.copy()

    def refresh(self) -> None:
        """Reload all configurations from disk."""
        self._configs.clear()
        self._load_configs()


# Create a singleton instance
model_config_loader = ModelConfigLoader()
