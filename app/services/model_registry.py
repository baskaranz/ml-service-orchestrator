"""
Service for model registry operations.
"""

import asyncio
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI

from app.config.models_config import ModelConfigManager
from app.config.settings import settings
from app.models.config_models import ModelConfig
from app.schemas.api_models import ModelSummary
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ModelRegistryService:
    """
    Service for managing the model registry.
    """
    
    def __init__(self, config_manager: ModelConfigManager):
        """
        Initialize the model registry service.
        
        Args:
            config_manager: Model configuration manager
        """
        self.config_manager = config_manager
        self._watch_task: Optional[asyncio.Task] = None
    
    async def startup(self) -> None:
        """
        Start the model registry service on application startup.
        """
        logger.info("Starting model registry service")
        
        # Load initial configurations
        await self.config_manager.load_configs()
        
        # Start watching for configuration changes
        self._watch_task = asyncio.create_task(self.config_manager.start_watching())
        
        logger.info("Model registry service started")
    
    async def shutdown(self) -> None:
        """
        Shutdown the model registry service on application shutdown.
        """
        logger.info("Shutting down model registry service")
        
        # Cancel the watch task if it's running
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            
        logger.info("Model registry service shut down")
    
    def get_model_config(self, model_id: str) -> ModelConfig:
        """
        Get a model configuration by ID.
        
        Args:
            model_id: Model ID
            
        Returns:
            Model configuration
        """
        return self.config_manager.get_model_config(model_id)
    
    def list_models(self) -> List[ModelSummary]:
        """
        Get a list of all models.
        
        Returns:
            List of model summaries
        """
        return [
            ModelSummary(
                id=model.id,
                name=model.name,
                description=model.description,
                version=model.version,
                active=model.active
            )
            for model in self.config_manager.models.values()
        ]
    
    def add_model(self, model_config: ModelConfig) -> ModelConfig:
        """
        Add a new model.
        
        Args:
            model_config: Model configuration
            
        Returns:
            Added model configuration
        """
        self.config_manager.add_model_config(model_config)
        return model_config
    
    def update_model(self, model_id: str, model_config: ModelConfig) -> ModelConfig:
        """
        Update an existing model.
        
        Args:
            model_id: Model ID
            model_config: New model configuration
            
        Returns:
            Updated model configuration
        """
        self.config_manager.update_model_config(model_id, model_config)
        return model_config
    
    def delete_model(self, model_id: str) -> None:
        """
        Delete a model.
        
        Args:
            model_id: Model ID
        """
        self.config_manager.delete_model_config(model_id)
    
    async def reload_configs(self) -> Dict[str, ModelConfig]:
        """
        Reload all model configurations.
        
        Returns:
            Dictionary of model configurations
        """
        _, models = await self.config_manager.load_configs()
        return models


def get_model_registry_service(
    config_manager: ModelConfigManager = Depends(lambda: ModelConfigManager(
        config_dir=settings.CONFIG_DIR, 
        registry_file=settings.MODELS_REGISTRY_FILE
    ))
) -> ModelRegistryService:
    """
    Dependency for getting the model registry service.
    
    Args:
        config_manager: Model configuration manager
        
    Returns:
        Model registry service
    """
    return ModelRegistryService(config_manager)


def setup_model_registry(app: FastAPI) -> None:
    """
    Set up the model registry on application startup and shutdown.
    
    Args:
        app: FastAPI application
    """
    # The model registry service is now managed by the lifespan context manager
    # in the main application file, so this function is no longer needed
    pass