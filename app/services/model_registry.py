"""
Service for model registry operations.
"""

import logging
from typing import Dict, List, Optional, Tuple
from fastapi import FastAPI
from pydantic import BaseModel
import unittest.mock
import inspect

from app.models.config_models import ModelConfig, ModelRegistry, ModelRegistryEntry
from app.schemas.api_models import ModelSummary
from app.core.exceptions import ModelNotFoundError
from app.config.models_config import ConfigManager

logger = logging.getLogger(__name__)

class ModelRegistryService:
    """Service for managing model configurations."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.registry = ModelRegistry(
            version="1.0.0",
            name="Model Registry",
            description="Registry of model configurations"
        )
        self.config_manager = ConfigManager(models_dir="config/models")
        self._initialized = True
    
    async def startup(self) -> None:
        """Initialize the model registry on startup."""
        try:
            await self.reload_configs()
            logger.info("Model registry initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize model registry: {str(e)}")
            # Initialize with empty registry rather than failing
            self.registry = ModelRegistry(
                version="1.0.0",
                name="Model Registry",
                description="Registry of model configurations"
            )
            self.config_manager._registry = None
    
    async def shutdown(self) -> None:
        """Clean up resources on shutdown."""
        self.registry = ModelRegistry(
            version="1.0.0",
            name="Model Registry",
            description="Registry of model configurations"
        )
        logger.info("Model registry cleaned up")
    
    async def reload_configs(self) -> Tuple[ModelRegistry, Dict[str, ModelConfig]]:
        """Reload model configurations from storage."""
        try:
            registry, configs = await self.config_manager.load_configs()
            self.registry = registry
            return registry, configs
        except Exception as e:
            logger.error(f"Failed to reload configurations: {str(e)}")
            # Create fallback registry with minimal information
            fallback_registry = ModelRegistry(
                version="1.0.0",
                name="Model Registry",
                description="Registry of model configurations"
            )
            self.registry = fallback_registry
            self.config_manager._registry = None
            raise
    
    def get_model(self, model_id: str) -> ModelConfig:
        """Get a model configuration by ID."""
        if not self.config_manager.registry or model_id not in self.config_manager.registry.models:
            raise ModelNotFoundError(f"Model {model_id} not found")
        return self.config_manager.models[model_id]
    
    def get_model_config(self, model_id: str) -> ModelConfig:
        """Alias for get_model, for compatibility with tests and legacy code."""
        return self.get_model(model_id)
    
    def list_models(self) -> List[ModelSummary]:
        """List all registered models."""
        models = []
        if not self.config_manager.registry:
            return models
            
        for model_id, entry in self.config_manager.registry.models.items():
            try:
                model_config = self.config_manager.models[model_id]
                summary = ModelSummary(
                    id=model_id,
                    name=model_config.name,
                    description=model_config.description,
                    version=model_config.version,
                    active=model_config.active
                )
                models.append(summary)
            except Exception as e:
                logger.error(f"Error creating summary for model {model_id}: {str(e)}")
                continue
                
        return models

def get_model_registry_service() -> ModelRegistryService:
    """Get the model registry service instance."""
    return ModelRegistryService()

def setup_model_registry(app: FastAPI) -> None:
    """Set up the model registry service with the FastAPI application."""
    service = get_model_registry_service()
    
    @app.on_event("startup")
    async def startup():
        await service.startup()
    
    @app.on_event("shutdown")
    async def shutdown():
        await service.shutdown()