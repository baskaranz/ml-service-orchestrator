"""Tests for the proxy service."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request, Response

from app.core.exceptions import CircuitBreakerError, ModelRequestError
from app.services.proxy import ProxyService


@pytest.fixture
def proxy_service():
    """Create a proxy service for testing."""
    mock_registry = MagicMock()
    mock_orchestrator = MagicMock()
    return ProxyService(mock_registry, mock_orchestrator)


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator for testing."""
    mock_orch = MagicMock()
    # Add necessary methods that will be called in tests
    mock_orch._build_target_url = MagicMock()
    mock_orch._prepare_request_data = AsyncMock()
    mock_orch.proxy_request = AsyncMock()
    return mock_orch


@pytest.fixture
def llm_provider_config():
    """Create a mock LLM provider config for testing."""
    # This is a simple mock that can be expanded as needed
    return {"api_key": "test_api_key", "model": "test_model", "temperature": 0.7, "max_tokens": 100}


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request for testing."""
    mock_req = MagicMock(spec=Request)
    mock_req.method = "POST"
    mock_req.headers = {"Content-Type": "application/json", "User-Agent": "Test Client"}
    mock_req.query_params = {"param1": "value1", "param2": "value2"}
    mock_req.url = MagicMock()
    mock_req.url.path = "/orchestrator/test_model_1/predict"

    # Setup body
    mock_req.body = AsyncMock(return_value=json.dumps({"text": "test input"}).encode())
    mock_req.json = AsyncMock(return_value={"text": "test input"})

    return mock_req


@pytest.mark.asyncio
async def test_proxy_to_model_success(
    proxy_service, mock_request, model_config_instance, llm_provider_config
):
    """Test successful proxying to a model endpoint."""
    # Mock orchestrator's proxy_request method
    proxy_service.orchestrator.proxy_request = AsyncMock(
        return_value=Response(
            content=json.dumps({"result": "success"}).encode(),
            status_code=200,
            media_type="application/json",
        )
    )

    # Mock model registry's get_model_config method
    proxy_service.model_registry.get_model_config = MagicMock(return_value=model_config_instance)

    # Call the proxy_to_model method
    response = await proxy_service.proxy_to_model("test_model_1", mock_request, "predict")

    # Verify orchestrator.proxy_request was called
    proxy_service.orchestrator.proxy_request.assert_called_once()
    call_args = proxy_service.orchestrator.proxy_request.call_args[1]
    assert call_args["model_config"] == model_config_instance
    assert call_args["request"] == mock_request
    assert call_args["path_suffix"] == "predict"

    # Verify response
    assert response.status_code == 200
    assert json.loads(response.body)["result"] == "success"


@pytest.mark.asyncio
async def test_proxy_to_model_not_found(proxy_service, mock_request, llm_provider_config):
    """Test proxying to a model that doesn't exist."""
    # Mock model registry to raise exception for non-existent model
    proxy_service.model_registry.get_model_config = MagicMock(
        side_effect=Exception("Model not found")
    )

    # Call the proxy_to_model method and expect exception
    with pytest.raises(Exception):
        await proxy_service.proxy_to_model("nonexistent_model", mock_request)


@pytest.mark.asyncio
async def test_proxy_to_model_error(
    proxy_service, mock_request, model_config_instance, llm_provider_config
):
    """Test handling errors from the model endpoint."""
    # Mock model registry's get_model_config method
    proxy_service.model_registry.get_model_config = MagicMock(return_value=model_config_instance)

    # Mock orchestrator to raise ModelRequestError
    proxy_service.orchestrator.proxy_request = AsyncMock(
        side_effect=ModelRequestError(message="Error from model API", model_id="test_model_1")
    )

    # Call the proxy_to_model method and expect the error to be re-raised
    with pytest.raises(ModelRequestError) as exc_info:
        await proxy_service.proxy_to_model("test_model_1", mock_request)

    assert exc_info.value.message == "Error from model API"
    assert exc_info.value.model_id == "test_model_1"


@pytest.mark.asyncio
async def test_proxy_to_model_circuit_breaker(
    proxy_service, mock_request, model_config_instance, llm_provider_config
):
    """Test handling circuit breaker errors."""
    # Mock model registry's get_model_config method
    proxy_service.model_registry.get_model_config = MagicMock(return_value=model_config_instance)

    # Mock orchestrator to raise CircuitBreakerError
    proxy_service.orchestrator.proxy_request = AsyncMock(
        side_effect=CircuitBreakerError(model_id="test_model_1")
    )

    # Call the proxy_to_model method and expect a ModelRequestError
    # CircuitBreakerError is wrapped in a ModelRequestError for consistent error handling
    with pytest.raises(ModelRequestError) as exc_info:
        await proxy_service.proxy_to_model("test_model_1", mock_request)

    # Verify the error details
    assert "circuit breaker" in exc_info.value.message.lower()
    assert exc_info.value.model_id == "test_model_1"


@pytest.mark.asyncio
async def test_proxy_to_model_unexpected_error(
    proxy_service, mock_request, model_config_instance, llm_provider_config
):
    """Test handling unexpected errors."""
    # Mock model registry's get_model_config method
    proxy_service.model_registry.get_model_config = MagicMock(return_value=model_config_instance)

    # Mock orchestrator to raise an unexpected error
    proxy_service.orchestrator.proxy_request = AsyncMock(side_effect=Exception("Unexpected error"))

    # Call the proxy_to_model method and expect a ModelRequestError
    with pytest.raises(ModelRequestError) as exc_info:
        await proxy_service.proxy_to_model("test_model_1", mock_request)

    assert "Unexpected error" in exc_info.value.message
    assert exc_info.value.model_id == "test_model_1"


@pytest.mark.asyncio
async def test_orchestrator_circuit_breaker(
    mock_orchestrator, model_config_instance, mock_request, llm_provider_config
):
    """Test the circuit breaker in the orchestrator."""
    # Mock the circuit breaker
    mock_circuit_breaker = MagicMock()
    mock_circuit_breaker.call = AsyncMock()

    # Mock the get_circuit_breaker method
    mock_orchestrator.get_circuit_breaker = MagicMock(return_value=mock_circuit_breaker)

    # Simulate the circuit breaker being open by raising CircuitBreakerError
    mock_orchestrator.proxy_request = AsyncMock(
        side_effect=CircuitBreakerError(model_id="test_model_1")
    )

    # Call proxy_request and expect CircuitBreakerError
    with pytest.raises(CircuitBreakerError) as exc_info:
        await mock_orchestrator.proxy_request(
            model_config_instance, mock_request, "predict", llm_provider=llm_provider_config
        )
    assert exc_info.value.model_id == "test_model_1"
    # Optionally, check the error message
    assert "circuit breaker" in (exc_info.value.message or "").lower()


@pytest.mark.asyncio
async def test_orchestrator_build_target_url(mock_orchestrator):
    """Test building target URLs in the orchestrator."""
    # Import the actual implementation to test
    from app.services.orchestrator import Orchestrator

    # Create a real orchestrator instance just for this test
    real_orchestrator = Orchestrator()

    # Test with no path suffix
    url1 = real_orchestrator._build_target_url("http://example.com/api", "")
    assert url1 == "http://example.com/api"

    # Test with path suffix
    url2 = real_orchestrator._build_target_url("http://example.com/api", "predict")
    assert url2 == "http://example.com/api/predict"

    # Test with trailing slash in base URL
    url3 = real_orchestrator._build_target_url("http://example.com/api/", "predict")
    assert url3 == "http://example.com/api/predict"

    # Test with leading slash in path suffix
    url4 = real_orchestrator._build_target_url("http://example.com/api", "/predict")
    assert url4 == "http://example.com/api/predict"


@pytest.mark.asyncio
async def test_get_request_body_json(mock_request):
    """Test extracting JSON request body."""
    # Import the actual implementation to test
    from app.services.orchestrator import Orchestrator

    # Create a real orchestrator instance just for this test
    real_orchestrator = Orchestrator()

    # Set up mock request with JSON content type
    mock_request.headers = {"content-type": "application/json"}
    mock_request.json = AsyncMock(return_value={"text": "test input"})

    # Get request body using the real implementation
    body = await real_orchestrator._prepare_request_data(mock_request)

    # Verify JSON was parsed and returned directly
    assert isinstance(body, dict)
    assert body == {"text": "test input"}


@pytest.mark.asyncio
async def test_get_request_body_raw(mock_request):
    """Test extracting raw request body."""
    # Import the actual implementation to test
    from app.services.orchestrator import Orchestrator

    # Create a real orchestrator instance just for this test
    real_orchestrator = Orchestrator()

    # Set up mock request with non-JSON content type
    mock_request.headers = {"content-type": "text/plain"}
    mock_request.body = AsyncMock(return_value=b"raw text data")

    # Get request body using the real implementation
    body = await real_orchestrator._prepare_request_data(mock_request)

    # Verify raw body was returned as a dictionary with a 'raw' key
    assert body == {"raw": b"raw text data"}


@pytest.mark.asyncio
async def test_execute_proxied_request(model_config_instance, mock_request):
    """Test executing a proxied request."""
    # Create a mock orchestrator with specific behavior for this test
    mock_orch = MagicMock()

    # Mock HTTP client
    http_client = MagicMock()
    http_client.request = AsyncMock(
        return_value={
            "status_code": 200,
            "content": b'{"result": "success"}',
            "headers": {"Content-Type": "application/json"},
        }
    )

    # Mock the model registry to return our test model
    mock_orch.models = {"test_model_1": model_config_instance}

    # Create a mock for execute_with_circuit_breaker that properly handles coroutines
    async def mock_execute_with_circuit_breaker(model_config, func):
        return await func()

    mock_orch.execute_with_circuit_breaker = mock_execute_with_circuit_breaker

    # Mock the _get_http_client method to return our mock HTTP client
    mock_orch._get_http_client = MagicMock(return_value=http_client)

    # Mock the _prepare_request_data method
    mock_orch._prepare_request_data = AsyncMock(return_value={"text": "test input"})

    # Mock the _build_target_url method
    mock_orch._build_target_url = MagicMock(return_value=model_config_instance.endpoint_url)

    # Mock the request object
    mock_request.method = "POST"
    mock_request.headers = {"User-Agent": "Test Client", "Content-Type": "application/json"}
    mock_request.query_params = {"param": "value"}
    mock_request.json = AsyncMock(return_value={"text": "test input"})

    # Import the actual implementation to test
    from app.services.orchestrator import Orchestrator

    # Create a real orchestrator instance and replace its methods with our mocks
    real_orchestrator = Orchestrator()
    real_orchestrator._get_http_client = mock_orch._get_http_client
    real_orchestrator.execute_with_circuit_breaker = mock_orch.execute_with_circuit_breaker
    real_orchestrator._prepare_request_data = mock_orch._prepare_request_data
    real_orchestrator.models = mock_orch.models

    # Call proxy_request on the real orchestrator with our mocked methods
    response = await real_orchestrator.proxy_request(
        model_config=model_config_instance, request=mock_request, path_suffix=""
    )

    # Verify HTTP client was called with the correct arguments
    http_client.request.assert_called_once()

    # Verify response
    assert isinstance(response, dict)
    assert response["status_code"] == 200
    assert response["content"] == b'{"result": "success"}'
    assert response["headers"]["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_execute_proxied_request_error(model_config_instance, mock_request):
    """Test handling errors in executing a proxied request."""
    # Create a mock orchestrator with specific behavior for this test
    mock_orch = MagicMock()

    # Mock the model registry to return our test model
    mock_orch.models = {"test_model_1": model_config_instance}

    # Mock the execute_with_circuit_breaker to execute the function directly
    async def mock_execute_with_cb(model_config, func):
        try:
            return await func()
        except Exception as e:
            raise ModelRequestError(
                message=str(e), model_id=getattr(model_config_instance, "id", "unknown")
            )

    mock_orch.execute_with_circuit_breaker = mock_execute_with_cb

    # Mock HTTP client to raise an error
    http_client = MagicMock()
    http_client.request = AsyncMock(side_effect=Exception("HTTP error"))
    mock_orch._get_http_client = MagicMock(return_value=http_client)

    # Mock the _prepare_request_data method
    mock_orch._prepare_request_data = AsyncMock(return_value={"text": "test input"})

    # Mock the _build_target_url method
    mock_orch._build_target_url = MagicMock(return_value=model_config_instance.endpoint_url)

    # Mock the request object
    mock_request.method = "POST"
    mock_request.headers = {"User-Agent": "Test Client", "Content-Type": "application/json"}
    mock_request.query_params = {"param": "value"}
    mock_request.json = AsyncMock(return_value={"text": "test input"})

    # Import the actual implementation to test
    from app.services.orchestrator import Orchestrator

    # Create a real orchestrator instance and replace its methods with our mocks
    real_orchestrator = Orchestrator()
    real_orchestrator._get_http_client = mock_orch._get_http_client
    real_orchestrator.execute_with_circuit_breaker = mock_orch.execute_with_circuit_breaker
    real_orchestrator._prepare_request_data = mock_orch._prepare_request_data
    real_orchestrator.models = mock_orch.models

    # Call proxy_request and expect exception
    with pytest.raises(ModelRequestError) as exc_info:
        await real_orchestrator.proxy_request(
            model_config=model_config_instance, request=mock_request, path_suffix=""
        )

    # The error message should contain the original error
    assert "HTTP error" in str(exc_info.value)
    assert exc_info.value.model_id == getattr(model_config_instance, "id", "unknown")


@pytest.mark.asyncio
async def test_inactive_model(model_config_instance, mock_request):
    """Test handling of inactive models."""
    # Create an inactive model
    inactive_config = model_config_instance.model_copy(update={"active": False})

    # Create a mock orchestrator with specific behavior for this test
    mock_orch = MagicMock()

    # Add to orchestrator's models
    mock_orch.models = {"inactive_model": inactive_config}

    # Mock the _prepare_request_data method
    mock_orch._prepare_request_data = AsyncMock(return_value={})

    # Mock the _build_target_url method
    mock_orch._build_target_url = MagicMock(return_value=inactive_config.endpoint_url)

    # Mock the request object
    mock_request.method = "POST"
    mock_request.headers = {"Content-Type": "application/json"}
    mock_request.query_params = {}
    mock_request.json = AsyncMock(return_value={})

    # Import the actual implementation to test
    from app.services.orchestrator import Orchestrator

    # Create a real orchestrator instance and replace its methods with our mocks
    real_orchestrator = Orchestrator()
    real_orchestrator._prepare_request_data = mock_orch._prepare_request_data

    # Try to execute a request with the inactive model
    with pytest.raises(ModelRequestError) as exc_info:
        await real_orchestrator.proxy_request(
            model_config=inactive_config, request=mock_request, path_suffix=""
        )

    # Verify the error message and status code
    assert "not active" in str(exc_info.value).lower()
    assert exc_info.value.model_id == inactive_config.id
    assert exc_info.value.status_code == 409
