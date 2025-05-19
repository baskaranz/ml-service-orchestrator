#!/usr/bin/env python3
import sys
import json
import requests

def test_model(model_id="mock-model-1"):
    """Test a model directly."""
    
    # Test model directly
    url = f"http://localhost:8001/predict"
    payload = {"input": "Hello, world!"}
    
    try:
        print(f"Testing model {model_id} directly...")
        response = requests.post(url, json=payload)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"Error testing model directly: {str(e)}")
        return False

if __name__ == "__main__":
    model_id = sys.argv[1] if len(sys.argv) > 1 else "mock-model-1"
    test_model(model_id)