"""Script to generate dummy model configurations."""

import os
from pathlib import Path
import yaml

def generate_dummy_configs():
    """Generate dummy model configurations."""
    # Create config/models directory if it doesn't exist
    config_dir = Path("config/models")
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate configs for 10 models
    for i in range(1, 11):
        model_id = f"dummy-model-{i}"
        port = 8000 + i
        
        config = {
            "id": model_id,
            "name": f"Dummy Model {i}",
            "description": f"A dummy model for testing #{i}",
            "version": "1.0.0",
            "endpoint_url": f"http://localhost:{port}",
            "active": True,
            "timeout": 30.0,
            "max_retries": 3,
            "headers": {}
        }
        
        # Write to file
        config_path = config_dir / f"{model_id}.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print(f"Generated config for {model_id}")

if __name__ == "__main__":
    generate_dummy_configs() 