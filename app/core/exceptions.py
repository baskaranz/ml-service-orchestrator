"""
Custom exception handlers for the application.
"""

from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.logging import get_logger

logger = get_logger(__name__)


class ModelRequestError(Exception):
    """Error encountered when making a request to a model endpoint."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        model_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.model_id = model_id
        self.details = details or {}
        super().__init__(self.message)


class CircuitBreakerError(Exception):
    """Error raised when the circuit breaker is open."""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable due to circuit breaker",
        model_id: Optional[str] = None
    ):
        self.message = message
        self.model_id = model_id
        super().__init__(self.message)


class ConfigurationError(Exception):
    """Error in service configuration."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


async def model_request_error_handler(request: Request, exc: ModelRequestError) -> JSONResponse:
    """
    Handle ModelRequestError exceptions.
    
    Args:
        request: FastAPI request object
        exc: The ModelRequestError exception
        
    Returns:
        JSON response with error details
    """
    logger.error(
        f"Model request error: {exc.message}",
        extra={"model_id": exc.model_id, "status_code": exc.status_code, "details": exc.details}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": "MODEL_REQUEST_ERROR",
            "details": exc.details
        }
    )


async def circuit_breaker_error_handler(request: Request, exc: CircuitBreakerError) -> JSONResponse:
    """
    Handle CircuitBreakerError exceptions.
    
    Args:
        request: FastAPI request object
        exc: The CircuitBreakerError exception
        
    Returns:
        JSON response with error details
    """
    logger.warning(
        f"Circuit breaker error: {exc.message}",
        extra={"model_id": exc.model_id}
    )
    
    return JSONResponse(
        status_code=503,  # Service Unavailable
        content={
            "error": exc.message,
            "code": "CIRCUIT_BREAKER_OPEN",
            "details": {"model_id": exc.model_id}
        }
    )


async def configuration_error_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    """
    Handle ConfigurationError exceptions.
    
    Args:
        request: FastAPI request object
        exc: The ConfigurationError exception
        
    Returns:
        JSON response with error details
    """
    logger.error(
        f"Configuration error: {exc.message}",
        extra={"details": exc.details}
    )
    
    return JSONResponse(
        status_code=500,  # Internal Server Error
        content={
            "error": exc.message,
            "code": "CONFIGURATION_ERROR",
            "details": exc.details
        }
    )


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTPException with custom format.
    
    Args:
        request: FastAPI request object
        exc: The HTTPException
        
    Returns:
        JSON response with error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": str(exc.detail),
            "code": f"HTTP_{exc.status_code}",
            "details": getattr(exc, "details", None)
        }
    )


def setup_exception_handlers(app: Any) -> None:
    """
    Register exception handlers with the FastAPI app.
    
    Args:
        app: FastAPI application
    """
    app.add_exception_handler(ModelRequestError, model_request_error_handler)
    app.add_exception_handler(CircuitBreakerError, circuit_breaker_error_handler)
    app.add_exception_handler(ConfigurationError, configuration_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)