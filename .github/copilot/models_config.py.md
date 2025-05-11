# Create instructions for models_config.py
Create a config loader class that:
1. Reads model configurations from YAML files in a specified directory
2. Supports hot-reloading of configurations when files change
3. Validates configurations against Pydantic models
4. Supports environment variable substitution in configurations
5. Maintains a registry of all loaded models with their endpoints
6. Handles file watching with proper error handling
7. Uses async file operations for better performance
8. Implements proper locking for thread safety