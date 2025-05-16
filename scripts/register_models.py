#!/usr/bin/env python3
"""Script to register mock models with the orchestrator."""
import os
import sys
import json
import requests
from typing import Dict, Any

# Configuration
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")

# Model configurations
MODELS = [
    {
        "model": {
            "id": "mock-model-1",
            "name": "Mock Model 1",
            "description": "First mock model for testing",
            "version": "1.0.0",
            "endpoint_url": "http://mock-model-1:8000/predict",
            "active": True,
            "platform": {
                "name": "mock",
                "config": {"timeout": 30, "max_retries": 3}
            }
        }
    },
    {
        "model": {
            "id": "mock-model-2",
            "name": "Mock Model 2",
            "description": "Second mock model for testing",
            "version": "1.0.0",
            "endpoint_url": "http://mock-model-2:8000/predict",
            "active": True,
            "platform": {
                "name": "mock",
                "config": {"timeout": 30, "max_retries": 3}
            }
        }
    }
]

def register_model(model_config: Dict[str, Any]) -> bool:
    """Register a single model with the orchestrator."""
    url = f"{ORCHESTRATOR_URL}/admin/register-model"
    headers = {
        "X-API-Key": "dev-admin-key"  # Default admin key from test settings
    }
    try:
        response = requests.post(url, json=model_config, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"✅ Successfully registered model: {model_config['model']['id']}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to register model {model_config['model']['id']}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False

def main():
    """Main function to register all models."""
    print(f"Registering models with orchestrator at {ORCHESTRATOR_URL}...")
    
    success = all(register_model(model) for model in MODELS)
    
    if success:
        print("\n🎉 All models registered successfully!")
        print(f"\nYou can now access the models at:")
        for model in MODELS:
            print(f"- {model['model']['name']}: {ORCHESTRATOR_URL}/orchestrator/models/{model['model']['id']}/predict")
    else:
        print("\n⚠️ Some models failed to register. Check the logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
