#!/bin/bash
# Script to load models inside the Docker container

# Create a Python script inside the container
cat > /tmp/load_models.py << 'EOF'
#!/usr/bin/env python3
"""
Script to manually load models into the orchestrator.
"""

import os
import sys
import yaml
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.append('/app')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("load_models")

def main():
    """Main function to load models."""
    logger.info("Starting manual model loading script...")
    
    # Try to import required modules
    try:
        from app.models.config_models import ModelConfig
        from app.api.routers.orchestrator import _orchestrator
    except ImportError as e:
        logger.error(f"Error importing required modules: {e}")
        logger.info("Make sure this script is run inside the Docker container with the correct Python environment")
        sys.exit(1)
    
    # Define the models directory
    models_dir = Path("/app/config/local/models")
    logger.info(f"Looking for models in: {models_dir}")
    
    # Check if the directory exists
    if not models_dir.exists():
        logger.error(f"Models directory not found: {models_dir}")
        sys.exit(1)
    
    # List all YAML files in the directory
    yaml_files = list(models_dir.glob("*.yaml")) + list(models_dir.glob("*.yml"))
    logger.info(f"Found {len(yaml_files)} YAML files: {[f.name for f in yaml_files]}")
    
    # Load models from YAML files
    models = {}
    for file_path in yaml_files:
        try:
            with open(file_path, 'r') as f:
                logger.info(f"Loading model from {file_path}")
                model_dict = yaml.safe_load(f)
                if model_dict and isinstance(model_dict, dict):
                    # Ensure the model is active
                    model_dict['active'] = True
                    model_config = ModelConfig(**model_dict)
                    models[model_config.id] = model_config
                    logger.info(f"Successfully loaded model: {model_config.id}")
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
    
    # If no models were loaded, use fallback models
    if not models:
        logger.warning("No models loaded from files, using fallback models")
        fallback_models = [
            {
                "id": "model1",
                "name": "Model 1",
                "description": "Mock model 1",
                "endpoint_url": "http://host.docker.internal:8001/predict",
                "active": True,
                "timeout": 30.0,
                "max_retries": 3
            },
            {
                "id": "model2",
                "name": "Model 2",
                "description": "Mock model 2",
                "endpoint_url": "http://host.docker.internal:8002/predict",
                "active": True,
                "timeout": 30.0,
                "max_retries": 3
            },
            {
                "id": "mock-model-1",
                "name": "Mock Model 1",
                "description": "Mock model for testing",
                "endpoint_url": "http://mock-model-1:8000/predict",
                "active": True,
                "timeout": 30.0,
                "max_retries": 3
            },
            {
                "id": "mock-model-2",
                "name": "Mock Model 2",
                "description": "Another mock model for testing",
                "endpoint_url": "http://mock-model-2:8000/predict",
                "active": True,
                "timeout": 30.0,
                "max_retries": 3
            }
        ]
        
        for model_dict in fallback_models:
            try:
                model_config = ModelConfig(**model_dict)
                models[model_config.id] = model_config
                logger.info(f"Created fallback model: {model_config.id}")
            except Exception as e:
                logger.error(f"Error creating fallback model {model_dict.get('id')}: {e}")
    
    # Update the orchestrator's models
    if models:
        logger.info(f"Updating orchestrator with {len(models)} models")
        _orchestrator._models = models
        logger.info(f"Models loaded: {list(_orchestrator._models.keys())}")
    else:
        logger.error("No models were loaded. The orchestrator will not be able to process requests.")
    
    # Verify models are loaded
    logger.info(f"Final orchestrator models: {_orchestrator._models}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF

# Make the script executable
chmod +x /tmp/load_models.py

# Run the script with the correct Python environment
cd /app && python /tmp/load_models.py
