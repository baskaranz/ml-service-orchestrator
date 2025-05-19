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
    mock_client = AsyncMock()
    mock_client.request = AsyncMock()
    mock_client.aclose = AsyncMock()
    with patch("httpx.AsyncClient", return_value=mock_client):
        client = HttpClient()
        yield client
        asyncio.run(client.close())


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
    assert client.http2 is True  # Default should be True


def test_init_custom_values():
    """Test HttpClient initialization with custom values."""
    auth_config = MagicMock(spec=AuthConfig)
    client = HttpClient(
        timeout=60.0,
        max_retries=5,
        backoff_factor=1.0,
        auth_config=auth_config,
        http2=False  # Explicitly set to False for this test
    )
    assert client.timeout == 60.0
    assert client.max_retries == 5
    assert client.backoff_factor == 1.0
    assert client.auth_config == auth_config
    assert client.http2 is False  # Should respect custom value


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
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_response.headers = {"Content-Type": "application/json"}
    http_client._client.request.return_value = mock_response
    status, data, headers = await http_client.request(
        "GET",
        "http://example.com",
        headers={"Accept": "application/json"},
        json={"key": "value"},
        params={"param": "value"}
    )
    assert status == 200
    assert data == {"result": "success"}
    assert headers == {"Content-Type": "application/json"}
    http_client._client.request.assert_called_once()
    args = http_client._client.request.call_args[1]
    assert args["method"] == "GET"
    assert args["url"] == "http://example.com"
    assert args["headers"]["Accept"] == "application/json"
    assert args["json"] == {"key": "value"}
    assert args["params"] == {"param": "value"}


@pytest.mark.asyncio
async def test_request_pydantic_model(http_client):
    """Test request with Pydantic model as JSON data."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.headers = {}
    http_client._client.request.return_value = mock_response
    model = TestModel(name="test", value=123)
    await http_client.request(
        "POST",
        "http://example.com",
        json=model
    )
    http_client._client.request.assert_called_once()
    args = http_client._client.request.call_args[1]
    assert args["json"] == {"name": "test", "value": 123}


@pytest.mark.asyncio
async def test_request_json_parse_error(http_client):
    """Test handling response JSON parsing errors."""
    with patch("httpx.Response.json", side_effect=ValueError("Invalid JSON")):
        mock_response = httpx.Response(200, content=b"{invalid json}", headers={})
        http_client._client.request = AsyncMock(return_value=mock_response)
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
    mock_error = httpx.RequestError("Connection error")
    mock_success_response = MagicMock()
    mock_success_response.status_code = 200
    mock_success_response.json.return_value = {"result": "success"}
    mock_success_response.headers = {}
    http_client._client.request = AsyncMock(side_effect=[mock_error, mock_success_response])
    with patch("asyncio.sleep", new_callable=AsyncMock):
        status, data, headers = await http_client.request(
            "GET",
            "http://example.com"
        )
        assert status == 200
        assert data == {"result": "success"}
        asyncio.sleep.assert_called_once()


@pytest.mark.asyncio
async def test_request_max_retries_exceeded(http_client):
    """Test request that fails after max retries."""
    http_client.max_retries = 2
    http_client._client.request = AsyncMock(side_effect=httpx.RequestError("Connection error"))
    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(ModelRequestError):
            await http_client.request("GET", "http://example.com")
        assert asyncio.sleep.call_count == 1
        first_delay = http_client.backoff_factor * (2 ** 0)
        asyncio.sleep.assert_called_once_with(first_delay)


@pytest.mark.asyncio
async def test_request_with_auth(http_client, auth_config_api_key_header):
    """Test request with authentication applied."""
    http_client.auth_config = auth_config_api_key_header
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_response.headers = {}
    http_client._client.request.return_value = mock_response
    await http_client.request(
        "GET",
        "http://example.com",
        headers={"Accept": "application/json"}
    )
    http_client._client.request.assert_called_once()
    args = http_client._client.request.call_args[1]
    assert args["headers"]["X-API-Key"] == "test-api-key"
    assert args["headers"]["Accept"] == "application/json"


@pytest.mark.asyncio
async def test_request_custom_timeout(http_client):
    """Test request with custom timeout."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_response.headers = {}
    http_client._client.request.return_value = mock_response
    await http_client.request(
        "GET",
        "http://example.com",
        timeout=60.0
    )
    http_client._client.request.assert_called_once()
    args = http_client._client.request.call_args[1]
    assert args["timeout"] == 60.0