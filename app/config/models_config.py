"""
Configuration loading and management for model endpoints.
"""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml
from fastapi import HTTPException, status
from pydantic import ValidationError
from watchfiles import awatch

from app.models.config_models import ModelConfig, ModelRegistry
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ModelConfigManager:
    """
    Manages the loading and reloading of model configurations from YAML files.
    """
    
    def __init__(self, config_dir: str, registry_file: str):
        """
        Initialize the model config manager.
        
        Args:
            config_dir: Directory containing model configuration files
            registry_file: Path to the models registry file
        """
        self.config_dir = Path(config_dir)
        self.registry_file = Path(registry_file)
        self.registry: Optional[ModelRegistry] = None
        self.models: Dict[str, ModelConfig] = {}
        self._watch_task = None
        self._env_pattern = re.compile(r'\${([^:}]+)(?::([^}]+))?}')
    
    async def load_configs(self) -> Tuple[ModelRegistry, Dict[str, ModelConfig]]:
        """
        Load all model configurations and registry.
        
        Returns:
            Tuple of (registry, models dict)
        """
        try:
            # Load the registry file
            registry_content = self._read_yaml_file(self.registry_file)
            
            # Process environment variables in the registry content
            processed_registry = self._process_env_vars(registry_content)
            
            # Parse into the registry model
            registry = ModelRegistry.model_validate(processed_registry)
            self.registry = registry
            
            # Load each model configuration
            models = {}
            for entry in registry.models:
                model_path = self.config_dir / entry.config_file
                try:
                    # Load and process the model config
                    model_content = self._read_yaml_file(model_path)
                    processed_model = self._process_env_vars(model_content)
                    
                    # Parse into the model config
                    model_config = ModelConfig.model_validate(processed_model)
                    
                    # Verify the ID in the file matches the registry ID
                    if model_config.id != entry.id:
                        logger.warning(
                            f"Model ID mismatch: {model_config.id} in file, {entry.id} in registry. "
                            f"Using registry ID."
                        )
                        model_config.id = entry.id
                    
                    models[entry.id] = model_config
                    logger.info(f"Loaded model configuration for '{entry.id}'")
                    
                except FileNotFoundError:
                    logger.error(f"Model configuration file not found: {model_path}")
                except ValidationError as e:
                    logger.error(f"Invalid model configuration for '{entry.id}': {str(e)}")
                except Exception as e:
                    logger.error(f"Error loading model '{entry.id}': {str(e)}")
            
            self.models = models
            return registry, models
            
        except FileNotFoundError:
            logger.error(f"Registry file not found: {self.registry_file}")
            raise
        except ValidationError as e:
            logger.error(f"Invalid registry configuration: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error loading model configurations: {str(e)}")
            raise
    
    def _read_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Read and parse a YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Dictionary containing the YAML content
        """
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _process_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process environment variables in the configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with environment variables replaced
        """
        if isinstance(config, dict):
            return {k: self._process_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._process_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._replace_env_vars(config)
        else:
            return config
    
    def _replace_env_vars(self, value: str) -> str:
        """
        Replace environment variables in a string.
        
        Format: ${ENV_VAR:default_value}
        
        Args:
            value: String possibly containing environment variables
            
        Returns:
            String with environment variables replaced
        """
        def replace(match):
            env_var = match.group(1)
            default = match.group(2) if match.group(2) else None
            return os.environ.get(env_var, default or '')
        
        return self._env_pattern.sub(replace, value)
    
    async def start_watching(self) -> None:
        """
        Start watching for changes in configuration files.
        """
        async for changes in awatch(self.config_dir):
            # Check if any relevant files changed
            changed_files = {Path(changed[1]) for changed in changes}
            if self._should_reload(changed_files):
                logger.info("Configuration files changed, reloading...")
                await self.load_configs()
    
    def _should_reload(self, changed_files: Set[Path]) -> bool:
        """
        Determine if configs should be reloaded based on changed files.
        
        Args:
            changed_files: Set of changed file paths
            
        Returns:
            True if configs should be reloaded, False otherwise
        """
        # Always reload if registry file changed
        if self.registry_file in changed_files:
            return True
        
        # Check if any model config files changed
        if not self.registry:
            return False
            
        for entry in self.registry.models:
            model_path = self.config_dir / entry.config_file
            if model_path in changed_files:
                return True
                
        return False
    
    def get_model_config(self, model_id: str) -> ModelConfig:
        """
        Get a model configuration by ID.
        
        Args:
            model_id: Model ID to retrieve
            
        Returns:
            ModelConfig for the specified ID
            
        Raises:
            HTTPException: If the model is not found
        """
        if model_id not in self.models:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_id}' not found"
            )
            
        return self.models[model_id]
    
    def add_model_config(self, model_config: ModelConfig) -> None:
        """
        Add a new model configuration.
        
        Args:
            model_config: Model configuration to add
            
        Raises:
            HTTPException: If the model already exists
        """
        if model_config.id in self.models:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Model '{model_config.id}' already exists"
            )
            
        # Save to file
        model_file = f"models/{model_config.id}.yaml"
        model_path = self.config_dir / model_file
        
        # Convert to dict and save
        model_dict = model_config.model_dump()
        with open(model_path, 'w') as f:
            yaml.dump(model_dict, f, default_flow_style=False)
        
        # Update registry
        if self.registry:
            self.registry.models.append(ModelRegistry.ModelRegistryEntry(
                id=model_config.id,
                config_file=model_file
            ))
            
            # Save updated registry
            with open(self.registry_file, 'w') as f:
                yaml.dump(self.registry.model_dump(), f, default_flow_style=False)
        
        # Update in-memory model
        self.models[model_config.id] = model_config
    
    def update_model_config(self, model_id: str, model_config: ModelConfig) -> None:
        """
        Update an existing model configuration.
        
        Args:
            model_id: ID of the model to update
            model_config: New model configuration
            
        Raises:
            HTTPException: If the model is not found
        """
        if model_id not in self.models:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_id}' not found"
            )
            
        # Ensure IDs match
        if model_config.id != model_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model ID mismatch: {model_config.id} != {model_id}"
            )
            
        # Find the registry entry
        registry_entry = None
        if self.registry:
            for entry in self.registry.models:
                if entry.id == model_id:
                    registry_entry = entry
                    break
        
        if not registry_entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registry entry for model '{model_id}' not found"
            )
            
        # Save to file
        model_path = self.config_dir / registry_entry.config_file
        
        # Convert to dict and save
        model_dict = model_config.model_dump()
        with open(model_path, 'w') as f:
            yaml.dump(model_dict, f, default_flow_style=False)
        
        # Update in-memory model
        self.models[model_id] = model_config
    
    def delete_model_config(self, model_id: str) -> None:
        """
        Delete a model configuration.
        
        Args:
            model_id: ID of the model to delete
            
        Raises:
            HTTPException: If the model is not found
        """
        if model_id not in self.models:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_id}' not found"
            )
            
        # Find the registry entry
        registry_entry = None
        registry_index = -1
        if self.registry:
            for i, entry in enumerate(self.registry.models):
                if entry.id == model_id:
                    registry_entry = entry
                    registry_index = i
                    break
        
        if not registry_entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registry entry for model '{model_id}' not found"
            )
            
        # Delete the file
        model_path = self.config_dir / registry_entry.config_file
        if model_path.exists():
            model_path.unlink()
        
        # Update registry
        if self.registry and registry_index >= 0:
            self.registry.models.pop(registry_index)
            
            # Save updated registry
            with open(self.registry_file, 'w') as f:
                yaml.dump(self.registry.model_dump(), f, default_flow_style=False)
        
        # Remove from in-memory models
        del self.models[model_id]