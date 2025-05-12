"""Test exception handling."""
import pytest
import json
from unittest.mock import MagicMock

from fastapi import Request
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    http_error_handler,
    model_request_error_handler,
    circuit_breaker_error_handler,
    configuration_error_handler,
    ModelRequestError,
    CircuitBreakerError,
    ConfigurationError,
    setup_exception_handlers
)


@pytest.fixture
def mock_request():
    """Create a mock request for testing."""
    return Request(scope={"type": "http", "path": "/test"})


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app."""
    return MagicMock()


@pytest.mark.asyncio
async def test_http_error_handler(mock_request):
    """Test handling of HTTPException."""
    # Create a test exception
    exc = StarletteHTTPException(status_code=400, detail="Test error")
    
    # Handle the exception
    response = await http_error_handler(mock_request, exc)
    
    # Verify response
    assert response.status_code == 400
    data = json.loads(bytes(response.body).decode('utf-8'))
    assert data["error"] == "Test error"
    assert data["code"] == "HTTP_400"
    assert data["details"] is None


@pytest.mark.asyncio
async def test_http_error_handler_with_details(mock_request):
    """Test handling of HTTPException with details."""
    # Create a test exception with details
    exc = StarletteHTTPException(status_code=400, detail="Test error")
    setattr(exc, "details", {"field": "test_field", "issue": "invalid format"})
    
    # Handle the exception
    response = await http_error_handler(mock_request, exc)
    
    # Verify response
    assert response.status_code == 400
    data = json.loads(bytes(response.body).decode('utf-8'))
    assert data["error"] == "Test error"
    assert data["code"] == "HTTP_400"
    assert data["details"] == {"field": "test_field", "issue": "invalid format"}


@pytest.mark.asyncio
async def test_model_request_error_handler(mock_request):
    """Test handling of ModelRequestError."""
    # Create a test exception
    exc = ModelRequestError(
        message="Model request failed", 
        status_code=502, 
        model_id="test_model",
        details={"reason": "Connection error"}
    )
    
    # Handle the exception
    response = await model_request_error_handler(mock_request, exc)
    
    # Verify response
    assert response.status_code == 502
    data = json.loads(bytes(response.body).decode('utf-8'))
    assert data["error"] == "Model request failed"
    assert data["code"] == "MODEL_REQUEST_ERROR"
    assert data["details"] == {"reason": "Connection error"}


@pytest.mark.asyncio
async def test_circuit_breaker_error_handler(mock_request):
    """Test handling of CircuitBreakerError."""
    # Create a test exception
    exc = CircuitBreakerError(
        message="Service temporarily unavailable", 
        model_id="test_model"
    )
    
    # Handle the exception
    response = await circuit_breaker_error_handler(mock_request, exc)
    
    # Verify response
    assert response.status_code == 503  # Service Unavailable
    data = json.loads(bytes(response.body).decode('utf-8'))
    assert data["error"] == "Service temporarily unavailable"
    assert data["code"] == "CIRCUIT_BREAKER_OPEN"
    assert data["details"] == {"model_id": "test_model"}


@pytest.mark.asyncio
async def test_configuration_error_handler(mock_request):
    """Test handling of ConfigurationError."""
    # Create a test exception
    exc = ConfigurationError(
        message="Invalid configuration", 
        details={"config_file": "models.yaml", "issue": "missing required field"}
    )
    
    # Handle the exception
    response = await configuration_error_handler(mock_request, exc)
    
    # Verify response
    assert response.status_code == 500  # Internal Server Error
    data = json.loads(bytes(response.body).decode('utf-8'))
    assert data["error"] == "Invalid configuration"
    assert data["code"] == "CONFIGURATION_ERROR"
    assert data["details"] == {"config_file": "models.yaml", "issue": "missing required field"}


def test_setup_exception_handlers(mock_app):
    """Test exception handlers are registered correctly."""
    setup_exception_handlers(mock_app)
    
    # Verify that add_exception_handler was called for each exception type
    assert mock_app.add_exception_handler.call_count == 6
    
    # Verify ModelRequestError handler was registered
    mock_app.add_exception_handler.assert_any_call(ModelRequestError, model_request_error_handler)
    
    # Verify CircuitBreakerError handler was registered
    mock_app.add_exception_handler.assert_any_call(CircuitBreakerError, circuit_breaker_error_handler)
    
    # Verify ConfigurationError handler was registered
    mock_app.add_exception_handler.assert_any_call(ConfigurationError, configuration_error_handler)
    
    # Verify HTTPException handler was registered
    mock_app.add_exception_handler.assert_any_call(StarletteHTTPException, http_error_handler)
