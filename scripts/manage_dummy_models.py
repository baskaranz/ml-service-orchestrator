"""
Script to manage dummy models in the orchestrator.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import yaml

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.models.config_models import ModelConfig

def create_model_config(model_name: str, port: int) -> Dict[str, Any]:
    """Create a dummy model configuration."""
    return {
        "id": model_name,
        "name": model_name.capitalize(),
        "description": f"A dummy model for testing purposes: {model_name}",
        "version": "1.0.0",
        "endpoint_url": f"http://localhost:{port}",
        "enabled": True,
        "timeout": 30.0,
        "retry_count": 3,
        "retry_delay": 1.0,
        "circuit_breaker": {
            "failure_threshold": 5,
            "recovery_timeout": 30,
            "half_open_timeout": 10
        }
    }

def ensure_model_configs_dir() -> Path:
    """Ensure the model configs directory exists at project root config/models."""
    config_dir = Path(__file__).parent.parent.parent / "config" / "models"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def register_models(model_names: List[str]) -> List[str]:
    """Write all dummy model configs as YAML files in config/models/."""
    models_dir = ensure_model_configs_dir()
    model_ids = []
    for i, model_name in enumerate(model_names, start=1):
        config_data = create_model_config(model_name, 8000 + i)
        model_path = models_dir / f"{model_name}.yaml"
        with open(model_path, "w") as f:
            yaml.dump(config_data, f)
        print(f"Wrote model config to {model_path}")
        model_ids.append(model_name)
    return model_ids

def main():
    """Main function to manage dummy models."""
    # Use simple model names
    model_names = [f"model{i}" for i in range(1, 11)]
    print("Registering models...")
    register_models(model_names)

if __name__ == "__main__":
    main() 