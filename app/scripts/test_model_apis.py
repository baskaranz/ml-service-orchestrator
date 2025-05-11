"""
Script to test model APIs directly and through the orchestrator.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

import aiohttp
import requests

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.models.config_models import ModelConfig
from app.services.orchestrator import Orchestrator

async def test_direct_model_api(model_config: ModelConfig) -> Dict[str, Any]:
    """Test a model API directly."""
    async with aiohttp.ClientSession() as session:
        url = f"{model_config.endpoint_url}/predict"
        headers = model_config.headers
        data = {"input": "test input"}
        
        try:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Status {response.status}", "detail": await response.text()}
        except Exception as e:
            return {"error": "Request failed", "detail": str(e)}

async def test_orchestrator_api(model_id: str) -> Dict[str, Any]:
    """Test a model API through the orchestrator."""
    async with aiohttp.ClientSession() as session:
        url = f"http://localhost:8000/orchestrator/models/{model_id}"
        headers = {"Content-Type": "application/json"}
        data = {"input": "test input"}
        
        try:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Status {response.status}", "detail": await response.text()}
        except Exception as e:
            return {"error": "Request failed", "detail": str(e)}

async def main():
    """Main function to test model APIs."""
    # Load model configurations
    config_dir = Path(__file__).parent.parent / "config" / "models"
    configs = []
    
    for config_file in config_dir.glob("dummy-model-*.json"):
        with open(config_file) as f:
            config_data = json.load(f)
            config = ModelConfig(**config_data)
            configs.append(config)
    
    # Test each model
    print("\nTesting direct model APIs...")
    for config in configs:
        print(f"\nTesting direct API for {config.id}:")
        result = await test_direct_model_api(config)
        print(json.dumps(result, indent=2))
    
    print("\nTesting orchestrator APIs...")
    for config in configs:
        print(f"\nTesting orchestrator API for {config.id}:")
        result = await test_orchestrator_api(config.id)
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main()) 