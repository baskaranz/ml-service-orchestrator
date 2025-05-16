"""
Script to update the mock model endpoint URL in the orchestrator.
"""
import requests
import os
from typing import Dict, Any

# Configuration
ORCHESTRATOR_URL = "http://localhost:8000"
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "test-admin-key")  # Default from test settings

# Model configuration to update
MODEL_ID = "mock-model-1"
NEW_ENDPOINT = "http://lasso-mock-model-1-1:8000/predict"

def update_model_endpoint():
    """Update the model's endpoint URL in the orchestrator."""
    # First, get the current model config
    response = requests.get(
        f"{ORCHESTRATOR_URL}/admin/models/{MODEL_ID}",
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get model config: {response.status_code} - {response.text}")
        return
    
    model_config = response.json()
    
    # Update the endpoint URL
    model_config["endpoint_url"] = NEW_ENDPOINT
    
    # Update the model using the register-model endpoint
    update_response = requests.post(
        f"{ORCHESTRATOR_URL}/admin/register-model",
        json={
            "model": {
                "id": MODEL_ID,
                "name": model_config["name"],
                "endpoint_url": NEW_ENDPOINT,
                "active": model_config.get("active", True)
            }
        },
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    
    if update_response.status_code == 200:
        print(f"✅ Successfully updated model {MODEL_ID}")
        print(f"New endpoint: {NEW_ENDPOINT}")
    else:
        print(f"❌ Failed to update model: {update_response.status_code} - {update_response.text}")

if __name__ == "__main__":
    update_model_endpoint()
