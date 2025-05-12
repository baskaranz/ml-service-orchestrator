"""
Model-specific error handling with retry functionality.
"""

from typing import Any, Callable, Dict, Optional, Type
import httpx
from datetime import datetime

from app.core.exceptions import ModelRequestError, CircuitBreakerError
from app.utils.error_handling.base import BaseErrorHandler, RetryConfig

class ModelErrorHandler(BaseErrorHandler):
    """Error handler specifically for model requests."""
    
    def __init__(
        self,
        model_id: str,
        retry_config: Optional[RetryConfig] = None,
        excluded_exceptions: Optional[list[Type[Exception]]] = None
    ):
        # Default excluded exceptions for model requests
        default_excluded = [
            CircuitBreakerError,  # Don't retry if circuit breaker is open
            ValueError,  # Don't retry for invalid inputs
            TypeError,  # Don't retry for type errors
        ]
        
        # Merge with user-provided excluded exceptions
        if excluded_exceptions:
            default_excluded.extend(excluded_exceptions)
        
        super().__init__(retry_config, default_excluded)
        self.model_id = model_id
        self._request_stats: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_success": None,
            "last_failure": None,
        }
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if the error should trigger a retry for model requests."""
        # First check base retry conditions
        if not super()._should_retry(error):
            return False
        
        # Don't retry certain HTTP status codes
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            if status_code in [400, 401, 403, 404, 422]:
                return False
        
        return True
    
    def _update_request_stats(self, success: bool):
        """Update request statistics."""
        self._request_stats["total_requests"] += 1
        if success:
            self._request_stats["successful_requests"] += 1
            self._request_stats["last_success"] = datetime.now()
        else:
            self._request_stats["failed_requests"] += 1
            self._request_stats["last_failure"] = datetime.now()
    
    async def with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a model request with retry logic.
        
        Args:
            func: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function execution
            
        Raises:
            ModelRequestError: If all retries fail
        """
        try:
            result = await super().with_retry(func, *args, **kwargs)
            self._update_request_stats(True)
            return result
        except Exception as e:
            self._update_request_stats(False)
            # Convert to ModelRequestError if it's not already
            if not isinstance(e, ModelRequestError):
                raise ModelRequestError(
                    message=f"Model request failed after {self.retry_config.max_retries} retries: {str(e)}",
                    model_id=self.model_id
                ) from e
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current request statistics."""
        return {
            "model_id": self.model_id,
            "request_stats": self._request_stats,
            "error_stats": {
                "counts": self._error_counts,
                "last_errors": {
                    k: v.isoformat() for k, v in self._last_error_times.items()
                }
            }
        } 