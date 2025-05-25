"""
Tests for the orchestrator service.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from starlette.requests import Request

from app.core.circuit_breaker import CircuitState
from app.core.exceptions import CircuitBreakerError, ModelRequestError
from app.models.config_models import AuthConfig, CircuitBreakerConfig, ModelConfig
from app.services.orchestrator import Orchestrator
from app.utils.http import HttpClient

# Mock __builtins__ for tests
MOCK_BUILTINS = {"ValueError": ValueError, "KeyError": KeyError, "TypeError": TypeError}


@pytest.fixture
def orchestrator():
    """Create an orchestrator for testing."""
    return Orchestrator(config_dir="config/models")


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.headers = {"Content-Type": "application/json"}
    request.query_params = {"param": "value"}
    request.path_params = {"model_id": "test_model", "path_suffix": "predict"}
    request.json = AsyncMock(return_value={"input": "test"})
    request.body = AsyncMock(return_value=b'{"input": "test"}')
    request.url = MagicMock()
    request.url.path = "/models/test_model/predict"
    return request


@pytest.fixture
def mock_model_config():
    """Create a mock model configuration."""
    model_config = MagicMock(spec=ModelConfig)
    model_config.id = "test_model"
    model_config.name = "Test Model"
    model_config.endpoint_url = "http://example.com/model"
    model_config.timeout = 30.0
    model_config.active = True

    # Create a mock platform with circuit breaker config
    platform_mock = MagicMock()
    platform_mock.circuit_breaker = {
        "failure_threshold": 5,
        "recovery_timeout": 30,
        "expected_exceptions": ["ValueError", "KeyError", "TypeError"],
    }
    model_config.platform = platform_mock

    # Old attribute kept for backward compatibility in tests
    model_config.circuit_breaker = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30,
        expected_exceptions=["ValueError", "KeyError", "TypeError"],
    )

    model_config.auth = AuthConfig(type="api_key", api_key="test_api_key")
    return model_config


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = MagicMock(spec=HttpClient)
    client.request = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_build_target_url(orchestrator):
    """Test building target URLs for proxied requests."""
    # Test with a simple URL and no path suffix should raise TypeError (missing required argument)
    with pytest.raises(TypeError):
        orchestrator._build_target_url("http://example.com/model")

    # Test with a URL with a trailing slash and no path suffix should raise TypeError (missing required argument)
    with pytest.raises(TypeError):
        orchestrator._build_target_url("http://example.com/model/")

    # Test with a URL and a path suffix
    url = orchestrator._build_target_url("http://example.com/model", "predict")
    assert url == "http://example.com/model/predict"

    # Test with a URL with a trailing slash and a path suffix
    url = orchestrator._build_target_url("http://example.com/model/", "predict")
    assert url == "http://example.com/model/predict"

    # Test with an empty path suffix
    url = orchestrator._build_target_url("http://example.com/model", "")
    assert url == "http://example.com/model"

    # Test with a path suffix that's just a slash
    url = orchestrator._build_target_url("http://example.com/model", "/")
    assert url == "http://example.com/model"


# The test_get_exclude_exceptions test has been removed as it was testing an internal
# implementation detail that no longer exists in the current version of the code.


@pytest.mark.asyncio
async def test_get_circuit_breaker(orchestrator, mock_model_config):
    """Test getting or creating a circuit breaker for a model."""
    # First call should create a new circuit breaker
    cb1 = orchestrator.get_circuit_breaker(mock_model_config)
    assert cb1 is not None

    # Second call with same model should return the same circuit breaker
    cb2 = orchestrator.get_circuit_breaker(mock_model_config)
    assert cb2 is cb1

    # Call with a different model should return a different circuit breaker
    mock_model_config_2 = MagicMock()
    mock_model_config_2.id = "another_model"
    mock_model_config_2.platform = MagicMock()
    mock_model_config_2.platform.circuit_breaker = {}

    cb3 = orchestrator.get_circuit_breaker(mock_model_config_2)
    assert cb3 is not None
    assert cb3 is not cb1


@pytest.mark.asyncio
async def test_get_request_body_json(orchestrator, mock_request):
    """Test extracting JSON request body."""
    # Mock the request to return JSON data
    mock_request.headers = {"Content-Type": "application/json"}
    mock_request.json = AsyncMock(return_value={"input": "test"})

    # The method should return the raw request body in a dictionary with a 'raw' key
    data = await orchestrator._prepare_request_data(mock_request)
    assert data == {"raw": b'{"input": "test"}'}


@pytest.mark.asyncio
async def test_get_request_body_raw(orchestrator, mock_request):
    """Test extracting raw request body."""
    # Mock the request to return raw data
    mock_request.headers = {"Content-Type": "text/plain"}
    mock_request.body = AsyncMock(return_value=b"raw data")

    data = await orchestrator._prepare_request_data(mock_request)
    assert data == {"raw": b"raw data"}


@pytest.mark.asyncio
async def test_get_request_body_json_error(orchestrator, mock_request):
    """Test handling JSON parsing errors in request body extraction."""
    # Create a mock request with the correct headers and body
    from fastapi import Request

    # Create a mock request with a body that will cause a JSON decode error
    async def mock_receive():
        return {
            "type": "http.request",
            "body": b'{"invalid": "json',  # Invalid JSON (missing closing brace)
            "more_body": False,
        }

    # Create a proper Starlette request with headers
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "path": "/test",
            "headers": [(b"content-type", b"application/json")],
        }
    )

    # Replace the request's receive method with our mock
    request._receive = mock_receive

    # The method should raise ModelRequestError when JSON parsing fails
    with pytest.raises(ModelRequestError) as exc_info:
        await orchestrator._prepare_request_data(request)

    # Check that the error message contains the expected text
    assert "Failed to parse request body" in str(exc_info.value)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_proxy_request_success(
    orchestrator, mock_http_client, mock_model_config, mock_request
):
    """Test successful execution of proxied request."""
    # Setup test data
    mock_model_config.id = "test_model"
    mock_model_config.endpoint_url = "http://example.com/model"
    mock_model_config.timeout = 30.0
    mock_model_config.active = True

    # Add the mock model to the orchestrator's models dictionary
    orchestrator.models[mock_model_config.id] = mock_model_config

    # Mock the request object
    mock_request.method = "POST"
    mock_request.headers = {"Content-Type": "application/json"}
    mock_request.query_params = {"param": "value"}
    mock_request.json = AsyncMock(return_value={"input": "test"})
    mock_request.body = AsyncMock(return_value=b'{"input": "test"}')

    # Create a mock response that matches what the proxy_request method expects
    mock_response = {
        "status_code": 200,
        "content": {"result": "success"},
        "headers": {"Content-Type": "application/json"},
    }

    # Create a mock circuit breaker with CLOSED state
    mock_circuit_breaker = MagicMock()
    mock_circuit_breaker.state = "closed"  # Ensure the circuit breaker is closed
    mock_circuit_breaker.model_id = mock_model_config.id

    # Configure execute_async to actually execute the function and return its result
    async def execute_async_side_effect(func):
        return await func()

    mock_circuit_breaker.execute_async = AsyncMock(side_effect=execute_async_side_effect)

    # Mock the HTTP client to return the mock response
    mock_http_client.request = AsyncMock(return_value=mock_response)

    # Mock the error handler to return the response content
    mock_error_handler = MagicMock()
    mock_error_handler.process_response = AsyncMock(return_value=mock_response["content"])

    # Mock the circuit breaker and HTTP client methods
    with (
        patch.object(
            orchestrator, "_get_http_client", return_value=mock_http_client
        ) as mock_get_client,
        patch.object(
            orchestrator, "get_circuit_breaker", return_value=mock_circuit_breaker
        ) as mock_get_cb,
        patch.object(
            orchestrator, "_get_error_handler", return_value=mock_error_handler
        ) as mock_get_error_handler,
    ):
        # Call the method under test
        response = await orchestrator.proxy_request(
            mock_model_config, mock_request, path_suffix="predict"
        )

        # Verify the circuit breaker was checked
        mock_get_cb.assert_called_once_with(mock_model_config)

        # Verify the HTTP client was used
        mock_get_client.assert_called_once_with(mock_model_config)

        # Verify the request was made with the correct parameters
        mock_http_client.request.assert_called_once()
        call_args = mock_http_client.request.call_args[1]
        assert call_args["method"] == "POST"
        assert call_args["url"] == "http://example.com/model/predict"
        assert call_args["headers"] == {"Content-Type": "application/json"}
        assert call_args["params"] == {"param": "value"}
        # Check for either 'json' or 'data' key in the request arguments
        assert ("json" in call_args and call_args["json"] == {"input": "test"}) or (
            "data" in call_args and call_args["data"] == b'{"input": "test"}'
        )
        assert call_args["timeout"] == 30.0

        # Verify the response is as expected
        assert response == mock_response

        # The error handler's process_response method is not called in the success case
        mock_error_handler.process_response.assert_not_called()

        # Verify the response matches our expected format
        assert isinstance(response, dict)
        assert "status_code" in response
        assert "content" in response
        assert "headers" in response
        assert response["status_code"] == 200
        assert response["content"] == {"result": "success"}


@pytest.mark.asyncio
async def test_proxy_request_error(orchestrator, mock_http_client, mock_model_config, mock_request):
    """Test handling errors in proxied request execution."""
    # Setup test data
    error_message = "Error from model"
    mock_model_config.id = "error_model"
    mock_model_config.endpoint_url = "http://example.com/model"
    mock_model_config.timeout = 30.0
    mock_model_config.active = True

    # Add the mock model to the orchestrator's models dictionary
    orchestrator.models[mock_model_config.id] = mock_model_config

    # Mock the request object
    mock_request.method = "POST"
    mock_request.headers = {"Content-Type": "application/json"}
    mock_request.query_params = {}
    mock_request.json = AsyncMock(return_value={"input": "test"})
    mock_request.body = AsyncMock(return_value=b'{"input": "test"}')

    # Create a mock circuit breaker
    mock_circuit_breaker = MagicMock()
    mock_circuit_breaker.state = "closed"
    mock_circuit_breaker.model_id = mock_model_config.id

    # Configure execute_async to raise an exception
    async def execute_async_side_effect(func):
        raise ModelRequestError(
            message=error_message, status_code=500, model_id=mock_model_config.id
        )

    mock_circuit_breaker.execute_async = AsyncMock(side_effect=execute_async_side_effect)

    # Mock the circuit breaker and HTTP client methods
    with (
        patch.object(
            orchestrator, "_get_http_client", return_value=mock_http_client
        ) as mock_get_client,
        patch.object(
            orchestrator, "get_circuit_breaker", return_value=mock_circuit_breaker
        ) as mock_get_cb,
        patch.object(
            orchestrator, "_get_error_handler", return_value=MagicMock()
        ) as mock_get_error_handler,
    ):
        # Call the method under test and expect a ModelRequestError
        with pytest.raises(ModelRequestError) as exc_info:
            await orchestrator.proxy_request(mock_model_config, mock_request, path_suffix="predict")

        # Verify the circuit breaker was checked
        mock_get_cb.assert_called_once_with(mock_model_config)

        # HTTP client should not be called since we're raising an error in execute_async
        mock_get_client.assert_not_called()
        mock_http_client.request.assert_not_called()

        # Verify error details
        assert error_message in str(exc_info.value)
        assert exc_info.value.status_code == 500
        assert exc_info.value.model_id == mock_model_config.id


@pytest.mark.asyncio
async def test_proxy_request_inactive_model(
    orchestrator, mock_request, mock_model_config, mock_http_client
):
    """Test proxying requests to inactive models."""
    # Setup test data
    mock_model_config.id = "inactive_model"
    mock_model_config.active = False

    # Mock the request object
    mock_request.method = "POST"
    mock_request.headers = {"Content-Type": "application/json"}

    # Call the method under test and expect an exception
    with pytest.raises(ModelRequestError) as exc_info:
        await orchestrator.proxy_request(mock_model_config, mock_request, path_suffix="predict")

    # Verify the error details
    assert "is not active" in str(exc_info.value)
    assert exc_info.value.status_code == 409
    assert exc_info.value.model_id == "inactive_model"

    # Verify no HTTP request was made
    mock_http_client.request.assert_not_called()


@pytest.mark.asyncio
async def test_proxy_request_circuit_breaker_open(
    orchestrator, mock_request, mock_model_config, mock_http_client
):
    """Test proxying requests when circuit breaker is open."""
    # Setup test data
    mock_model_config.id = "circuit_broken_model"
    mock_model_config.active = True
    mock_model_config.endpoint_url = "http://example.com/model"
    mock_model_config.timeout = 30.0

    # Add the mock model to the orchestrator's models dictionary
    orchestrator.models[mock_model_config.id] = mock_model_config

    # Create a mock circuit breaker that's open
    mock_circuit_breaker = MagicMock()
    mock_circuit_breaker.state = "open"
    mock_circuit_breaker.last_failure = 0
    mock_circuit_breaker.failure_count = 10
    mock_circuit_breaker.model_id = (
        mock_model_config.id
    )  # Add model_id to match actual circuit breaker

    # Mock the circuit breaker's execute_async method to raise a CircuitBreakerError
    # This simulates what happens when the circuit breaker is open
    async def mock_execute_async(func):
        raise CircuitBreakerError("Circuit breaker is open", model_id=mock_model_config.id)

    # Mock the request object
    mock_request.method = "POST"
    mock_request.headers = {"Content-Type": "application/json"}
    mock_request.query_params = {}
    mock_request.json = AsyncMock(return_value={"input": "test"})
    mock_request.body = AsyncMock(return_value=b'{"input": "test"}')

    # Mock the error handler to pass through the error
    mock_error_handler = MagicMock()
    mock_error_handler.process_response = AsyncMock(side_effect=lambda x: x)

    # Configure the circuit breaker's execute_async method
    mock_circuit_breaker.execute_async = mock_execute_async

    # Mock the circuit breaker and HTTP client methods
    with (
        patch.object(
            orchestrator, "_get_http_client", return_value=mock_http_client
        ) as mock_get_client,
        patch.object(
            orchestrator, "get_circuit_breaker", return_value=mock_circuit_breaker
        ) as mock_get_cb,
        patch.object(
            orchestrator, "_get_error_handler", return_value=mock_error_handler
        ) as mock_get_error_handler,
    ):
        # Call the method under test and expect a ModelRequestError
        with pytest.raises(ModelRequestError) as exc_info:
            await orchestrator.proxy_request(mock_model_config, mock_request, path_suffix="predict")

        # The HTTP client and its getter should not be called when circuit is open
        mock_get_client.assert_not_called()
        mock_http_client.request.assert_not_called()

        # Verify the error message indicates the circuit is open
        assert "Failed to proxy request to model" in str(exc_info.value)
        assert "Circuit breaker is open" in str(exc_info.value)
        assert hasattr(exc_info.value, "model_id")
        assert exc_info.value.model_id == mock_model_config.id
        assert hasattr(exc_info.value, "status_code")
        assert exc_info.value.status_code == 500


# The following test is commented out because CircuitBreakerListener is not implemented
# def test_circuit_breaker_listener():
#     # Test implementation would go here
#     pass
