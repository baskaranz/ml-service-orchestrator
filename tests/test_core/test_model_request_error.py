"""Test ModelRequestError handling."""
import pytest
import json
from fastapi import Request
from app.core.exceptions import ModelRequestError, model_request_error_handler


@pytest.fixture
def mock_request():
    """Create a mock request for testing."""
    return Request(scope={"type": "http", "path": "/test"})


@pytest.mark.asyncio
async def test_model_request_error_handler(mock_request):
    """Test handling of ModelRequestError."""
    # Create a test exception
    exc = ModelRequestError(
        message="Model request failed", 
        status_code=502, 
        model_id="test_model",
        details={"reason": "Connection error"}
    )
    
    # Handle the exception
    response = await model_request_error_handler(mock_request, exc)
    
    # Verify response
    assert response.status_code == 502
    data = json.loads(response.body.decode())
    assert data["error"] == "Model request failed"
    assert data["code"] == "MODEL_REQUEST_ERROR"
    assert data["details"] == {"reason": "Connection error"}
