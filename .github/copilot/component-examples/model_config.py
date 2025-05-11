"""
Model configuration system for the ML Orchestrator.

This example demonstrates the model configuration system used in the ML Orchestrator service
for loading, validating, and managing YAML-based model configurations with environment
variable substitution.
"""

import os
import re
import yaml
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from pydantic import BaseModel, Field, validator

# Configuration models

class CircuitBreakerSettings(BaseModel):
    """Settings for circuit breaker pattern."""
    
    failure_threshold: int = Field(
        default=5,
        description="Number of failures before opening the circuit"
    )
    reset_timeout: float = Field(
        default=30.0,
        description="Seconds to wait before attempting to close the circuit"
    )
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "forbid"

class AuthType(str, Enum):
    """Authentication type enum."""
    
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC = "basic"

class AuthConfig(BaseModel):
    """Authentication configuration."""
    
    type: AuthType = Field(default=AuthType.NONE, description="Authentication type")
    key_name: Optional[str] = Field(
        default=None,
        description="Header name for API key authentication"
    )
    key_value: Optional[str] = Field(
        default=None,
        description="API key or token value"
    )
    username: Optional[str] = Field(
        default=None,
        description="Username for basic authentication"
    )
    password: Optional[str] = Field(
        default=None,
        description="Password for basic authentication"
    )
    location: Optional[str] = Field(
        default="header",
        description="Location of the auth data (header, query, etc.)"
    )
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "forbid"
    
    @validator("key_name")
    def validate_key_name(cls, v, values):
        """Validate that key_name is provided for API key auth."""
        if values.get("type") == AuthType.API_KEY and not v:
            raise ValueError("key_name is required for API key authentication")
        return v
    
    @validator("key_value")
    def validate_key_value(cls, v, values):
        """Validate that key_value is provided for API key or bearer token auth."""
        auth_type = values.get("type")
        if auth_type in [AuthType.API_KEY, AuthType.BEARER_TOKEN] and not v:
            raise ValueError(f"key_value is required for {auth_type} authentication")
        return v

class CacheConfig(BaseModel):
    """Configuration for response caching."""
    
    enabled: bool = Field(default=False, description="Whether caching is enabled")
    ttl: int = Field(default=300, description="Time-to-live in seconds")
    max_size: int = Field(default=100, description="Maximum number of cached items")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "forbid"

class ModelConfig(BaseModel):
    """Configuration for a model endpoint."""
    
    id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Display name for the model")
    description: str = Field(default="", description="Description of the model")
    endpoint_url: str = Field(..., description="URL for the model endpoint")
    version: str = Field(default="1.0.0", description="Model version")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    
    # Nested configuration objects
    circuit_breaker: Optional[CircuitBreakerSettings] = Field(
        default=None,
        description="Circuit breaker settings"
    )
    auth: Optional[AuthConfig] = Field(
        default=None,
        description="Authentication configuration"
    )
    cache: Optional[CacheConfig] = Field(
        default=None,
        description="Cache configuration"
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional headers to send with requests"
    )
    active: bool = Field(default=True, description="Whether the model is active")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "forbid"


class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str):
        """Initialize the exception.
        
        Args:
            message: The error message
        """
        self.message = message
        super().__init__(self.message)


class ModelConfigManager:
    """Manager for model configurations.
    
    This class handles loading and managing model configurations from YAML files.
    It supports environment variable substitution in configuration values and
    validates configurations against the ModelConfig schema.
    
    Features:
    - Loading configurations from YAML files
    - Environment variable substitution
    - Hot-reloading configurations when files change
    - Validation of configurations
    """
    
    def __init__(self, config_dir: str, registry_file: str):
        """Initialize the model configuration manager.
        
        Args:
            config_dir: Path to the directory containing model configurations
            registry_file: Path to the model registry file
        """
        self.config_dir = config_dir
        self.registry_file = registry_file
        self._registry: Dict[str, str] = {}  # model_id -> file_path
        self._models: Dict[str, ModelConfig] = {}
    
    def _substitute_env_vars(self, config_str: str) -> str:
        """Substitute environment variables in a configuration string.
        
        Supports the format ${VAR:default} where VAR is the environment variable
        name and default is an optional default value to use if the variable is
        not set.
        
        Args:
            config_str: Configuration string with environment variables
            
        Returns:
            Configuration string with environment variables substituted
        """
        # Use regex pattern to find ${VAR:default} and substitute with env vars
        pattern = r"\${([^:}]+)(?::([^}]+))?}"
        
        def replace_env_var(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) else ""
            return os.environ.get(var_name, default)
        
        return re.sub(pattern, replace_env_var, config_str)
    
    def _validate_config(self, config_dict: Dict, model_id: str) -> ModelConfig:
        """Validate a model configuration.
        
        Args:
            config_dict: Dictionary containing model configuration
            model_id: The model ID for error messages
            
        Returns:
            Validated ModelConfig instance
            
        Raises:
            ConfigurationError: If the configuration is invalid
        """
        try:
            # Ensure ID is set
            config_dict["id"] = model_id
            
            # Validate against ModelConfig
            return ModelConfig(**config_dict)
        except Exception as e:
            raise ConfigurationError(f"Invalid configuration for model {model_id}: {str(e)}")
    
    async def load_registry(self) -> Dict[str, str]:
        """Load the model registry.
        
        Returns:
            Dictionary mapping model IDs to file paths
            
        Raises:
            FileNotFoundError: If the registry file doesn't exist
            ConfigurationError: If the registry file is invalid
        """
        if not os.path.exists(self.registry_file):
            raise FileNotFoundError(f"Registry file not found: {self.registry_file}")
        
        try:
            # Read registry file
            with open(self.registry_file, "r") as f:
                registry_str = f.read()
            
            # Substitute environment variables
            registry_str = self._substitute_env_vars(registry_str)
            
            # Parse YAML
            registry_dict = yaml.safe_load(registry_str)
            
            # Extract model mappings
            models = registry_dict.get("models", [])
            registry = {}
            
            for model in models:
                model_id = model.get("id")
                file_path = model.get("file")
                
                if not model_id or not file_path:
                    continue
                
                registry[model_id] = file_path
            
            self._registry = registry
            return registry
        except Exception as e:
            raise ConfigurationError(f"Failed to load registry file: {str(e)}")
    
    async def load_model_config(self, model_id: str, file_path: str) -> ModelConfig:
        """Load a model configuration from a file.
        
        Args:
            model_id: The model ID
            file_path: The file path relative to config_dir
            
        Returns:
            The model configuration
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ConfigurationError: If the configuration file is invalid
        """
        full_path = os.path.join(self.config_dir, file_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Configuration file not found: {full_path}")
        
        try:
            # Read configuration file
            with open(full_path, "r") as f:
                config_str = f.read()
            
            # Substitute environment variables
            config_str = self._substitute_env_vars(config_str)
            
            # Parse YAML
            config_dict = yaml.safe_load(config_str)
            
            # Validate
            return self._validate_config(config_dict, model_id)
        except FileNotFoundError:
            raise
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration for model {model_id}: {str(e)}")
    
    async def load_configs(self) -> Dict[str, ModelConfig]:
        """Load all model configurations.
        
        Returns:
            Dictionary mapping model IDs to their configurations
            
        Raises:
            FileNotFoundError: If the registry file doesn't exist
            ConfigurationError: If any configuration file is invalid
        """
        registry = await self.load_registry()
        models: Dict[str, ModelConfig] = {}
        
        for model_id, file_path in registry.items():
            try:
                config = await self.load_model_config(model_id, file_path)
                models[model_id] = config
            except FileNotFoundError:
                print(f"Warning: Configuration file for model {model_id} not found: {file_path}")
            except ConfigurationError as e:
                print(f"Warning: {str(e)}")
        
        self._models = models
        return models
    
    async def save_model_config(self, model: ModelConfig) -> None:
        """Save a model configuration to a file.
        
        Args:
            model: The model configuration to save
            
        Raises:
            ConfigurationError: If the configuration can't be saved
        """
        model_id = model.id
        
        # Get file path from registry or create a default
        if model_id in self._registry:
            file_path = self._registry[model_id]
        else:
            # Create default file path
            file_path = f"models/{model_id}.yaml"
            self._registry[model_id] = file_path
        
        full_path = os.path.join(self.config_dir, file_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        try:
            # Convert to dict and remove id (it's in the registry)
            config_dict = model.dict()
            config_dict.pop("id", None)
            
            # Save to file
            with open(full_path, "w") as f:
                yaml.dump(config_dict, f, default_flow_style=False)
            
            # Update registry
            await self.save_registry()
            
            # Update models
            self._models[model_id] = model
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration for model {model_id}: {str(e)}")
    
    async def save_registry(self) -> None:
        """Save the registry to file.
        
        Raises:
            ConfigurationError: If the registry can't be saved
        """
        try:
            # Create registry dict
            registry_dict = {
                "version": "1.0.0",
                "models": [
                    {"id": model_id, "file": file_path}
                    for model_id, file_path in self._registry.items()
                ]
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
            
            # Save to file
            with open(self.registry_file, "w") as f:
                yaml.dump(registry_dict, f, default_flow_style=False)
        except Exception as e:
            raise ConfigurationError(f"Failed to save registry file: {str(e)}")
    
    async def delete_model_config(self, model_id: str) -> None:
        """Delete a model configuration.
        
        Args:
            model_id: The model ID
            
        Raises:
            KeyError: If the model doesn't exist
            ConfigurationError: If the configuration can't be deleted
        """
        if model_id not in self._registry:
            raise KeyError(f"Model {model_id} not found")
        
        file_path = self._registry[model_id]
        full_path = os.path.join(self.config_dir, file_path)
        
        try:
            # Remove file if it exists
            if os.path.exists(full_path):
                os.remove(full_path)
            
            # Remove from registry
            del self._registry[model_id]
            
            # Update registry
            await self.save_registry()
            
            # Remove from models
            if model_id in self._models:
                del self._models[model_id]
        except Exception as e:
            raise ConfigurationError(f"Failed to delete configuration for model {model_id}: {str(e)}")
    
    async def monitor_configs(self):
        """Monitor configuration files for changes."""
        last_modified = {}
        
        while True:
            # Check if any files have changed
            changed = False
            
            # Check registry file
            if os.path.exists(self.registry_file):
                registry_mtime = os.path.getmtime(self.registry_file)
                if self.registry_file not in last_modified or registry_mtime > last_modified[self.registry_file]:
                    changed = True
                    last_modified[self.registry_file] = registry_mtime
            
            # Check model config files
            for model_id, file_path in self._registry.items():
                full_path = os.path.join(self.config_dir, file_path)
                if os.path.exists(full_path):
                    mtime = os.path.getmtime(full_path)
                    if full_path not in last_modified or mtime > last_modified[full_path]:
                        changed = True
                        last_modified[full_path] = mtime
            
            # Reload configs if changed
            if changed:
                print("Configuration files changed, reloading...")
                try:
                    await self.load_configs()
                    print(f"Reloaded {len(self._models)} model configurations")
                except Exception as e:
                    print(f"Error reloading configurations: {str(e)}")
            
            # Wait before checking again
            await asyncio.sleep(5)


# Example usage
async def example_usage():
    """Example usage of the model configuration system."""
    # Create temp config directory
    config_dir = "example_config"
    os.makedirs(os.path.join(config_dir, "models"), exist_ok=True)
    
    # Create registry file
    registry_file = os.path.join(config_dir, "registry.yaml")
    registry = {
        "version": "1.0.0",
        "models": [
            {"id": "example_model", "file": "models/example_model.yaml"}
        ]
    }
    
    with open(registry_file, "w") as f:
        yaml.dump(registry, f, default_flow_style=False)
    
    # Create model config file
    model_file = os.path.join(config_dir, "models", "example_model.yaml")
    model_config = {
        "name": "Example Model",
        "description": "An example model for demonstration",
        "endpoint_url": "${EXAMPLE_MODEL_URL:http://localhost:8000/example}",
        "version": "1.0.0",
        "timeout": 10.0,
        "auth": {
            "type": "api_key",
            "key_name": "X-API-Key",
            "key_value": "${EXAMPLE_MODEL_KEY:default_key}"
        },
        "active": True
    }
    
    with open(model_file, "w") as f:
        yaml.dump(model_config, f, default_flow_style=False)
    
    # Create config manager
    manager = ModelConfigManager(config_dir, registry_file)
    
    # Load configurations
    models = await manager.load_configs()
    
    # Print loaded models
    print("\nLoaded models:")
    for model_id, config in models.items():
        print(f"  {model_id}: {config.name} - {config.endpoint_url}")
    
    # Add a new model
    new_model = ModelConfig(
        id="new_model",
        name="New Model",
        description="A new model added at runtime",
        endpoint_url="http://localhost:8000/new",
        auth=AuthConfig(
            type=AuthType.BEARER_TOKEN,
            key_value="test_token"
        ),
        cache=CacheConfig(
            enabled=True,
            ttl=60,
            max_size=10
        )
    )
    
    await manager.save_model_config(new_model)
    
    # Reload configurations
    models = await manager.load_configs()
    
    # Print loaded models after adding
    print("\nLoaded models after adding new_model:")
    for model_id, config in models.items():
        print(f"  {model_id}: {config.name} - {config.endpoint_url}")
    
    # Delete a model
    await manager.delete_model_config("new_model")
    
    # Reload configurations
    models = await manager.load_configs()
    
    # Print loaded models after deleting
    print("\nLoaded models after deleting new_model:")
    for model_id, config in models.items():
        print(f"  {model_id}: {config.name} - {config.endpoint_url}")
    
    # Clean up
    print("\nCleaning up example files...")
    import shutil
    shutil.rmtree(config_dir)


# Run the example if executed directly
if __name__ == "__main__":
    asyncio.run(example_usage())