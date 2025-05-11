"""Advanced tests for the proxy service."""

import json
import logging
from unittest.mock import patch, AsyncMock, MagicMock, call

import pytest
from fastapi import Request, Response

from app.core.exceptions import ModelRequestError, CircuitBreakerError
from app.models.config_models import ModelConfig
from app.services.orchestrator import Orchestrator
from app.services.model_registry import ModelRegistryService
from app.services.proxy import ProxyService


@pytest.fixture
def mock_request():
    """Create a mock request for testing."""
    # Create a mock request
    mock_req = MagicMock(spec=Request)
    
    # Setup basic attributes
    mock_req.method = "GET"
    mock_req.headers = {"Content-Type": "application/json"}
    
    # Setup URL
    mock_req.url = MagicMock()
    mock_req.url.path = "/models/test-model"
    
    return mock_req


@pytest.fixture
def advanced_request():
    """Create a more advanced mock request for testing."""
    # Create a mock request
    mock_req = MagicMock(spec=Request)
    
    # Setup basic attributes
    mock_req.method = "POST"
    mock_req.headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-token",
        "X-Request-ID": "test-request-id"
    }
    mock_req.query_params = {"version": "v2", "debug": "true"}
    
    # Setup URL
    mock_req.url = MagicMock()
    mock_req.url.path = "/models/test-model/classify"
    mock_req.url.query = "version=v2&debug=true"
    
    # Setup body handling
    mock_req.body = AsyncMock(return_value=json.dumps({"input": "test data"}).encode())
    mock_req.json = AsyncMock(return_value={"input": "test data"})
    
    return mock_req


# We'll use the existing mock_request fixture


@pytest.fixture
def proxy_service():
    """Create a proxy service for testing."""
    mock_registry = MagicMock(spec=ModelRegistryService)
    mock_orchestrator = MagicMock(spec=Orchestrator)
    return ProxyService(mock_registry, mock_orchestrator)


@pytest.mark.asyncio
async def test_proxy_service_with_path_suffix(mock_request):
    """Test proxy_to_model with different path suffixes."""
    # Create a model config
    model_config = MagicMock(spec=ModelConfig)
    model_config.id = "test_model"
    
    # Create service with our own mocks for this test
    mock_registry = MagicMock(spec=ModelRegistryService)
    mock_orchestrator = MagicMock(spec=Orchestrator)
    service = ProxyService(mock_registry, mock_orchestrator)
    
    # Mock dependencies
    mock_registry.get_model_config = MagicMock(return_value=model_config)
    mock_orchestrator.proxy_request = AsyncMock(return_value=Response(
        content=json.dumps({"result": "success"}).encode(),
        status_code=200,
        media_type="application/json"
    ))
    
    # Test with empty path
    await service.proxy_to_model("test_model", mock_request, "")
    mock_orchestrator.proxy_request.assert_called_with(
        model_config=model_config,
        request=mock_request,
        path_suffix=""
    )
    
    # Reset mock
    mock_orchestrator.proxy_request.reset_mock()
    
    # Test with simple path
    await service.proxy_to_model("test_model", mock_request, "predict")
    mock_orchestrator.proxy_request.assert_called_with(
        model_config=model_config,
        request=mock_request,
        path_suffix="predict"
    )
    
    # Reset mock
    mock_orchestrator.proxy_request.reset_mock()
    
    # Test with complex path
    await service.proxy_to_model("test_model", mock_request, "v2/predict/image")
    mock_orchestrator.proxy_request.assert_called_with(
        model_config=model_config,
        request=mock_request,
        path_suffix="v2/predict/image"
    )


@pytest.mark.asyncio
async def test_proxy_service_model_config_not_found(mock_request):
    """Test proxy_to_model when model config isn't found and registry raises KeyError."""
    # Create service with our own mocks for this test
    mock_registry = MagicMock(spec=ModelRegistryService)
    mock_orchestrator = MagicMock(spec=Orchestrator)
    service = ProxyService(mock_registry, mock_orchestrator)
    
    # Mock model registry to raise KeyError (likely scenario)
    mock_registry.get_model_config = MagicMock(side_effect=KeyError("Model not found"))
    
    # Call and expect specific error
    with pytest.raises(ModelRequestError) as exc_info:
        await service.proxy_to_model("nonexistent_model", mock_request)
    
    # Verify error details
    # assert exc_info.value.status_code == 500  # Removed: ModelRequestError has no status_code
    assert "Model not found" in str(exc_info.value.message)
    assert exc_info.value.model_id == "nonexistent_model"


@pytest.mark.asyncio
async def test_proxy_service_with_logger(mock_request):
    """Test that the service properly logs its activities."""
    # Create test objects
    model_config = MagicMock(spec=ModelConfig)
    model_config.id = "test_model"
    
    # Create service with our own mocks for this test
    mock_registry = MagicMock(spec=ModelRegistryService)
    mock_orchestrator = MagicMock(spec=Orchestrator)
    
    # Setup logger mock
    with patch("app.services.proxy.logger") as mock_logger:
        service = ProxyService(mock_registry, mock_orchestrator)
        
        # Mock dependencies for successful response
        mock_registry.get_model_config = MagicMock(return_value=model_config)
        mock_orchestrator.proxy_request = AsyncMock(return_value=Response(
            content=json.dumps({"result": "success"}).encode(),
            status_code=200,
            media_type="application/json"
        ))
        
        # Call the service
        await service.proxy_to_model("test_model", mock_request)
        
        # Verify info log
        mock_logger.info.assert_called_once()
        assert "Proxying request to model: test_model" in mock_logger.info.call_args[0][0]
        
        # No errors should be logged
        mock_logger.error.assert_not_called()
        
        # Reset mocks
        mock_logger.reset_mock()
        mock_orchestrator.proxy_request = AsyncMock(side_effect=Exception("Test error"))
        
        # Call with error
        with pytest.raises(ModelRequestError):
            await service.proxy_to_model("test_model", mock_request)
        
        # Verify error log
        mock_logger.error.assert_called_once()
        assert "Error proxying request to model 'test_model'" in mock_logger.error.call_args[0][0]
        assert "Test error" in mock_logger.error.call_args[0][0]


@pytest.mark.asyncio
async def test_proxy_service_with_specific_exceptions(mock_request):
    """Test proxy service with different specific exception types."""
    # Create test objects
    model_config = MagicMock(spec=ModelConfig)
    model_config.id = "test_model"
    
    # Create service with our own mocks for this test
    mock_registry = MagicMock(spec=ModelRegistryService)
    mock_orchestrator = MagicMock(spec=Orchestrator)
    service = ProxyService(mock_registry, mock_orchestrator)
    
    # Setup
    mock_registry.get_model_config = MagicMock(return_value=model_config)
    
    # Test ValueError
    mock_orchestrator.proxy_request = AsyncMock(side_effect=ValueError("Invalid value"))
    with pytest.raises(ModelRequestError) as exc_info:
        await service.proxy_to_model("test_model", mock_request)
    assert "Invalid value" in str(exc_info.value.message)
    
    # Test TypeError
    mock_orchestrator.proxy_request = AsyncMock(side_effect=TypeError("Type error"))
    with pytest.raises(ModelRequestError) as exc_info:
        await service.proxy_to_model("test_model", mock_request)
    assert "Type error" in str(exc_info.value.message)
    
    # Test KeyError
    mock_orchestrator.proxy_request = AsyncMock(side_effect=KeyError("Missing key"))
    with pytest.raises(ModelRequestError) as exc_info:
        await service.proxy_to_model("test_model", mock_request)
    assert "Missing key" in str(exc_info.value.message)
    
    # Test for ModelRequestError passthrough
    model_error = ModelRequestError(message="Model error", model_id="test_model")
    mock_orchestrator.proxy_request = AsyncMock(side_effect=model_error)
    with pytest.raises(ModelRequestError) as exc_info:
        await service.proxy_to_model("test_model", mock_request)
    assert exc_info.value == model_error


@pytest.mark.asyncio
async def test_proxy_service_with_circuit_breaker_error(mock_request):
    """Test that CircuitBreakerError is correctly handled."""
    # Create service with our own mocks for this test
    mock_registry = MagicMock(spec=ModelRegistryService)
    mock_orchestrator = MagicMock(spec=Orchestrator)
    service = ProxyService(mock_registry, mock_orchestrator)
    
    # Circuit breaker error should be turned into a ModelRequestError
    circuit_error = CircuitBreakerError("circuit breaker open", model_id="test_model")
    
    # Have the orchestrator raise the error
    mock_registry.get_model_config = MagicMock(return_value=MagicMock())
    mock_orchestrator.proxy_request = AsyncMock(side_effect=circuit_error)
    
    # The circuit breaker should be converted to a ModelRequestError
    with pytest.raises(ModelRequestError) as exc_info:
        await service.proxy_to_model("test_model", mock_request)
    
    # Verify it contains the circuit breaker message
    assert "circuit breaker" in str(exc_info.value.message).lower()


@pytest.mark.asyncio
async def test_proxy_service_with_advanced_request(advanced_request):
    """Test the proxy service with a more advanced request."""
    # Create test objects
    model_config = MagicMock(spec=ModelConfig)
    model_config.id = "test-model"
    
    # Create service with our own mocks for this test
    mock_registry = MagicMock(spec=ModelRegistryService)
    mock_orchestrator = MagicMock(spec=Orchestrator)
    service = ProxyService(mock_registry, mock_orchestrator)
    
    # Setup mocks
    mock_registry.get_model_config = MagicMock(return_value=model_config)
    mock_orchestrator.proxy_request = AsyncMock(return_value=Response(
        content=json.dumps({"result": "success", "confidence": 0.95}).encode(),
        status_code=200,
        media_type="application/json"
    ))
    
    # Call with model ID and path suffix
    response = await service.proxy_to_model(
        "test-model", 
        advanced_request, 
        "classify"
    )
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["result"] == "success"
    assert data["confidence"] == 0.95
    
    # Verify the orchestrator was called with the right arguments
    mock_orchestrator.proxy_request.assert_called_once()
    call_args = mock_orchestrator.proxy_request.call_args[1]
    assert call_args["model_config"] == model_config
    assert call_args["request"] == advanced_request
    assert call_args["path_suffix"] == "classify"