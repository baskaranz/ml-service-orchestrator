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
    """Exception raised when a model request fails."""
    
    def __init__(self, message: str, status_code: int = 503, model_id: Optional[str] = None, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.model_id = model_id
        self.details = details
        super().__init__(message)


class CircuitBreakerError(Exception):
    """Exception raised when a circuit breaker is open."""
    
    def __init__(self, *args, **kwargs):
        # Accept both (message, model_id) and (model_id, message) signatures
        if len(args) == 2:
            # Called as (message, model_id)
            message, model_id = args
        elif len(args) == 1:
            # Called as (model_id,) or (message,)
            if 'model_id' in kwargs:
                model_id = kwargs['model_id']
                message = args[0]
            else:
                model_id = args[0]
                message = kwargs.get('message', None)
        else:
            model_id = kwargs.get('model_id', None)
            message = kwargs.get('message', None)
        if model_id is None:
            raise ValueError("model_id is required for CircuitBreakerError")
        self.model_id = model_id
        self.message = message or f"Circuit breaker is open for model {model_id}"
        super().__init__(self.message)


class ConfigurationError(Exception):
    """Exception raised when there is a configuration error."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class ModelNotFoundError(Exception):
    """Exception raised when a model is not found."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def model_request_error_handler(request: Request, exc: ModelRequestError) -> JSONResponse:
    """Handle ModelRequestError exceptions."""
    logger.error(
        f"Model request error: {exc.message}",
        extra={"model_id": exc.model_id}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": "MODEL_REQUEST_ERROR",
            "details": exc.details,
        },
    )


async def circuit_breaker_error_handler(request: Request, exc: CircuitBreakerError) -> JSONResponse:
    """Handle CircuitBreakerError exceptions."""
    logger.warning(
        f"Circuit breaker error: {exc.message}",
        extra={"model_id": exc.model_id}
    )
    
    return JSONResponse(
        status_code=503,
        content={
            "error": exc.message,
            "code": "CIRCUIT_BREAKER_OPEN",
            "details": {"model_id": exc.model_id},
        },
    )


async def configuration_error_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    """Handle ConfigurationError exceptions."""
    logger.error(
        f"Configuration error: {exc.message}",
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": exc.message,
            "code": "CONFIGURATION_ERROR",
            "details": exc.details,
        },
    )


async def model_not_found_error_handler(request: Request, exc: ModelNotFoundError) -> JSONResponse:
    """Handle ModelNotFoundError exceptions."""
    logger.error(
        f"Model not found: {exc.message}",
    )
    
    return JSONResponse(
        status_code=404,
        content={
            "error": exc.message,
            "code": "MODEL_NOT_FOUND",
        },
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
    """Set up exception handlers for the application."""
    app.add_exception_handler(ModelRequestError, model_request_error_handler)
    app.add_exception_handler(CircuitBreakerError, circuit_breaker_error_handler)
    app.add_exception_handler(ConfigurationError, configuration_error_handler)
    app.add_exception_handler(ModelNotFoundError, model_not_found_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)