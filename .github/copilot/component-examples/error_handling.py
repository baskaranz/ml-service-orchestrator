"""
ML Orchestrator Error Handling Pattern

This example demonstrates the error handling patterns used in the ML Orchestrator
for consistent API responses, logging, and telemetry.
"""
import functools
import logging
import traceback
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Error codes enum
class ErrorCode(str, Enum):
    """Error codes used for categorizing errors in the ML Orchestrator."""
    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    
    # Domain-specific errors
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_LOADING_ERROR = "MODEL_LOADING_ERROR"
    INFERENCE_ERROR = "INFERENCE_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # External service errors
    REGISTRY_ERROR = "REGISTRY_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    PROXY_ERROR = "PROXY_ERROR"
    
    # Metadata
    @classmethod
    def get_http_status(cls, code: "ErrorCode") -> int:
        """Map error codes to HTTP status codes."""
        status_map = {
            cls.UNKNOWN_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            cls.VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
            cls.AUTHENTICATION_ERROR: status.HTTP_401_UNAUTHORIZED,
            cls.AUTHORIZATION_ERROR: status.HTTP_403_FORBIDDEN,
            cls.NOT_FOUND_ERROR: status.HTTP_404_NOT_FOUND,
            
            cls.MODEL_NOT_FOUND: status.HTTP_404_NOT_FOUND,
            cls.MODEL_LOADING_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            cls.INFERENCE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            cls.CONFIG_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            cls.DEPENDENCY_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            cls.CIRCUIT_BREAKER_OPEN: status.HTTP_503_SERVICE_UNAVAILABLE,
            cls.RATE_LIMIT_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
            
            cls.REGISTRY_ERROR: status.HTTP_502_BAD_GATEWAY,
            cls.STORAGE_ERROR: status.HTTP_502_BAD_GATEWAY,
            cls.PROXY_ERROR: status.HTTP_502_BAD_GATEWAY,
        }
        return status_map.get(code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# Base error response model
class ErrorDetail(BaseModel):
    """Detailed error information."""
    loc: Optional[List[str]] = Field(None, description="Error location (e.g. field path)")
    msg: str = Field(..., description="Error message")
    type: Optional[str] = Field(None, description="Error type")


class ErrorResponse(BaseModel):
    """Standard error response format for ML Orchestrator API."""
    code: ErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    trace_id: Optional[str] = Field(None, description="Trace ID for debugging")
    request_id: Optional[str] = Field(None, description="Request ID")


# Base exception class
class OrchestratorError(Exception):
    """
    Base exception class for ML Orchestrator errors.
    
    All domain-specific exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[List[ErrorDetail]] = None,
        status_code: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            code: Error code from ErrorCode enum
            details: Optional list of detailed error information
            status_code: HTTP status code (overrides the default for the error code)
            original_error: Original exception that caused this error
        """
        self.message = message
        self.code = code
        self.details = details or []
        self._status_code = status_code
        self.original_error = original_error
        super().__init__(message)
    
    @property
    def status_code(self) -> int:
        """Get the HTTP status code for this error."""
        if self._status_code is not None:
            return self._status_code
        return ErrorCode.get_http_status(self.code)
    
    def to_response(self, trace_id: Optional[str] = None, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert exception to ErrorResponse model."""
        return ErrorResponse(
            code=self.code,
            message=self.message,
            details=self.details,
            trace_id=trace_id,
            request_id=request_id
        )


# Domain-specific exceptions
class ModelNotFoundError(OrchestratorError):
    """Raised when a requested model is not found."""
    
    def __init__(
        self,
        model_id: str,
        message: Optional[str] = None,
        details: Optional[List[ErrorDetail]] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize the exception.
        
        Args:
            model_id: ID of the model that was not found
            message: Custom error message (defaults to a standard message)
            details: Optional list of detailed error information
            original_error: Original exception that caused this error
        """
        if message is None:
            message = f"Model not found: {model_id}"
            
        super().__init__(
            message=message,
            code=ErrorCode.MODEL_NOT_FOUND,
            details=details,
            original_error=original_error
        )
        self.model_id = model_id


class InferenceError(OrchestratorError):
    """Raised when an error occurs during model inference."""
    
    def __init__(
        self,
        model_id: str,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize the exception.
        
        Args:
            model_id: ID of the model that encountered an error
            message: Error message
            details: Optional list of detailed error information
            original_error: Original exception that caused this error
        """
        super().__init__(
            message=message,
            code=ErrorCode.INFERENCE_ERROR,
            details=details,
            original_error=original_error
        )
        self.model_id = model_id


class CircuitBreakerOpenError(OrchestratorError):
    """Raised when a request is rejected due to an open circuit breaker."""
    
    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[List[ErrorDetail]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            service_name: Name of the service with an open circuit breaker
            message: Custom error message (defaults to a standard message)
            details: Optional list of detailed error information
        """
        if message is None:
            message = f"Service temporarily unavailable: {service_name} (circuit breaker open)"
            
        super().__init__(
            message=message,
            code=ErrorCode.CIRCUIT_BREAKER_OPEN,
            details=details
        )
        self.service_name = service_name


# Exception handlers for FastAPI

def extract_request_id(request: Request) -> Optional[str]:
    """Extract request ID from headers or generate a new one."""
    # In a real implementation, this would extract from X-Request-ID header
    # or generate a new UUID if not present
    return getattr(request.state, "request_id", None)


def extract_trace_id(request: Request) -> Optional[str]:
    """Extract trace ID for distributed tracing."""
    # In a real implementation, this would extract from tracing headers
    return getattr(request.state, "trace_id", None)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Set up exception handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(OrchestratorError)
    async def orchestrator_exception_handler(request: Request, exc: OrchestratorError) -> JSONResponse:
        """Handle OrchestratorError exceptions."""
        trace_id = extract_trace_id(request)
        request_id = extract_request_id(request)
        
        # Log the error with trace context
        log_context = {
            "trace_id": trace_id,
            "request_id": request_id,
            "error_code": exc.code,
            "status_code": exc.status_code,
            "path": request.url.path
        }
        
        if exc.original_error:
            logger.error(
                f"Orchestrator error: {exc.message}",
                exc_info=exc.original_error,
                extra=log_context
            )
        else:
            logger.error(f"Orchestrator error: {exc.message}", extra=log_context)
        
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_response(trace_id, request_id).dict(exclude_none=True)
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle Pydantic validation errors."""
        trace_id = extract_trace_id(request)
        request_id = extract_request_id(request)
        
        # Convert Pydantic error details to our format
        details = []
        for error in exc.errors():
            details.append(ErrorDetail(
                loc=error["loc"],
                msg=error["msg"],
                type=error["type"]
            ))
        
        # Create a custom error response
        error_response = ErrorResponse(
            code=ErrorCode.VALIDATION_ERROR,
            message="Validation error",
            details=details,
            trace_id=trace_id,
            request_id=request_id
        )
        
        # Log the validation error
        logger.warning(
            f"Validation error: {request.url.path}",
            extra={
                "trace_id": trace_id,
                "request_id": request_id,
                "path": request.url.path,
                "validation_errors": [error.dict() for error in details]
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.dict(exclude_none=True)
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle FastAPI HTTPException."""
        trace_id = extract_trace_id(request)
        request_id = extract_request_id(request)
        
        # Map status code to error code
        error_code = ErrorCode.UNKNOWN_ERROR
        if exc.status_code == 404:
            error_code = ErrorCode.NOT_FOUND_ERROR
        elif exc.status_code == 401:
            error_code = ErrorCode.AUTHENTICATION_ERROR
        elif exc.status_code == 403:
            error_code = ErrorCode.AUTHORIZATION_ERROR
        elif exc.status_code == 400:
            error_code = ErrorCode.VALIDATION_ERROR
        
        # Create a custom error response
        error_response = ErrorResponse(
            code=error_code,
            message=exc.detail,
            trace_id=trace_id,
            request_id=request_id
        )
        
        # Log the HTTP error
        logger.warning(
            f"HTTP error {exc.status_code}: {exc.detail}",
            extra={
                "trace_id": trace_id,
                "request_id": request_id,
                "path": request.url.path,
                "status_code": exc.status_code
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.dict(exclude_none=True),
            headers=exc.headers or {}
        )
    
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions."""
        trace_id = extract_trace_id(request)
        request_id = extract_request_id(request)
        
        # Log the unhandled exception with traceback
        logger.error(
            f"Unhandled exception: {str(exc)}",
            exc_info=exc,
            extra={
                "trace_id": trace_id,
                "request_id": request_id,
                "path": request.url.path
            }
        )
        
        # In production, we don't want to expose internal error details
        error_message = "An unexpected error occurred"
        
        error_response = ErrorResponse(
            code=ErrorCode.UNKNOWN_ERROR,
            message=error_message,
            trace_id=trace_id,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.dict(exclude_none=True)
        )


# Exception handling decorators

F = TypeVar("F", bound=Callable[..., Any])

def handle_exceptions(
    default_error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
    error_map: Optional[Dict[Type[Exception], ErrorCode]] = None
) -> Callable[[F], F]:
    """
    Decorator for handling exceptions in service functions.
    
    Args:
        default_error_code: Default error code for unhandled exceptions
        error_map: Mapping of exception types to error codes
        
    Returns:
        Decorated function that handles exceptions
    """
    error_map = error_map or {}
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except OrchestratorError:
                # Already handled by our exception system
                raise
            except Exception as e:
                # Map the exception to an error code
                for exc_type, code in error_map.items():
                    if isinstance(e, exc_type):
                        error_code = code
                        break
                else:
                    error_code = default_error_code
                
                # Create a new OrchestratorError
                raise OrchestratorError(
                    message=str(e),
                    code=error_code,
                    original_error=e
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except OrchestratorError:
                # Already handled by our exception system
                raise
            except Exception as e:
                # Map the exception to an error code
                for exc_type, code in error_map.items():
                    if isinstance(e, exc_type):
                        error_code = code
                        break
                else:
                    error_code = default_error_code
                
                # Create a new OrchestratorError
                raise OrchestratorError(
                    message=str(e),
                    code=error_code,
                    original_error=e
                )
        
        # Choose the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)
    
    return decorator


# Example usage

"""
from fastapi import FastAPI, Depends

app = FastAPI()
setup_exception_handlers(app)

# Example service function with exception handling
@handle_exceptions(
    default_error_code=ErrorCode.INFERENCE_ERROR,
    error_map={
        KeyError: ErrorCode.MODEL_NOT_FOUND,
        ValueError: ErrorCode.VALIDATION_ERROR,
        ConnectionError: ErrorCode.DEPENDENCY_ERROR
    }
)
async def run_model_inference(model_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    # This might raise various exceptions
    if model_id not in available_models:
        raise KeyError(f"Model not found: {model_id}")
        
    if not validate_input(input_data):
        raise ValueError("Invalid input data")
        
    try:
        return await call_inference_service(model_id, input_data)
    except ConnectionError:
        raise  # This will be caught by the decorator
        
# API endpoint using the service function
@app.post("/api/models/{model_id}/predict")
async def predict(
    model_id: str,
    request_data: Dict[str, Any]
) -> Dict[str, Any]:
    # The exception handling decorator will convert exceptions
    # to OrchestratorError, which will be handled by the exception handler
    return await run_model_inference(model_id, request_data)
"""