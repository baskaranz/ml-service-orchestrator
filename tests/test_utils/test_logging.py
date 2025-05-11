import logging
import os
from unittest.mock import patch, MagicMock

import pytest

from app.utils.logging import (
    get_logger,
    setup_logging,
    RequestLogContext,
    LoggingMiddleware
)


def test_setup_logging():
    """Test setting up the logging configuration."""
    # Call setup_logging with test settings
    setup_logging(log_level="DEBUG")
    
    # Get the root logger and check its level
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    
    # Check that handlers were added
    assert len(root_logger.handlers) > 0
    
    # Test with different log level
    setup_logging(log_level="ERROR")
    assert root_logger.level == logging.ERROR


def test_get_logger():
    """Test getting a logger for a specific module."""
    # Get logger for a test module
    logger = get_logger("test_module")
    
    # Check logger name
    assert logger.name == "test_module"
    
    # Check that it's the same instance when called again
    assert get_logger("test_module") is logger


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app for middleware testing."""
    app = MagicMock()
    return app


@pytest.fixture
def mock_request():
    """Create a mock request for middleware testing."""
    request = MagicMock()
    request.method = "GET"
    request.url.path = "/test/path"
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def logging_middleware(mock_app):
    """Create a LoggingMiddleware instance."""
    return LoggingMiddleware(mock_app)


@pytest.mark.asyncio
async def test_logging_middleware(logging_middleware, mock_request, mock_app):
    """Test the logging middleware."""
    # Setup mock call_next function
    async def mock_call_next(request):
        # Simulate some processing time
        response = MagicMock()
        response.status_code = 200
        return response
    
    # Setup log capture
    with patch.object(logging_middleware, "logger") as mock_logger:
        # Call middleware
        response = await logging_middleware.dispatch(mock_request, mock_call_next)
        
        # Verify response was returned
        assert response.status_code == 200
        
        # Verify logging occurred
        assert mock_logger.info.call_count >= 2  # Should log at start and end
        
        # Verify some of the log messages
        log_calls = [call_args[0][0] for call_args in mock_logger.info.call_args_list]
        # Check that the log messages contain the request method and path
        assert any("Request started" in log_call for log_call in log_calls)
        assert any("Request completed" in log_call for log_call in log_calls)
        assert any("GET" in log_call for log_call in log_calls)
        assert any("/test/path" in log_call for log_call in log_calls)


def test_request_log_context():
    """Test the RequestLogContext class."""
    # Create a context with request info
    context = RequestLogContext(
        request_id="test-123",
        method="POST",
        path="/api/test",
        client_ip="192.168.1.1"
    )
    
    # Check properties
    assert context.request_id == "test-123"
    assert context.method == "POST"
    assert context.path == "/api/test"
    assert context.client_ip == "192.168.1.1"
    
    # Test string representation
    context_str = str(context)
    assert "test-123" in context_str
    assert "POST" in context_str
    assert "/api/test" in context_str


def test_request_log_context_with_model():
    """Test RequestLogContext with model information."""
    # Create a context with model info
    context = RequestLogContext(
        request_id="model-req-123",
        method="POST",
        path="/orchestrator/test-model/predict",
        client_ip="192.168.1.1",
        model_id="test-model"
    )
    
    # Check model is included
    assert context.model_id == "test-model"
    
    # Test string representation includes model
    context_str = str(context)
    assert "test-model" in context_str
