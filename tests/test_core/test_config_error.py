"""Test ConfigurationError handling."""

import json

import pytest
from fastapi import Request

from app.core.exceptions import ConfigurationError, configuration_error_handler


@pytest.fixture
def mock_request():
    """Create a mock request for testing."""
    return Request(scope={"type": "http", "path": "/test"})


@pytest.mark.asyncio
async def test_configuration_error_handler(mock_request):
    """Test handling of ConfigurationError."""
    # Create a test exception
    exc = ConfigurationError(
        message="Invalid configuration",
        details={"config_file": "models.yaml", "issue": "missing required field"},
    )

    # Handle the exception
    response = await configuration_error_handler(mock_request, exc)

    # Verify response
    assert response.status_code == 500  # Internal Server Error
    data = json.loads(response.body.decode())
    assert data["error"] == "Invalid configuration"
    assert data["code"] == "CONFIGURATION_ERROR"
    assert data["details"] == {"config_file": "models.yaml", "issue": "missing required field"}
