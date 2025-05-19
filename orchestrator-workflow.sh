#!/bin/bash
# Comprehensive script to set up and run the orchestrator with mock models

set -e  # Exit on error

# Color setup for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Orchestrator Workflow${NC}"

# Remove any existing containers
echo -e "${YELLOW}Stopping and removing any existing containers...${NC}"
docker-compose down -v

# Fix the HTTP client to properly handle Content-Length headers
echo -e "${YELLOW}Applying HTTP client fix...${NC}"
cat > http_fix.patch << 'EOF'
--- http.py.orig	2023-07-28 12:00:00.000000000 +0000
+++ http.py	2023-07-28 12:00:01.000000000 +0000
@@ -151,6 +151,11 @@
         # Initialize headers and params
         request_headers = dict(headers or {})
         request_params = dict(params or {})
+        
+        # FIX: Always remove content-length header to let httpx handle it properly
+        if 'content-length' in request_headers:
+            del request_headers['content-length']
+        if 'Content-Length' in request_headers:
+            del request_headers['Content-Length']
 
         # Apply authentication
         if self.auth_config:
EOF

if grep -q "del request_headers\['content-length'\]" app/utils/http.py; then
    echo -e "${GREEN}HTTP client fix already applied${NC}"
else
    # Apply patch manually without patch command
    cp app/utils/http.py app/utils/http.py.bak
    # Insert content-length fix after line 150
    sed -i.bak '150a\        # FIX: Always remove content-length header to let httpx handle it properly\n        if '\''content-length'\'' in request_headers:\n            del request_headers['\''content-length'\'']\n        if '\''Content-Length'\'' in request_headers:\n            del request_headers['\''Content-Length'\'']' app/utils/http.py
    echo -e "${GREEN}HTTP client fix applied${NC}"
fi

# Update the register_models.py script to use correct endpoints
echo -e "${YELLOW}Updating register_models.py script...${NC}"
cat > scripts/register_models.py << 'EOF'
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
            "endpoint_url": "http://mock-model-1:8000",
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
            "endpoint_url": "http://mock-model-2:8000",
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
    url = f"{ORCHESTRATOR_URL}/admin/models"
    headers = {
        "X-API-Key": "test-admin-key",  # Admin key from settings
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=model_config, headers=headers, timeout=30)
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
EOF

# Create a config directory for models if it doesn't exist
echo -e "${YELLOW}Creating config directory structure...${NC}"
mkdir -p config/local/models

# Create test model configurations
echo -e "${YELLOW}Creating model configurations...${NC}"
cat > config/local/models/mock-model-1.yaml << 'EOF'
id: mock-model-1
name: Mock Model 1
description: First mock model for testing
version: 1.0.0
endpoint_url: http://mock-model-1:8000
active: true
platform:
  name: mock
  config:
    timeout: 30
    max_retries: 3
EOF

cat > config/local/models/mock-model-2.yaml << 'EOF'
id: mock-model-2
name: Mock Model 2
description: Second mock model for testing
version: 1.0.0
endpoint_url: http://mock-model-2:8000
active: true
platform:
  name: mock
  config:
    timeout: 30
    max_retries: 3
EOF

# Create .env file for Docker Compose
echo -e "${YELLOW}Creating .env file...${NC}"
cat > .env << 'EOF'
ORCHESTRATOR_PORT=8000
LOG_LEVEL=DEBUG
ADMIN_API_KEY=test-admin-key
EOF

# Create a test script
echo -e "${YELLOW}Creating test script...${NC}"
cat > test_orchestrator.py << 'EOF'
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
EOF

chmod +x test_orchestrator.py
chmod +x scripts/register_models.py

# Build and start the containers
echo -e "${YELLOW}Building and starting containers...${NC}"
docker-compose build
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 15

# Register models with the orchestrator
echo -e "${YELLOW}Registering models with the orchestrator...${NC}"
python3 scripts/register_models.py

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
python3 test_orchestrator.py

echo -e "${GREEN}Orchestrator workflow completed!${NC}"
echo -e "You can access the orchestrator at http://localhost:8000"
echo -e "You can access the mock models directly at:"
echo -e "- Mock Model 1: http://localhost:8001"
echo -e "- Mock Model 2: http://localhost:8002"
echo -e "The orchestrator API is available at:"
echo -e "- Health check: http://localhost:8000/health"
echo -e "- Model list (requires X-API-Key: test-admin-key): http://localhost:8000/admin/models"
echo -e "- Model prediction: http://localhost:8000/orchestrator/models/mock-model-1/predict"