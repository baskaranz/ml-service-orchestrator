"""
Test script for error handling and statistics functionality.
"""

import asyncio
import logging
from typing import Dict, Any
from unittest.mock import AsyncMock, patch
import httpx
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.requests import Request as StarletteRequest

from app.core.exceptions import ModelRequestError
from app.models.config_models import ModelConfig, CircuitBreakerConfig
from app.services.orchestrator import Orchestrator
from app.utils.error_handling import RetryConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create test app
app = FastAPI(
    title="Error Handling Test App",
    description="Test application for error handling functionality",
    version="1.0.0"
)
orchestrator = Orchestrator()

# Mock model configuration
test_model_config = ModelConfig(
    id="test-model",
    name="Test Model",
    description="Test model for error handling",
    version="1.0.0",
    endpoint_url="http://mocked-endpoint/test",
    active=True,
    max_retries=2,
    timeout=5.0,
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=2,
        reset_timeout=10.0,
        exclude_exceptions=["ValueError"]
    )
)

# Mock HTTP client
class MockHttpClient:
    def __init__(self):
        self.call_count = 0
    async def request(self, *args, **kwargs):
        self.call_count += 1
        # Simulate failure for first two calls, then success
        if self.call_count <= 2:
            raise Exception(f"Simulated failure {self.call_count}")
        return 200, {"status": "success", "attempt": self.call_count}, {"content-type": "application/json"}

class MockCircuitBreaker:
    def __init__(self):
        self.current_state = "closed"
    def success(self):
        pass
    def failure(self):
        pass

@app.post("/test")
async def test_endpoint(request: Request):
    """Test endpoint that uses the orchestrator."""
    return await orchestrator.proxy_request(test_model_config, request)

@app.get("/test/stats")
async def get_stats():
    """Get statistics for the test model."""
    return orchestrator.get_model_stats("test-model")

async def run_tests():
    """Run the test suite."""
    client = TestClient(app)
    # Patch the orchestrator's _get_client and get_circuit_breaker to use the mocks
    with patch.object(Orchestrator, "_get_client", return_value=MockHttpClient()), \
         patch.object(Orchestrator, "get_circuit_breaker", return_value=MockCircuitBreaker()):
        logger.info("Test 1: Testing successful request after retries")
        response = client.post("/test", json={"test": "data"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        logger.info("Test 2: Checking statistics")
        stats = client.get("/test/stats").json()
        assert stats["model_id"] == "test-model"
        assert stats["request_stats"]["total_requests"] > 0
        assert stats["request_stats"]["successful_requests"] > 0
        assert "error_stats" in stats
        logger.info("Test 3: Testing circuit breaker (simulate more failures)")
        # Patch to always fail
        with patch.object(MockHttpClient, "request", new=AsyncMock(side_effect=Exception("Always fail"))):
            for _ in range(3):
                try:
                    client.post("/test", json={"test": "data"})
                except Exception as e:
                    logger.info(f"Expected error: {str(e)}")
        logger.info("Test 4: Checking final statistics")
        final_stats = client.get("/test/stats").json()
        assert final_stats["request_stats"]["failed_requests"] > 0
        assert "error_stats" in final_stats
        logger.info("All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests()) 