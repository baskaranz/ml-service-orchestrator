"""
Configuration loading and management for model endpoints.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

import yaml
from pydantic import BaseModel, ValidationError

from app.core.exceptions import ModelAlreadyExistsError, ModelNotFoundError
from app.models.config_models import ModelConfig, ModelRegistry
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ModelConfigManager:
    """Manages model configurations."""

    def __init__(self, config_dir: str = None, env: str = None):
        """Initialize the configuration manager.

        Args:
            config_dir: Base configuration directory path. If None, will be determined automatically.
            env: Environment name (dev, stg, prod, local). If None, uses APP_ENV environment variable.
        """
        # Get environment from parameter or environment variable, default to 'local'
        self.env = (env or os.getenv("APP_ENV", "local")).lower()

        # Validate environment
        valid_envs = ["dev", "stg", "prod", "test", "local"]
        if self.env not in valid_envs:
            raise ValueError(
                f"Invalid environment: {self.env}. Must be one of: {', '.join(valid_envs)}"
            )

        # Log the environment being used
        logger.info(f"Initializing ModelConfigManager with environment: {self.env}")

        # Determine the base config directory
        if config_dir:
            config_path = Path(config_dir).resolve()
        else:
            # Try to determine the config directory automatically
            possible_config_dirs = [
                Path("/app/config"),  # Docker container
                Path.cwd() / "config",  # Local development
                Path(__file__).parent.parent.parent / "config",  # Installed package
            ]

            config_path = None
            for dir_path in possible_config_dirs:
                if dir_path.exists() and dir_path.is_dir():
                    config_path = dir_path.resolve()
                    break

            if config_path is None:
                # Default to current working directory
                config_path = Path.cwd() / "config"

        # Determine models directory
        possible_models_dirs = [
            config_path / "local" / "models",  # /config/local/models (current location)
            config_path / "models" / self.env,  # /config/models/{env}
            config_path / self.env / "models",  # /config/{env}/models
            config_path / "models" / "local",  # /config/models/local (legacy)
        ]

        # Check each possible directory
        models_dir = None
        for dir_path in possible_models_dirs:
            dir_path = dir_path.resolve()
            logger.debug(f"Checking for models in: {dir_path}")
            if dir_path.exists() and dir_path.is_dir():
                models_dir = dir_path
                logger.info(f"Found models directory: {models_dir}")
                break

        # If no directory found, create the standard one
        if models_dir is None:
            models_dir = config_path / self.env / "models"
            logger.warning(f"No models directory found, creating: {models_dir}")
            try:
                models_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created models directory: {models_dir}")
            except Exception as e:
                logger.error(f"Failed to create models directory {models_dir}: {str(e)}")
                raise

        self.models_dir = str(models_dir)
        self.config_dir = str(config_path)

        # Log the final paths being used
        logger.info(f"Using models directory: {self.models_dir}")
        logger.info(f"Using config directory: {self.config_dir}")
        logger.info(f"Current working directory: {os.getcwd()}")

        # List the contents of the models directory for debugging
        try:
            models_path = Path(self.models_dir)
            if models_path.exists():
                files = [f.name for f in models_path.iterdir() if f.is_file()]
                yaml_files = [f for f in files if f.endswith((".yaml", ".yml"))]
                logger.info(f"Found {len(yaml_files)} YAML files in {self.models_dir}")

                if yaml_files:
                    logger.debug(f"YAML files: {yaml_files}")

                    # Log the first few lines of each YAML file for debugging
                    for yaml_file in yaml_files[:3]:  # Limit to first 3 files to avoid log spam
                        try:
                            with open(models_path / yaml_file, "r") as f:
                                first_lines = [next(f) for _ in range(5)]
                            logger.debug(f"First lines of {yaml_file}:\n{''.join(first_lines)}")
                        except Exception as e:
                            logger.debug(f"Could not read {yaml_file}: {str(e)}")
                else:
                    logger.warning(f"No YAML files found in {self.models_dir}")
            else:
                logger.error(f"Models directory does not exist: {self.models_dir}")
        except Exception as e:
            logger.error(f"Error listing contents of {self.models_dir}: {str(e)}")

        # Initialize model storage
        self.models: Dict[str, ModelConfig] = {}
        self.registry: Optional[ModelRegistry] = None
        self.last_modified: Dict[str, float] = {}

        # Log the current working directory for debugging
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(
            f"Environment variables: { {k: v for k, v in os.environ.items() if k in ('APP_ENV', 'MODELS_DIR', 'CONFIG_DIR', 'CONFIG_PATH')} }"
        )

    def _generate_registry(self) -> ModelRegistry:
        """Generate registry from loaded model configurations."""
        registry_models = {}
        for model_id, model in self.models.items():
            registry_models[model_id] = model
        return ModelRegistry(
            name="Model Registry",
            description="Registry of model configurations",
            models=registry_models,
        )

    async def load_configs(self) -> Tuple[ModelRegistry, Dict[str, ModelConfig]]:
        """Load all model configurations from the config directory.

        This method loads model configurations from the environment-specific models directory.
        It expects the following structure:
            config/
            ├── local/
            │   └── models/
            │       ├── model1.yaml
            │       └── model2.yaml
            ├── dev/
            │   └── models/
            └── prod/
                └── models/"""
        try:
            # Use the models_dir set in __init__
            models_path = Path(self.models_dir)

            # Debug: Log the current working directory and models path
            logger.info(f"Current working directory: {os.getcwd()}")
            logger.info(f"Models path: {models_path}")
            logger.info(f"Models path exists: {models_path.exists()}")
            logger.info(f"Models path is absolute: {models_path.is_absolute()}")
            logger.info(f"Environment: {self.env}")

            if not models_path.exists():
                # Try to create the directory if it doesn't exist
                try:
                    models_path.mkdir(parents=True, exist_ok=True)
                    logger.warning(f"Created models directory: {models_path}")
                except Exception as e:
                    logger.error(f"Failed to create models directory {models_path}: {str(e)}")

                raise FileNotFoundError(
                    f"Models directory not found for environment '{self.env}': {models_path}"
                    f"\nPlease ensure the directory exists and contains model configurations."
                )

            # List all YAML files in the models directory
            yaml_files = list(models_path.glob("*.yaml")) + list(models_path.glob("*.yml"))
            logger.info(
                f"Found {len(yaml_files)} YAML files in {models_path}: {[f.name for f in yaml_files]}"
            )

            if not yaml_files:
                logger.warning(f"No YAML files found in {models_path}")

            self.models.clear()

            # Load all model YAMLs from the models directory
            for file_path in yaml_files:
                if file_path.name == "registry.yaml":
                    logger.debug(f"Skipping registry file: {file_path}")
                    continue  # Skip registry.yaml as we generate it

                try:
                    logger.info(f"Processing model file: {file_path}")
                    logger.info(f"File exists: {file_path.exists()}")
                    logger.info(f"File size: {file_path.stat().st_size} bytes")

                    # Read the file content first for debugging
                    try:
                        with open(file_path, "r") as f:
                            file_content = f.read()
                            logger.debug(f"File content:\n{file_content}")
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {str(e)}")
                        continue

                    model_dict = self._read_yaml_file(file_path)

                    # If the file is empty or not a dictionary, skip it
                    if not model_dict or not isinstance(model_dict, dict):
                        logger.warning(
                            f"Skipping invalid model file (not a YAML dictionary): {file_path}"
                        )
                        continue

                    # Set the model ID from the filename if not specified
                    if "id" not in model_dict:
                        model_dict["id"] = file_path.stem
                        logger.debug(f"Set model ID to filename: {model_dict['id']}")

                    expected_id = file_path.stem
                    if model_dict.get("id") != expected_id:
                        logger.warning(
                            f"Model ID mismatch in {file_path}: expected {expected_id}, got {model_dict.get('id')}"
                        )

                    # Ensure the active flag is set and is a boolean
                    if "active" not in model_dict:
                        logger.debug(f"No 'active' flag found in {file_path}, defaulting to True")
                        model_dict["active"] = True

                    # Log the active status
                    logger.info(
                        f"Model {model_dict.get('id')} active status: {model_dict.get('active')} (type: {type(model_dict.get('active'))})"
                    )

                    # Process environment variables in the config
                    model_dict = self._process_environment_vars(model_dict)

                    # Debug: Log the model dictionary before creating the ModelConfig
                    logger.debug(f"Creating ModelConfig from: {model_dict}")

                    # Create model config
                    try:
                        logger.info(f"Creating ModelConfig for {model_dict.get('id')}")
                        model_config = ModelConfig(**model_dict)

                        if model_config.id is None:
                            logger.warning(f"Model ID is None in {file_path}")
                            continue

                        # Log the model's active status after creation
                        active_status = getattr(model_config, "active", "not set")
                        logger.info(
                            f"Successfully created ModelConfig for '{model_config.id}' with active={active_status}"
                        )

                        # Log all attributes of the model config for debugging
                        logger.debug(f"ModelConfig attributes for {model_config.id}:")
                        for attr, value in model_config.dict().items():
                            logger.debug(f"  {attr}: {value} (type: {type(value)})")

                        self.models[model_config.id] = model_config
                        self.last_modified[str(file_path)] = file_path.stat().st_mtime

                        logger.info(
                            f"Successfully loaded model configuration for '{model_config.id}'"
                        )
                    except ValidationError as e:
                        logger.error(
                            f"Validation error creating ModelConfig from {file_path}: {str(e)}"
                        )
                        continue
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

    def _process_environment_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process environment variables in the configuration."""
        processed = {}
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Handle environment variable substitution
                env_var = value[2:-1]  # Remove ${ and }
                processed[key] = os.getenv(env_var, value)
            elif isinstance(value, dict):
                processed[key] = self._process_environment_vars(value)
            elif isinstance(value, list):
                processed[key] = [
                    (
                        self._process_environment_vars(v)
                        if isinstance(v, dict)
                        else (
                            os.getenv(v[2:-1], v)
                            if isinstance(v, str) and v.startswith("${") and v.endswith("}")
                            else v
                        )
                    )
                    for v in value
                ]
            else:
                processed[key] = value
        return processed

    def _write_yaml_file(self, file_path: Path, content: Dict[str, Any]) -> None:
        """Write content to a YAML file."""
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert Pydantic models to dicts
            if isinstance(content, BaseModel):
                content = content.model_dump()

            # Write to file
            with open(file_path, "w") as f:
                yaml.dump(content, f, default_flow_style=False, sort_keys=False)

            # Update last modified time
            self.last_modified[str(file_path)] = file_path.stat().st_mtime
        except Exception as e:
            logger.error(f"Failed to write YAML file {file_path}: {str(e)}")
            raise

    def get_model_config(self, model_id: str) -> ModelConfig:
        """Get a model configuration by ID."""
        if model_id not in self.models:
            raise ModelNotFoundError(f"Model not found: {model_id}")
        return self.models[model_id]

    def add_model_config(self, model: ModelConfig) -> None:
        """Add a new model configuration.

        Args:
            model: The model configuration to add

        Raises:
            ValueError: If model ID is None
            ModelAlreadyExistsError: If a model with the same ID already exists
        """
        if model.id is None:
            raise ValueError("Model ID cannot be None")
        if model.id in self.models:
            raise ModelAlreadyExistsError(f"Model already exists: {model.id}")

        # Write to disk in the environment-specific models directory
        config_path = Path(self.models_dir) / f"{model.id}.yaml"
        self._write_yaml_file(config_path, model.model_dump())

        # Update in-memory state
        self.models[model.id] = model
        self.registry = self._generate_registry()
        logger.info(f"Added model configuration: {model.id}")

    def update_model_config(self, model_id: str, model: ModelConfig) -> None:
        """Update an existing model configuration.

        Args:
            model_id: The ID of the model to update
            model: The updated model configuration

        Raises:
            ModelNotFoundError: If the model is not found
        """
        if model_id not in self.models:
            raise ModelNotFoundError(f"Model not found: {model_id}")

        # Write the updated config to disk
        config_path = Path(self.models_dir) / f"{model_id}.yaml"
        self._write_yaml_file(config_path, model.model_dump())

        # Update in-memory state
        self.models[model_id] = model
        self.registry = self._generate_registry()
        logger.info(f"Updated model configuration: {model_id}")

    def delete_model_config(self, model_id: str) -> None:
        """Delete a model configuration.

        Args:
            model_id: The ID of the model to delete

        Raises:
            ModelNotFoundError: If the model is not found
        """
        logger.debug(f"Attempting to delete model: {model_id}")
        logger.debug(f"Current models: {list(self.models.keys())}")

        if model_id not in self.models:
            raise ModelNotFoundError(f"Model not found: {model_id}")

        # Delete from disk
        config_path = Path(self.models_dir) / f"{model_id}.yaml"
        logger.debug(f"Config path: {config_path}")
        logger.debug(f"Config path exists: {config_path.exists()}")

        if config_path.exists():
            try:
                config_path.unlink()
                logger.info(f"Deleted model configuration: {model_id}")
            except Exception as e:
                logger.error(f"Failed to delete config file {config_path}: {str(e)}")
                raise

        # Update in-memory state
        logger.debug(f"Removing model {model_id} from in-memory models")
        del self.models[model_id]
        logger.debug(f"Updated models: {list(self.models.keys())}")
        self.registry = self._generate_registry()
        logger.debug("Registry updated after deletion")

    def should_reload(self, changed_files: Set[Path]) -> bool:
        """Check if configurations should be reloaded."""
        for file_path in changed_files:
            if not file_path.exists():
                continue
            current_mtime = file_path.stat().st_mtime
            if (
                str(file_path) not in self.last_modified
                or current_mtime > self.last_modified[str(file_path)]
            ):
                return True
        return False
