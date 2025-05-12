"""
Configuration loading and management for model endpoints.
"""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Iterable
from watchfiles import awatch

import yaml
from fastapi import HTTPException, status
from pydantic import ValidationError, BaseModel, Field

from app.models.config_models import ModelConfig, ModelRegistry
from app.utils.logging import get_logger
from app.core.exceptions import ModelNotFoundError, ModelAlreadyExistsError

logger = get_logger(__name__)

class ModelConfigManager:
    """Manages model configurations."""

    def __init__(self, config_dir: str = "config/models"):
        """Initialize the configuration manager."""
        self.config_dir = config_dir
        self.models: Dict[str, ModelConfig] = {}
        self.registry: Optional[ModelRegistry] = None
        self.last_modified: Dict[str, float] = {}

    def _generate_registry(self) -> ModelRegistry:
        """Generate registry from loaded model configurations."""
        registry_models = {}
        for model_id, model in self.models.items():
            registry_models[model_id] = {
                "id": model.id,
                "name": model.name,
                "description": model.description,
                "version": model.version,
                "endpoint": model.endpoint_url,
                "config_file": f"models/{model.id}.yaml",
                "active": model.active,
                "type": getattr(model, "type", None),
                "metadata": getattr(model, "metadata", {})
            }
        
        return ModelRegistry(
            version="1.0.0",
            name="Model Registry",
            description="Registry of model configurations",
            models=registry_models
        )

    async def load_configs(self) -> Tuple[ModelRegistry, Dict[str, ModelConfig]]:
        """Load all model configurations from the config directory."""
        try:
            config_path = Path(self.config_dir)
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration directory not found: {self.config_dir}")

            self.models.clear()
            
            # Load all model YAMLs
            for file_path in config_path.glob("*.yaml"):
                if file_path.name == "registry.yaml":
                    continue  # Skip registry.yaml as we generate it
                    
                try:
                    model_dict = self._read_yaml_file(file_path)
                    expected_id = file_path.stem
                    if model_dict.get("id") != expected_id:
                        logger.warning(f"Model ID mismatch in {file_path}: expected {expected_id}, got {model_dict.get('id')}")
                        continue
                    
                    model_config = ModelConfig(**model_dict)
                    if model_config.id is None:
                        logger.warning(f"Model ID cannot be None in {file_path}")
                        continue
                        
                    self.models[model_config.id] = model_config
                    self.last_modified[str(file_path)] = file_path.stat().st_mtime
                    
                    logger.info(f"Loaded model configuration for '{model_config.id}'")
                except ValidationError as e:
                    logger.error(f"Failed to validate model configuration in {file_path}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing model configuration in {file_path}: {str(e)}")
                    continue
            
            # Generate registry from loaded models
            self.registry = self._generate_registry()
            
            return self.registry, self.models
            
        except Exception as e:
            logger.error(f"Failed to reload configurations: {str(e)}")
            raise

    def _read_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Read and parse a YAML file."""
        try:
            with open(file_path, "r") as f:
                content = yaml.safe_load(f)
                if content is None:
                    raise ValueError(f"Empty YAML file: {file_path}")
                return content
        except yaml.YAMLError as e:
            logger.error(f"Failed to read YAML file {file_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to read YAML file {file_path}: {str(e)}")
            raise

    def get_model_config(self, model_id: str) -> ModelConfig:
        """Get a model configuration by ID."""
        if model_id not in self.models:
            raise ModelNotFoundError(f"Model not found: {model_id}")
        return self.models[model_id]

    def add_model_config(self, model: ModelConfig) -> None:
        """Add a new model configuration."""
        if model.id is None:
            raise ValueError("Model ID cannot be None")
        if model.id in self.models:
            raise ModelAlreadyExistsError(f"Model already exists: {model.id}")
        self.models[model.id] = model
        self.registry = self._generate_registry()  # Regenerate registry

    def update_model_config(self, model_id: str, model: ModelConfig) -> None:
        """Update an existing model configuration."""
        if model_id not in self.models:
            raise ModelNotFoundError(f"Model not found: {model_id}")
        self.models[model_id] = model
        self.registry = self._generate_registry()  # Regenerate registry

    def delete_model_config(self, model_id: str) -> None:
        """Delete a model configuration."""
        if model_id not in self.models:
            raise ModelNotFoundError(f"Model not found: {model_id}")
        del self.models[model_id]
        self.registry = self._generate_registry()  # Regenerate registry

    def should_reload(self, changed_files: Set[Path]) -> bool:
        """Check if configurations should be reloaded."""
        for file_path in changed_files:
            if not file_path.exists():
                continue
            current_mtime = file_path.stat().st_mtime
            if str(file_path) not in self.last_modified or current_mtime > self.last_modified[str(file_path)]:
                return True
        return False 