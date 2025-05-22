"""
Custom exceptions for the services module.
"""

from typing import Any, Dict, Optional

from fastapi import status


class ModelRequestError(Exception):
    """Exception raised for errors that occur during model requests.

    Attributes:
        message: Explanation of the error
        status_code: HTTP status code for the error response
        model_id: ID of the model that caused the error
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        model_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.model_id = model_id
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return (
            f"{self.message} (status_code={self.status_code}, "
            f"model_id={self.model_id}, details={self.details})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the exception to a dictionary for JSON responses."""
        return {
            "error": {
                "message": self.message,
                "status_code": self.status_code,
                "model_id": self.model_id,
                "details": self.details,
            }
        }


class ModelNotFoundError(ModelRequestError):
    """Exception raised when a requested model is not found."""

    def __init__(self, model_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Model '{model_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            model_id=model_id,
            details=details or {},
        )


class ModelNotReadyError(ModelRequestError):
    """Exception raised when a model is not ready to handle requests."""

    def __init__(self, model_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Model '{model_id}' is not ready to handle requests",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            model_id=model_id,
            details=details or {},
        )


class ModelRequestTimeoutError(ModelRequestError):
    """Exception raised when a model request times out."""

    def __init__(self, model_id: str, timeout: float, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Request to model '{model_id}' timed out after {timeout} seconds",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            model_id=model_id,
            details={"timeout": timeout, **(details or {})},
        )


class ModelRequestValidationError(ModelRequestError):
    """Exception raised for validation errors in model requests."""

    def __init__(
        self,
        model_id: str,
        validation_errors: Dict[str, Any],
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"Validation error for model '{model_id}'",
            status_code=status.HTTP_400_BAD_REQUEST,
            model_id=model_id,
            details={"validation_errors": validation_errors, **(details or {})},
        )


class CircuitBreakerError(ModelRequestError):
    """Exception raised when a circuit breaker is open for a model."""

    def __init__(self, model_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Circuit breaker is open for model '{model_id}'. Please try again later.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            model_id=model_id,
            details={"circuit_status": "open", **(details or {})},
        )
