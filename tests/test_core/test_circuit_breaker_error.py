"""Test CircuitBreakerError handling."""

import json

import pytest
from fastapi import Request

from app.core.exceptions import CircuitBreakerError, circuit_breaker_error_handler


@pytest.fixture
def mock_request():
    """Create a mock request for testing."""
    return Request(scope={"type": "http", "path": "/test"})


@pytest.mark.asyncio
async def test_circuit_breaker_error_handler(mock_request):
    """Test handling of CircuitBreakerError."""
    # Create a test exception
    exc = CircuitBreakerError(message="Service temporarily unavailable", model_id="test_model")

    # Handle the exception
    response = await circuit_breaker_error_handler(mock_request, exc)

    # Verify response
    assert response.status_code == 503  # Service Unavailable
    data = json.loads(response.body.decode())
    assert data["error"] == "Service temporarily unavailable"
    assert data["code"] == "CIRCUIT_BREAKER_OPEN"
    assert data["details"] == {"model_id": "test_model"}
