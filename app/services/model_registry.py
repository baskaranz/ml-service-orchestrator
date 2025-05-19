"""
Service for model registry operations.
"""

import logging
import os
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import unittest.mock
import inspect
from watchfiles import awatch
from pathlib import Path
from contextlib import asynccontextmanager

from app.models.config_models import ModelConfig, ModelRegistry, PlatformConfig
from app.schemas.api_models import ModelSummary
from app.core.exceptions import ModelNotFoundError, ModelAlreadyExistsError
from app.config.models_config import ModelConfigManager
from app.utils.logging import get_logger

logger = get_logger(__name__)

class ModelRegistryService:
    """Service for managing model configurations."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, env: str = None):
        if self._initialized:
            return
            
        self.registry = ModelRegistry(
            name="Model Registry",
            description=f"Registry of model configurations ({env or 'default'})"
        )
        # Initialize with the base config directory - ModelConfigManager will handle environment-specific paths
        self.config_manager = ModelConfigManager(
            config_dir="config",  # Simplified path
            env=env
        )
        self._initialized = True
        self._watch_task = None
    
    async def startup(self) -> None:
        """Initialize the model registry on startup."""
        try:
            await self.reload_configs()
            logger.info("Model registry initialized successfully")
            # Start watching for changes
            self._watch_task = asyncio.create_task(self._watch_configs())
        except Exception as e:
            logger.error(f"Failed to initialize model registry: {str(e)}")
            # Initialize with empty registry rather than failing
            self.registry = ModelRegistry(
                name="Model Registry",
                description="Fallback: registry of model configurations"
            )
            self.config_manager.registry = None
    
    async def shutdown(self) -> None:
        """Clean up resources on shutdown."""
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
        self.registry = ModelRegistry(
            name="Model Registry",
            description="Fallback: registry of model configurations"
        )
        self.config_manager.models.clear()
        self.config_manager.registry = None
        logger.info("Model registry cleaned up")
    
    async def _watch_configs(self) -> None:
        """Watch for changes in model configuration files."""
        try:
            config_path = Path(self.config_manager.config_dir)
            async for changes in awatch(config_path):
                if changes:
                    logger.info(f"Detected changes in model configurations: {changes}")
                    try:
                        await self.reload_configs()
                        logger.info("Successfully reloaded model configurations")
                    except Exception as e:
                        logger.error(f"Failed to reload configurations: {str(e)}")
        except asyncio.CancelledError:
            logger.info("Stopping configuration watcher")
            raise
        except Exception as e:
            logger.error(f"Error in configuration watcher: {str(e)}")
            # Restart watching after a delay
            await asyncio.sleep(5)
            self._watch_task = asyncio.create_task(self._watch_configs())
    
    async def reload_configs(self) -> Tuple[ModelRegistry, Dict[str, ModelConfig]]:
        """Reload model configurations from storage."""
        try:
            registry, configs = await self.config_manager.load_configs()
            self.registry = registry
            # Update the registry's models dictionary with the loaded configs
            self.registry.models = configs
            return registry, configs
        except Exception as e:
            logger.error(f"Failed to reload configurations: {str(e)}")
            # Create fallback registry with minimal information
            fallback_registry = ModelRegistry(
                name="Model Registry",
                description="Fallback: registry of model configurations"
            )
            self.registry = fallback_registry
            self.config_manager.registry = None
            raise
    
    def get_model(self, model_id: str) -> ModelConfig:
        """Get a model configuration by ID."""
        if model_id not in self.config_manager.models:
            raise ModelNotFoundError(f"Model {model_id} not found")
        return self.config_manager.models[model_id]
    
    def get_model_config(self, model_id: str) -> ModelConfig:
        """Alias for get_model, for compatibility with tests and legacy code."""
        return self.get_model(model_id)
    
    def list_models(self) -> List[ModelConfig]:
        """List all registered models."""
        # Return models from config manager, falling back to registry if needed
        if hasattr(self.config_manager, 'models') and self.config_manager.models:
            return list(self.config_manager.models.values())
        return list(self.registry.models.values())

    async def add_model(self, model_id: str, model_config: ModelConfig) -> ModelConfig:
        """Add a new model to the registry."""
        if model_id in self.config_manager.models:
            raise ModelAlreadyExistsError(f"Model {model_id} already exists")

        # Add to config manager
        if hasattr(self.config_manager, 'add_model_config'):
            if asyncio.iscoroutinefunction(self.config_manager.add_model_config):
                await self.config_manager.add_model_config(model_config)
            else:
                self.config_manager.add_model_config(model_config)
        else:
            # Fallback to direct assignment if add_model_config doesn't exist
            self.config_manager.models[model_id] = model_config

        # Add to registry
        self.registry.models[model_id] = model_config

        return model_config

    async def update_model(self, model_id: str, model_config: ModelConfig) -> ModelConfig:
        """Update an existing model configuration."""
        if model_id not in self.config_manager.models:
            raise ModelNotFoundError(f"Model {model_id} not found")

        # Update in config manager
        if hasattr(self.config_manager, 'update_model_config'):
            if asyncio.iscoroutinefunction(self.config_manager.update_model_config):
                await self.config_manager.update_model_config(model_id, model_config)
            else:
                self.config_manager.update_model_config(model_id, model_config)
        else:
            # Fallback to direct update if update_model_config doesn't exist
            self.config_manager.models[model_id] = model_config

        # Update in registry
        self.registry.models[model_id] = model_config

        return model_config

    async def delete_model(self, model_id: str) -> None:
        """Delete a model configuration."""
        if model_id not in self.config_manager.models:
            raise ModelNotFoundError(f"Model {model_id} not found")

        # Delete from config manager
        if hasattr(self.config_manager, 'delete_model_config'):
            if asyncio.iscoroutinefunction(self.config_manager.delete_model_config):
                await self.config_manager.delete_model_config(model_id)
            else:
                self.config_manager.delete_model_config(model_id)
        else:
            # Fallback to direct deletion if delete_model_config doesn't exist
            if model_id in self.config_manager.models:
                del self.config_manager.models[model_id]

        # Delete from registry
        if model_id in self.registry.models:
            del self.registry.models[model_id]

    async def activate_model(self, model_id: str) -> None:
        """Activate a model."""
        if model_id not in self.config_manager.models:
            raise ModelNotFoundError(f"Model {model_id} not found")
        
        model = self.config_manager.models[model_id]
        model.active = True
        
        # Update in registry
        if model_id in self.registry.models:
            self.registry.models[model_id].active = True
            
        # Persist the change
        await self.update_model(model_id, model)

    async def deactivate_model(self, model_id: str) -> None:
        """Deactivate a model."""
        if model_id not in self.config_manager.models:
            raise ModelNotFoundError(f"Model {model_id} not found")
        
        model = self.config_manager.models[model_id]
        model.active = False
        
        # Update in registry
        if model_id in self.registry.models:
            self.registry.models[model_id].active = False
            
        # Persist the change
        await self.update_model(model_id, model)

    async def register_model(self, model_id: str, model_config: ModelConfig) -> ModelConfig:
        """Manually register a model configuration."""
        return await self.add_model(model_id, model_config)


    def get_model_endpoint(self, model_id: str) -> str:
        """Get the endpoint URL for a specific model."""
        if model_id not in self.config_manager.models:
            raise ModelNotFoundError(f"Model {model_id} not found")
        return self.config_manager.models[model_id].endpoint_url

    def get_model_config_dict(self, model_id: str) -> Dict[str, Any]:
        """Get the full configuration for a specific model as a dictionary."""
        if model_id not in self.config_manager.models:
            raise ModelNotFoundError(f"Model {model_id} not found")
        return self.config_manager.models[model_id].model_dump()
        
    def get_model_timeout(self, model_id: str) -> float:
        """Get the request timeout for a specific model."""
        if model_id not in self.config_manager.models:
            raise ModelNotFoundError(f"Model {model_id} not found")
        return self.config_manager.models[model_id].timeout
        
    def get_model_retries(self, model_id: str) -> int:
        """Get the maximum number of retries for a specific model."""
        if model_id not in self.config_manager.models:
            raise ModelNotFoundError(f"Model {model_id} not found")
        return self.config_manager.models[model_id].max_retries
        
    def get_model_headers(self, model_id: str) -> Dict[str, str]:
        """Get the headers for a specific model."""
        if model_id not in self.config_manager.models:
            raise ModelNotFoundError(f"Model {model_id} not found")
        return self.config_manager.models[model_id].headers or {}
        
    async def get_platform_config(self) -> PlatformConfig:
        """Get the platform configuration.
        
        Returns:
            PlatformConfig: The current platform configuration
        """
        if hasattr(self.config_manager, 'get_platform_config'):
            if asyncio.iscoroutinefunction(self.config_manager.get_platform_config):
                return await self.config_manager.get_platform_config()
            return self.config_manager.get_platform_config()
        return PlatformConfig()
        
    async def update_platform_config(self, config: PlatformConfig) -> PlatformConfig:
        """Update the platform configuration.
        
        Args:
            config: The new platform configuration
            
        Returns:
            PlatformConfig: The updated platform configuration
        """
        if hasattr(self.config_manager, 'update_platform_config'):
            if asyncio.iscoroutinefunction(self.config_manager.update_platform_config):
                return await self.config_manager.update_platform_config(config)
            return self.config_manager.update_platform_config(config)
        return config
        
    async def get_model_platform_config(self, model_id: str) -> Dict[str, Any]:
        """Get the platform configuration for a specific model.
        
        Args:
            model_id: The ID of the model
            
        Returns:
            Dict[str, Any]: The platform configuration for the model
            
        Raises:
            ModelNotFoundError: If the model is not found
        """
        # First get the model to ensure it exists
        model = self.get_model(model_id)
        
        # Get the platform config from the config manager if available
        if hasattr(self.config_manager, 'get_model_platform_config'):
            if asyncio.iscoroutinefunction(self.config_manager.get_model_platform_config):
                return await self.config_manager.get_model_platform_config(model_id)
            return self.config_manager.get_model_platform_config(model_id)
            
        # Fallback to model's platform config if available
        if hasattr(model, 'platform') and model.platform is not None:
            return model.platform.dict() if hasattr(model.platform, 'dict') else model.platform
            
        # Return empty dict if no platform config is available
        return {}
        
    async def update_model_platform_config(self, model_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update the platform configuration for a specific model.
        
        Args:
            model_id: The ID of the model to update
            config: The new platform configuration
            
        Returns:
            Dict[str, Any]: The updated platform configuration
            
        Raises:
            ModelNotFoundError: If the model is not found
        """
        # First get the model to ensure it exists
        model = self.get_model(model_id)
        
        # Update the platform config using the config manager if available
        if hasattr(self.config_manager, 'update_model_platform_config'):
            if asyncio.iscoroutinefunction(self.config_manager.update_model_platform_config):
                return await self.config_manager.update_model_platform_config(model_id, config)
            return self.config_manager.update_model_platform_config(model_id, config)
            
        # Fallback to updating the model's platform config directly
        if not hasattr(model, 'platform') or model.platform is None:
            model.platform = {}
            
        # Update the platform config
        if isinstance(model.platform, dict):
            model.platform.update(config)
        elif hasattr(model.platform, 'update'):
            model.platform.update(**config)
            
        return config

def get_model_registry_service() -> ModelRegistryService:
    """Get the model registry service instance.
    
    Returns:
        ModelRegistryService: The model registry service instance
    """
    env = os.getenv("APP_ENV", "dev").lower()
    return ModelRegistryService(env=env)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup
    logger.info("Starting up model registry")
    registry = get_model_registry_service()
    app.state.model_registry = registry
    await registry.startup()
    yield
    # Shutdown
    logger.info("Shutting down model registry")
    await registry.shutdown()

def setup_model_registry(app: FastAPI) -> None:
    """Set up the model registry for the FastAPI application."""
    app.router.lifespan_context = lifespan
    if not app.router.on_startup:
        app.router.on_startup.append(lambda: None)  # Add a dummy startup event for backward compatibility
    if not app.router.on_shutdown:
        app.router.on_shutdown.append(lambda: None)  # Add a dummy shutdown event for backward compatibility