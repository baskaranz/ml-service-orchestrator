"""Test exception handlers setup."""

from unittest.mock import MagicMock

import pytest
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    CircuitBreakerError,
    ConfigurationError,
    ModelRequestError,
    circuit_breaker_error_handler,
    configuration_error_handler,
    http_error_handler,
    model_request_error_handler,
    setup_exception_handlers,
)


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app."""
    return MagicMock()


def test_setup_exception_handlers(mock_app):
    """Test exception handlers are registered correctly."""
    setup_exception_handlers(mock_app)

    # Verify that add_exception_handler was called for each exception type
    assert mock_app.add_exception_handler.call_count == 6

    # Verify ModelRequestError handler was registered
    mock_app.add_exception_handler.assert_any_call(ModelRequestError, model_request_error_handler)

    # Verify CircuitBreakerError handler was registered
    mock_app.add_exception_handler.assert_any_call(
        CircuitBreakerError, circuit_breaker_error_handler
    )

    # Verify ConfigurationError handler was registered
    mock_app.add_exception_handler.assert_any_call(ConfigurationError, configuration_error_handler)

    # Verify HTTPException handler was registered
    mock_app.add_exception_handler.assert_any_call(StarletteHTTPException, http_error_handler)
