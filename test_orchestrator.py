#!/usr/bin/env python3
"""Test script for the orchestrator."""
import requests
import json
import sys
import time

# Configuration
ORCHESTRATOR_URL = "http://localhost:8000"
MODEL_ID = "mock-model-1"

def test_health():
    """Test the health endpoint."""
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/health")
        response.raise_for_status()
        print(f"✅ Health check successful: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_model_list():
    """Test listing models."""
    try:
        response = requests.get(
            f"{ORCHESTRATOR_URL}/admin/models",
            headers={"X-API-Key": "test-admin-key"}
        )
        response.raise_for_status()
        models = response.json()
        print(f"✅ Model list successful: {len(models['models'])} models found")
        return True
    except Exception as e:
        print(f"❌ Model list failed: {e}")
        return False

def test_model_predict():
    """Test model prediction."""
    try:
        data = {
            "inputs": {
                "data": [1, 2, 3, 4, 5]
            },
            "parameters": {}
        }
        response = requests.post(
            f"{ORCHESTRATOR_URL}/orchestrator/models/{MODEL_ID}/predict",
            json=data
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ Model prediction successful")
        print(f"Result: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        print(f"❌ Model prediction failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing orchestrator...")
    
    # Wait for orchestrator to be ready
    print("Waiting for orchestrator to be ready...")
    retries = 0
    while retries < 30:
        try:
            requests.get(f"{ORCHESTRATOR_URL}/health", timeout=2)
            break
        except:
            retries += 1
            print(".", end="", flush=True)
            time.sleep(1)
    print()
    
    if retries == 30:
        print("❌ Orchestrator not ready after 30 seconds")
        sys.exit(1)
    
    # Run tests
    health_ok = test_health()
    model_list_ok = test_model_list()
    model_predict_ok = test_model_predict()
    
    # Print summary
    print("\n🔍 Test Summary:")
    print(f"Health check: {'✅' if health_ok else '❌'}")
    print(f"Model list: {'✅' if model_list_ok else '❌'}")
    print(f"Model prediction: {'✅' if model_predict_ok else '❌'}")
    
    if health_ok and model_list_ok and model_predict_ok:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
