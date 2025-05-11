# ML Orchestrator - Config Layer Instructions

This file provides detailed guidance for implementing config-related code in the ML Orchestrator service.

## Overview

The configuration layer is responsible for:
1. Loading and parsing YAML configuration files
2. Validating configurations against Pydantic models
3. Supporting environment variable substitution
4. Monitoring for configuration file changes
5. Providing configuration data to other components

## Key Files

- `app/config/models_config.py`: YAML model configuration loading and management
- `app/config/settings.py`: Environment-based application settings
- `app/core/models.py`: Pydantic data models for configuration

## Configuration Models

The core configuration model is `ModelConfig` in `app/core/models.py`:

```python
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
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional headers to send with requests"
    )
    active: bool = Field(default=True, description="Whether the model is active")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "forbid"
```

When extending this model with new features, follow the pattern of nested Pydantic models:

```python
class NewFeatureConfig(BaseModel):
    """Configuration for the new feature."""
    
    enabled: bool = Field(default=False, description="Whether the feature is enabled")
    setting_one: str = Field(default="default", description="First setting")
    setting_two: int = Field(default=10, description="Second setting")
    
    class Config:
        extra = "forbid"

# Then add to ModelConfig:
class ModelConfig(BaseModel):
    # Existing fields...
    
    new_feature: Optional[NewFeatureConfig] = Field(
        default=None,
        description="Configuration for the new feature"
    )
```

## YAML Configuration Management

The `ModelConfigManager` in `app/config/models_config.py` handles loading and parsing YAML configuration files:

```python
class ModelConfigManager:
    """Manager for model configurations."""
    
    def __init__(self, config_dir: str, registry_file: str):
        """Initialize the model configuration manager.
        
        Args:
            config_dir: Path to the directory containing model configurations
            registry_file: Path to the model registry file
        """
        self.config_dir = config_dir
        self.registry_file = registry_file
        self._registry = {}
        self._models = {}
    
    async def load_configs(self) -> Dict[str, ModelConfig]:
        """Load all model configurations.
        
        Returns:
            Dictionary mapping model IDs to their configurations
        
        Raises:
            FileNotFoundError: If the registry file doesn't exist
            ValueError: If the registry file is invalid
        """
        # Implementation...
```

When implementing configuration loading, follow these patterns:

1. **Environment Variable Substitution**:
   ```python
   def _substitute_env_vars(self, config_str: str) -> str:
       """Substitute environment variables in a configuration string.
       
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
   ```

2. **File Monitoring**:
   ```python
   async def monitor_configs(self):
       """Monitor configuration files for changes."""
       last_modified = {}
       
       while True:
           # Check if any files have changed
           changed = False
           
           # Check registry file
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
               await self.load_configs()
           
           # Wait before checking again
           await asyncio.sleep(5)
   ```

3. **Configuration Validation**:
   ```python
   def _validate_config(self, config_dict: Dict, model_id: str) -> ModelConfig:
       """Validate a model configuration.
       
       Args:
           config_dict: Dictionary containing model configuration
           model_id: The model ID for error messages
           
       Returns:
           Validated ModelConfig instance
           
       Raises:
           ValidationError: If the configuration is invalid
       """
       try:
           # Ensure ID is set
           config_dict["id"] = model_id
           
           # Validate against ModelConfig
           return ModelConfig(**config_dict)
       except ValidationError as e:
           raise ConfigurationError(f"Invalid configuration for model {model_id}: {str(e)}")
   ```

## Testing Config Code

When testing configuration code, follow these patterns:

```python
@pytest.fixture
def test_config_dir(tmp_path):
    """Create a temporary config directory."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    
    # Create registry file
    registry = {
        "version": "1.0.0",
        "models": [
            {"id": "test_model", "file": "models/test_model.yaml"}
        ]
    }
    
    registry_file = tmp_path / "registry.yaml"
    registry_file.write_text(yaml.dump(registry))
    
    # Create model config file
    model_config = {
        "name": "Test Model",
        "description": "Test model for unit tests",
        "endpoint_url": "http://example.com/test",
        "version": "1.0.0",
        "timeout": 10.0,
        "active": True
    }
    
    model_file = models_dir / "test_model.yaml"
    model_file.write_text(yaml.dump(model_config))
    
    return tmp_path

@pytest.mark.asyncio
async def test_load_configs(test_config_dir):
    """Test loading configurations."""
    manager = ModelConfigManager(
        config_dir=str(test_config_dir),
        registry_file=str(test_config_dir / "registry.yaml")
    )
    
    # Load configs
    configs = await manager.load_configs()
    
    # Verify
    assert "test_model" in configs
    assert configs["test_model"].name == "Test Model"
    assert configs["test_model"].endpoint_url == "http://example.com/test"
```

## Environment Variable Settings

The `settings.py` file uses Pydantic's `BaseSettings` to load settings from environment variables:

```python
class AppSettings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application settings
    APP_NAME: str = "ML Orchestrator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    
    # Config file paths
    CONFIG_DIR: str = "./config"
    MODELS_REGISTRY_FILE: str = "./config/models_registry.yaml"
    
    # Default service settings
    DEFAULT_TIMEOUT: float = 30.0
    DEFAULT_MAX_RETRIES: int = 3
    
    # Circuit breaker defaults
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RESET_TIMEOUT: float = 30.0
    
    # Admin API settings
    ADMIN_API_ENABLED: bool = True
    ADMIN_API_KEY: Optional[str] = None
    
    class Config:
        """Pydantic settings configuration."""
        
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
```

When adding new settings, follow this pattern and group related settings together.