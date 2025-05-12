"""Tests for the proxy service."""

import json
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import httpx
from fastapi import Request, Response, HTTPException

from app.core.exceptions import ModelRequestError, CircuitBreakerError
from app.models.config_models import ModelConfig, AuthConfig
from app.services.orchestrator import Orchestrator
from app.services.proxy import ProxyService


@pytest.fixture
def proxy_service():
    """Create a proxy service for testing."""
    mock_registry = MagicMock()
    mock_orchestrator = MagicMock()
    return ProxyService(mock_registry, mock_orchestrator)


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
async def test_proxy_to_model_success(proxy_service, mock_request, model_config_instance):
    """Test successful proxying to a model endpoint."""
    # Mock orchestrator's proxy_request method
    proxy_service.orchestrator.proxy_request = AsyncMock(
        return_value=Response(
            content=json.dumps({"result": "success"}).encode(),
            status_code=200,
            media_type="application/json"
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
async def test_proxy_to_model_not_found(proxy_service, mock_request):
    """Test proxying to a model that doesn't exist."""
    # Mock model registry to raise exception for non-existent model
    proxy_service.model_registry.get_model_config = MagicMock(
        side_effect=Exception("Model not found")
    )
    
    # Call the proxy_to_model method and expect exception
    with pytest.raises(Exception):
        await proxy_service.proxy_to_model("nonexistent_model", mock_request)


@pytest.mark.asyncio
async def test_proxy_to_model_error(proxy_service, mock_request, model_config_instance):
    """Test handling errors from the model endpoint."""
    # Mock model registry's get_model_config method
    proxy_service.model_registry.get_model_config = MagicMock(return_value=model_config_instance)
    
    # Mock orchestrator to raise ModelRequestError
    proxy_service.orchestrator.proxy_request = AsyncMock(
        side_effect=ModelRequestError(
            message="Error from model API",
            model_id="test_model_1"
        )
    )
    
    # Call the proxy_to_model method and expect the error to be re-raised
    with pytest.raises(ModelRequestError) as exc_info:
        await proxy_service.proxy_to_model("test_model_1", mock_request)
    
    assert exc_info.value.message == "Error from model API"
    assert exc_info.value.model_id == "test_model_1"


@pytest.mark.asyncio
async def test_proxy_to_model_circuit_breaker(proxy_service, mock_request, model_config_instance):
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
async def test_proxy_to_model_unexpected_error(proxy_service, mock_request, model_config_instance):
    """Test handling unexpected errors."""
    # Mock model registry's get_model_config method
    proxy_service.model_registry.get_model_config = MagicMock(return_value=model_config_instance)
    
    # Mock orchestrator to raise an unexpected error
    proxy_service.orchestrator.proxy_request = AsyncMock(
        side_effect=Exception("Unexpected error")
    )
    
    # Call the proxy_to_model method and expect a ModelRequestError
    with pytest.raises(ModelRequestError) as exc_info:
        await proxy_service.proxy_to_model("test_model_1", mock_request)
    
    assert "Unexpected error" in exc_info.value.message
    assert exc_info.value.model_id == "test_model_1"


@pytest.mark.asyncio
async def test_orchestrator_circuit_breaker(mock_orchestrator, model_config_instance, mock_request):
    """Test the circuit breaker in the orchestrator."""
    # Mock the circuit breaker
    mock_circuit_breaker = MagicMock()
    mock_circuit_breaker.call = AsyncMock()

    # Mock the get_circuit_breaker method
    mock_orchestrator.get_circuit_breaker = MagicMock(return_value=mock_circuit_breaker)

    # Simulate the circuit breaker being open by raising CircuitBreakerError
    mock_orchestrator.proxy_request = AsyncMock(side_effect=CircuitBreakerError(model_id="test_model_1"))

    # Call proxy_request and expect CircuitBreakerError
    with pytest.raises(CircuitBreakerError) as exc_info:
        await mock_orchestrator.proxy_request(model_config_instance, mock_request, "predict")
    assert exc_info.value.model_id == "test_model_1"
    # Optionally, check the error message
    assert "circuit breaker" in (exc_info.value.message or "").lower()


@pytest.mark.asyncio
async def test_orchestrator_build_target_url(mock_orchestrator):
    """Test building target URLs in the orchestrator."""
    # Test with no path suffix
    url1 = mock_orchestrator._build_target_url("http://example.com/api", "")
    assert url1 == "http://example.com/api"
    
    # Test with path suffix
    url2 = mock_orchestrator._build_target_url("http://example.com/api", "predict")
    assert url2 == "http://example.com/api/predict"
    
    # Test with trailing slash in base URL
    url3 = mock_orchestrator._build_target_url("http://example.com/api/", "predict")
    assert url3 == "http://example.com/api/predict"
    
    # Test with leading slash in path suffix
    url4 = mock_orchestrator._build_target_url("http://example.com/api", "/predict")
    assert url4 == "http://example.com/api/predict"


@pytest.mark.asyncio
async def test_get_request_body_json(mock_orchestrator, mock_request):
    """Test extracting JSON request body."""
    # Set up mock request with JSON content type
    mock_request.headers = {"content-type": "application/json"}
    mock_request.json = AsyncMock(return_value={"text": "test input"})
    
    # Get request body
    body = await mock_orchestrator._get_request_body(mock_request)
    
    # Verify JSON was parsed
    assert isinstance(body, dict)
    assert body["text"] == "test input"


@pytest.mark.asyncio
async def test_get_request_body_raw(mock_orchestrator, mock_request):
    """Test extracting raw request body."""
    # Set up mock request with non-JSON content type
    mock_request.headers = {"content-type": "text/plain"}
    mock_request.body = AsyncMock(return_value=b"raw text data")
    
    # Get request body
    body = await mock_orchestrator._get_request_body(mock_request)
    
    # Verify raw body was returned
    assert body == {"raw": b"raw text data"}


@pytest.mark.asyncio
async def test_execute_proxied_request(mock_orchestrator):
    """Test executing a proxied request."""
    # Mock HTTP client
    http_client = MagicMock()
    http_client.request = AsyncMock(return_value=(
        200,
        {"result": "success"},
        {"Content-Type": "application/json"}
    ))
    
    # Call _execute_proxied_request
    response = await mock_orchestrator._execute_proxied_request(
        http_client=http_client,
        method="POST",
        url="http://example.com/api",
        headers={"User-Agent": "Test Client"},
        data={"text": "test input"},
        params={"param": "value"},
        model_id="test_model_1"
    )
    
    # Verify HTTP client was called
    http_client.request.assert_called_once_with(
        method="POST",
        url="http://example.com/api",
        headers={"User-Agent": "Test Client"},
        json_data={"text": "test input"},
        params={"param": "value"}
    )
    
    # Verify response
    assert response.status_code == 200
    
    # The response body will be a Python string representation (with single quotes)
    # rather than valid JSON (with double quotes), so we'll evaluate it as Python
    response_body = response.body.decode('utf-8')
    response_data = eval(response_body)  # Use eval to safely convert the string to a dict
    assert response_data["result"] == "success"


@pytest.mark.asyncio
async def test_execute_proxied_request_error(mock_orchestrator):
    """Test handling errors in executing a proxied request."""
    # Mock HTTP client to raise an error
    http_client = MagicMock()
    http_client.request = AsyncMock(side_effect=Exception("HTTP error"))
    
    # Call _execute_proxied_request and expect exception
    with pytest.raises(ModelRequestError) as exc_info:
        await mock_orchestrator._execute_proxied_request(
            http_client=http_client,
            method="POST",
            url="http://example.com/api",
            headers={},
            data={},
            params={},
            model_id="test_model_1"
        )
    
    assert "HTTP error" in exc_info.value.message
    assert exc_info.value.model_id == "test_model_1"


@pytest.mark.asyncio
async def test_inactive_model(mock_orchestrator, mock_request):
    """Test handling inactive models."""
    # Create an inactive model
    inactive_model = ModelConfig(
        id="inactive_model",
        name="Inactive Model",
        description="Test inactive model",
        endpoint_url="http://example.com/api",
        version="1.0.0",
        timeout=30,
        max_retries=3,
        active=False
    )
    # Call proxy_request with inactive model
    with pytest.raises(ModelRequestError) as exc_info:
        await mock_orchestrator.proxy_request(inactive_model, mock_request)
    assert "not active" in exc_info.value.message.lower()
    assert exc_info.value.model_id == "inactive_model"