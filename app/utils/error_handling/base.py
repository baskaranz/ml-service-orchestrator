"""
Base error handler with retry functionality.
"""

from typing import Any, Callable, Dict, Optional, Type, Union
import asyncio
import logging
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

class RetryConfig:
    """Configuration for retry behavior."""
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

class BaseErrorHandler:
    """Base class for error handling with retry functionality."""
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        excluded_exceptions: Optional[list[Type[Exception]]] = None
    ):
        self.retry_config = retry_config or RetryConfig()
        self.excluded_exceptions = excluded_exceptions or []
        self._error_counts: Dict[str, int] = {}
        self._last_error_times: Dict[str, datetime] = {}
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if the error should trigger a retry."""
        error_type = type(error).__name__
        
        # Don't retry excluded exceptions
        if any(isinstance(error, exc) for exc in self.excluded_exceptions):
            return False
        
        # Check error count
        if self._error_counts.get(error_type, 0) >= self.retry_config.max_retries:
            return False
        
        return True
    
    def _get_retry_delay(self, attempt: int) -> float:
        """Calculate the delay before the next retry attempt."""
        delay = min(
            self.retry_config.initial_delay * (self.retry_config.exponential_base ** attempt),
            self.retry_config.max_delay
        )
        
        if self.retry_config.jitter:
            import random
            delay *= random.uniform(0.5, 1.5)
        
        return delay
    
    def _update_error_stats(self, error: Exception):
        """Update error statistics."""
        error_type = type(error).__name__
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        self._last_error_times[error_type] = datetime.now()
    
    def _reset_error_stats(self, error_type: str):
        """Reset error statistics for a specific error type."""
        self._error_counts[error_type] = 0
        self._last_error_times.pop(error_type, None)
    
    async def with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function execution
            
        Raises:
            Exception: The last exception if all retries fail
        """
        last_error: Optional[Exception] = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Reset error stats on success
                if last_error:
                    self._reset_error_stats(type(last_error).__name__)
                
                return result
                
            except Exception as e:
                last_error = e
                
                if not self._should_retry(e):
                    logger.error(
                        f"Max retries exceeded for {func.__name__}. "
                        f"Last error: {str(e)}"
                    )
                    raise
                
                self._update_error_stats(e)
                delay = self._get_retry_delay(attempt)
                
                logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}. "
                    f"Retrying in {delay:.2f} seconds. Error: {str(e)}"
                )
                
                await asyncio.sleep(delay)
        
        if last_error is None:
            raise RuntimeError("Unexpected error: last_error is None after retry loop")
        raise last_error
    
    def retry_decorator(self):
        """Decorator for adding retry functionality to functions."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.with_retry(func, *args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.with_retry(func, *args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator 