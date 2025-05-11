import json
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import httpx
from fastapi import HTTPException
from app.core.exceptions import ModelRequestError

from app.utils.http import HttpClient, build_url, make_request, handle_request_error, create_httpx_client


def test_build_url():
    """Test building URLs with various components."""
    # Base URL only
    assert build_url("http://example.com") == "http://example.com"
    
    # With path
    assert build_url("http://example.com", "api/v1") == "http://example.com/api/v1"
    
    # With query parameters
    assert build_url("http://example.com", query_params={"param1": "value1"}) == "http://example.com?param1=value1"
    
    # With multiple query parameters
    url = build_url("http://example.com", query_params={"param1": "value1", "param2": "value2"})
    assert "param1=value1" in url
    assert "param2=value2" in url
    
    # With path and query parameters
    url = build_url("http://example.com", "api/v1", {"param": "value"})
    assert url == "http://example.com/api/v1?param=value"
    
    # Base URL with trailing slash and path with leading slash
    assert build_url("http://example.com/", "/api/v1") == "http://example.com/api/v1"


@pytest.mark.asyncio
async def test_make_request_success():
    """Test successful HTTP request."""
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    
    # Mock httpx.AsyncClient.request
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        # Make request
        response = await make_request(
            "GET",
            "http://example.com",
            headers={"Content-Type": "application/json"},
            json={"key": "value"},
            timeout=10.0
        )
        
        # Verify response
        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        
        # Verify request was made properly
        mock_request.assert_called_once()
        args = mock_request.call_args[1]
        assert args["method"] == "GET"
        assert args["url"] == "http://example.com"
        assert args["headers"]["Content-Type"] == "application/json"
        assert args["json"] == {"key": "value"}
        assert args["timeout"] == 10.0


@pytest.mark.asyncio
async def test_make_request_error():
    """Test handling HTTP request errors."""
    # Mock httpx.AsyncClient.request to raise an exception
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = httpx.RequestError("Connection error")
        
        # Make request and expect ModelRequestError to be raised
        with pytest.raises(ModelRequestError):
            await make_request("GET", "http://example.com")


def test_handle_request_error():
    """Test handling various request errors."""
    # Test timeout error
    timeout_error = httpx.TimeoutException("Request timed out")
    with pytest.raises(ModelRequestError) as exc_info:
        handle_request_error(timeout_error, "test_model")
    
    assert "timed out" in str(exc_info.value)
    
    # Test connection error
    connection_error = httpx.RequestError("Connection failed")
    with pytest.raises(ModelRequestError) as exc_info:
        handle_request_error(connection_error, "test_model")
    
    assert "Connection failed" in str(exc_info.value)
    
    # Test generic request error
    req_error = httpx.RequestError("General error")
    with pytest.raises(ModelRequestError) as exc_info:
        handle_request_error(req_error, "test_model")
    
    assert "General error" in str(exc_info.value)
    
    # Test other exceptions
    other_error = ValueError("Unexpected error")
    with pytest.raises(ModelRequestError) as exc_info:
        handle_request_error(other_error, "test_model")
    
    assert "Unexpected error" in str(exc_info.value)


def test_create_httpx_client():
    """Test creating an HTTPX client with various parameters."""
    # Create client with defaults
    client = create_httpx_client()
    assert isinstance(client, httpx.AsyncClient)
    
    # Create client with timeout
    client = create_httpx_client(timeout=30.0)
    assert client.timeout.connect == 30.0
    
    # Create client with follow redirects
    client = create_httpx_client(follow_redirects=True)
    assert client.follow_redirects is True
    
    # Create client with custom headers
    client = create_httpx_client(headers={"User-Agent": "Test"})
    assert client.headers.get("User-Agent") == "Test"
