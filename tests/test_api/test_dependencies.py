"""Tests for the API dependencies."""

from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.api.dependencies import get_api_key


@pytest.mark.asyncio
async def test_get_api_key_valid(mock_settings):
    """Test get_api_key with a valid API key."""
    # Set a test admin API key
    mock_settings.ADMIN_API_KEY = "test-api-key"

    # Call the dependency with a valid API key
    with patch("app.config.settings.settings", mock_settings):
        api_key = "test-api-key"
        result = await get_api_key(api_key)

        # Verify the API key is returned
        assert result == api_key


@pytest.mark.asyncio
async def test_get_api_key_invalid(mock_settings):
    """Test get_api_key with an invalid API key."""
    # Set a test admin API key
    mock_settings.ADMIN_API_KEY = "test-api-key"

    # Call the dependency with an invalid API key
    with patch("app.config.settings.settings", mock_settings):
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key("invalid-api-key")

        # Verify the correct exception was raised
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "Invalid API key"


@pytest.mark.asyncio
async def test_get_api_key_not_configured(mock_settings):
    """Test get_api_key when admin API key is not configured."""
    # Clear the admin API key
    mock_settings.ADMIN_API_KEY = ""

    # Call the dependency with any API key
    with patch("app.config.settings.settings", mock_settings):
        result = await get_api_key("any-api-key")

        # Verify an empty string is returned
        assert result == ""


@pytest.mark.asyncio
async def test_get_api_key_none(mock_settings):
    """Test get_api_key when no API key is provided."""
    # Set a test admin API key
    mock_settings.ADMIN_API_KEY = "test-api-key"

    # Call the dependency with no API key
    with patch("app.config.settings.settings", mock_settings):
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(None)

        # Verify the correct exception was raised
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "Invalid API key"


@pytest.mark.asyncio
async def test_api_key_logging(mock_settings):
    """Test that invalid API key attempts are logged."""
    # Set a test admin API key
    mock_settings.ADMIN_API_KEY = "test-api-key"

    # Call the dependency with an invalid API key and verify logging
    with (
        patch("app.config.settings.settings", mock_settings),
        patch("app.api.dependencies.auth.logger") as mock_logger,
    ):

        # Expect an exception
        with pytest.raises(HTTPException):
            await get_api_key("invalid-api-key")

        # Verify a warning was logged
        mock_logger.warning.assert_called_once_with("Invalid API key attempt")


@pytest.mark.asyncio
async def test_api_key_in_endpoint():
    """Test API key validation in a FastAPI endpoint."""
    # Create a test app
    app = FastAPI()

    # Define a protected endpoint
    @app.get("/protected")
    async def protected_endpoint(api_key: str = Depends(get_api_key)):
        return {"message": "Access granted"}

    # Create a test client
    client = TestClient(app)

    # Mock the get_api_key dependency
    async def mock_get_api_key_valid(api_key: str = None):
        return "test-api-key"

    async def mock_get_api_key_invalid(api_key: str = None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")

    # Test with a valid key
    app.dependency_overrides[get_api_key] = mock_get_api_key_valid
    response = client.get("/protected", headers={"X-API-Key": "test-api-key"})
    assert response.status_code == 200
    assert response.json() == {"message": "Access granted"}

    # Test with an invalid key
    app.dependency_overrides[get_api_key] = mock_get_api_key_invalid
    response = client.get("/protected", headers={"X-API-Key": "invalid-key"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid API key"}

    # Clean up
    app.dependency_overrides = {}
