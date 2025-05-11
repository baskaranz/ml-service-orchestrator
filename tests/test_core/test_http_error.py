"""Test HTTP exception handling."""
import pytest
import json
from fastapi import Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import http_error_handler


@pytest.fixture
def mock_request():
    """Create a mock request for testing."""
    return Request(scope={"type": "http", "path": "/test"})


@pytest.mark.asyncio
async def test_http_error_handler(mock_request):
    """Test handling of HTTPException."""
    # Create a test exception
    exc = StarletteHTTPException(status_code=400, detail="Test error")
    
    # Handle the exception
    response = await http_error_handler(mock_request, exc)
    
    # Verify response
    assert response.status_code == 400
    data = json.loads(response.body.decode())
    assert data["error"] == "Test error"
    assert data["code"] == "HTTP_400"
