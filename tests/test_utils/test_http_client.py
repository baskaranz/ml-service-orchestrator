"""
Tests for HTTP client utilities.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
import httpx
import asyncio
from pydantic import BaseModel

from app.models.config_models import AuthConfig, AuthLocation, AuthType
from app.utils.http import HttpClient
from app.core.exceptions import ModelRequestError


class TestModel(BaseModel):
    """Test model for Pydantic serialization."""
    name: str
    value: int


@pytest.fixture
def http_client():
    """Create a default HTTP client for testing."""
    return HttpClient()


@pytest.fixture
def auth_config_api_key_header():
    """Create an API key auth config with header location."""
    auth = MagicMock(spec=AuthConfig)
    auth.type = AuthType.API_KEY
    auth.location = AuthLocation.HEADER
    auth.key_name = "X-API-Key"
    auth.key_value = "test-api-key"
    return auth


@pytest.fixture
def auth_config_api_key_query():
    """Create an API key auth config with query location."""
    auth = MagicMock(spec=AuthConfig)
    auth.type = AuthType.API_KEY
    auth.location = AuthLocation.QUERY
    auth.key_name = "api_key"
    auth.key_value = "test-api-key"
    return auth


@pytest.fixture
def auth_config_bearer_token():
    """Create a bearer token auth config."""
    auth = MagicMock(spec=AuthConfig)
    auth.type = AuthType.BEARER_TOKEN
    auth.key_value = "test-token"
    return auth


@pytest.fixture
def auth_config_basic():
    """Create a basic auth config."""
    auth = MagicMock(spec=AuthConfig)
    auth.type = AuthType.BASIC_AUTH
    auth.username = "user"
    auth.password = "pass"
    return auth


def test_init_defaults():
    """Test HttpClient initialization with defaults."""
    client = HttpClient()
    assert client.timeout == 30.0
    assert client.max_retries == 3
    assert client.backoff_factor == 0.5
    assert client.auth_config is not None
    assert client.auth_config.get('type', None) is None


def test_init_custom_values():
    """Test HttpClient initialization with custom values."""
    auth_config = MagicMock(spec=AuthConfig)
    client = HttpClient(
        timeout=60.0,
        max_retries=5,
        backoff_factor=1.0,
        auth_config=auth_config
    )
    assert client.timeout == 60.0
    assert client.max_retries == 5
    assert client.backoff_factor == 1.0
    assert client.auth_config == auth_config


def test_apply_auth_none(http_client):
    """Test applying no authentication."""
    headers = {}
    params = {}
    http_client._apply_auth(headers, params)
    assert headers == {}
    assert params == {}


def test_apply_auth_api_key_header(http_client, auth_config_api_key_header):
    """Test applying API key authentication in header."""
    http_client.auth_config = auth_config_api_key_header
    headers = {}
    params = {}
    http_client._apply_auth(headers, params)
    assert headers == {"X-API-Key": "test-api-key"}
    assert params == {}


def test_apply_auth_api_key_query(http_client, auth_config_api_key_query):
    """Test applying API key authentication in query params."""
    http_client.auth_config = auth_config_api_key_query
    headers = {}
    params = {}
    http_client._apply_auth(headers, params)
    assert headers == {}
    assert params == {"api_key": "test-api-key"}


def test_apply_auth_bearer_token(http_client, auth_config_bearer_token):
    """Test applying bearer token authentication."""
    http_client.auth_config = auth_config_bearer_token
    headers = {}
    params = {}
    http_client._apply_auth(headers, params)
    assert headers == {"Authorization": "Bearer test-token"}
    assert params == {}


def test_apply_auth_basic(http_client, auth_config_basic):
    """Test applying basic authentication."""
    http_client.auth_config = auth_config_basic
    headers = {}
    params = {}
    http_client._apply_auth(headers, params)
    assert 'Authorization' in headers
    assert headers['Authorization'].startswith('Basic ')


@pytest.mark.asyncio
async def test_request_success(http_client):
    """Test successful HTTP request."""
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_response.headers = {"Content-Type": "application/json"}
    
    # Mock client context manager
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)
    mock_client_context = MagicMock()
    mock_client_context.__aenter__.return_value = mock_client
    mock_client_context.__aexit__.return_value = None
    
    # Patch httpx.AsyncClient to return our mock
    with patch("httpx.AsyncClient", return_value=mock_client_context):
        status, data, headers = await http_client.request(
            "GET",
            "http://example.com",
            headers={"Accept": "application/json"},
            json_data={"key": "value"},
            params={"param": "value"}
        )
        
        # Verify response
        assert status == 200
        assert data == {"result": "success"}
        assert headers == {"Content-Type": "application/json"}
        
        # Verify request was made properly
        mock_client.request.assert_called_once()
        args = mock_client.request.call_args[1]
        assert args["method"] == "GET"
        assert args["url"] == "http://example.com"
        assert args["headers"]["Accept"] == "application/json"
        assert args["json"] == {"key": "value"}
        assert args["params"] == {"param": "value"}


@pytest.mark.asyncio
async def test_request_pydantic_model(http_client):
    """Test request with Pydantic model as JSON data."""
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.headers = {}
    
    # Mock client context manager
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)
    mock_client_context = MagicMock()
    mock_client_context.__aenter__.return_value = mock_client
    mock_client_context.__aexit__.return_value = None
    
    # Create a Pydantic model
    model = TestModel(name="test", value=123)
    
    # Patch httpx.AsyncClient to return our mock
    with patch("httpx.AsyncClient", return_value=mock_client_context):
        await http_client.request(
            "POST",
            "http://example.com",
            json_data=model
        )
        
        # Verify JSON serialization
        mock_client.request.assert_called_once()
        args = mock_client.request.call_args[1]
        assert args["json"] == {"name": "test", "value": 123}


@pytest.mark.asyncio
async def test_request_json_parse_error(http_client):
    """Test handling response JSON parsing errors."""
    # Use patch to intercept response.json() and make it raise an error
    with patch("httpx.Response.json", side_effect=ValueError("Invalid JSON")):
        # Mock status code 200 but invalid JSON response
        mock_response = httpx.Response(200, content=b"{invalid json}", headers={})
        
        # Mock client to return our mock response
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, 
                  return_value=mock_response):
            # Now the test should raise ModelRequestError when parsing the response
            with pytest.raises(ModelRequestError):
                await http_client.request(
                    method="GET",
                    url="http://test.com/api",
                    headers={},
                    params={}
                )


@pytest.mark.asyncio
async def test_request_with_retry_success(http_client):
    """Test request with retry that eventually succeeds."""
    # Mock responses - first one fails, second succeeds
    mock_error_response = MagicMock()
    mock_error_response.request = AsyncMock(side_effect=httpx.RequestError("Connection error"))
    
    mock_success_response = MagicMock()
    mock_success_response.status_code = 200
    mock_success_response.json.return_value = {"result": "success"}
    mock_success_response.headers = {}
    
    # Mock clients
    mock_error_client = AsyncMock()
    mock_error_client.request = AsyncMock(side_effect=httpx.RequestError("Connection error"))
    mock_error_client_context = MagicMock()
    mock_error_client_context.__aenter__.return_value = mock_error_client
    mock_error_client_context.__aexit__.return_value = None
    
    mock_success_client = AsyncMock()
    mock_success_client.request = AsyncMock(return_value=mock_success_response)
    mock_success_client_context = MagicMock()
    mock_success_client_context.__aenter__.return_value = mock_success_client
    mock_success_client_context.__aexit__.return_value = None
    
    # Patch httpx.AsyncClient and asyncio.sleep
    with patch("httpx.AsyncClient", side_effect=[mock_error_client_context, mock_success_client_context]), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        
        status, data, headers = await http_client.request(
            "GET",
            "http://example.com"
        )
        
        # Verify response
        assert status == 200
        assert data == {"result": "success"}
        
        # Verify sleep was called
        asyncio.sleep.assert_called_once()


@pytest.mark.asyncio
async def test_request_max_retries_exceeded(http_client):
    """Test request that fails after max retries."""
    # Set low retry count for faster test
    http_client.max_retries = 2
    
    # Mock client that always fails
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=httpx.RequestError("Connection error"))
    mock_client_context = MagicMock()
    mock_client_context.__aenter__.return_value = mock_client
    mock_client_context.__aexit__.return_value = None
    
    # Patch httpx.AsyncClient and asyncio.sleep
    with patch("httpx.AsyncClient", return_value=mock_client_context), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        
        # Expect ModelRequestError after all retries
        with pytest.raises(ModelRequestError):
            await http_client.request("GET", "http://example.com")
        
        # Verify sleep was called once (for 2 attempts, 1 sleep)
        assert asyncio.sleep.call_count == 1
        # Verify the first backoff call
        first_delay = http_client.backoff_factor * (2 ** 0)  # 0.5 * 1 = 0.5
        asyncio.sleep.assert_called_once_with(first_delay)


@pytest.mark.asyncio
async def test_request_with_auth(http_client, auth_config_api_key_header):
    """Test request with authentication applied."""
    # Set auth config
    http_client.auth_config = auth_config_api_key_header
    
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_response.headers = {}
    
    # Mock client
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)
    mock_client_context = MagicMock()
    mock_client_context.__aenter__.return_value = mock_client
    mock_client_context.__aexit__.return_value = None
    
    # Patch httpx.AsyncClient
    with patch("httpx.AsyncClient", return_value=mock_client_context):
        await http_client.request(
            "GET",
            "http://example.com",
            headers={"Accept": "application/json"}
        )
        
        # Verify auth header was added
        mock_client.request.assert_called_once()
        args = mock_client.request.call_args[1]
        assert args["headers"]["X-API-Key"] == "test-api-key"
        assert args["headers"]["Accept"] == "application/json"


@pytest.mark.asyncio
async def test_request_custom_timeout(http_client):
    """Test request with custom timeout."""
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_response.headers = {}
    
    # Mock client
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)
    mock_client_context = MagicMock()
    mock_client_context.__aenter__.return_value = mock_client
    mock_client_context.__aexit__.return_value = None
    
    # Patch httpx.AsyncClient
    with patch("httpx.AsyncClient", return_value=mock_client_context):
        # Use custom timeout
        await http_client.request(
            "GET",
            "http://example.com",
            timeout=60.0
        )