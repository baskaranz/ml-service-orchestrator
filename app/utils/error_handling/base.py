"""
Base error handling functionality.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type

from app.utils.logging import get_logger

logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0, max_delay: float = 10.0):
        """Initialize retry configuration."""
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay


class BaseErrorHandler:
    """Base class for error handling with retry functionality."""

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        excluded_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        """Initialize the error handler."""
        self.retry_config = retry_config or RetryConfig()
        self.excluded_exceptions = excluded_exceptions or []
        self.retry_count = 0
        self._error_counts: Dict[str, int] = {}
        self._last_error_times: Dict[str, datetime] = {}

    async def _should_retry(self, error: Exception) -> bool:
        """Determine if an error should trigger a retry."""
        # Don't retry if max retries reached
        if self.retry_count >= self.retry_config.max_retries:
            logger.info(f"Max retries ({self.retry_config.max_retries}) reached, not retrying")
            return False

        # Don't retry excluded exceptions
        for exc_type in self.excluded_exceptions:
            if isinstance(error, exc_type):
                logger.info(f"Error type {type(error).__name__} is excluded from retries")
                return False

        return True

    def _get_retry_delay(self) -> float:
        """Calculate the delay before the next retry."""
        # Exponential backoff with jitter
        delay = min(
            self.retry_config.initial_delay * (2**self.retry_count), self.retry_config.max_delay
        )
        # Add some jitter (±20%)
        jitter = delay * 0.2
        return delay + (asyncio.get_event_loop().time() % jitter)

    def increment_retry_count(self):
        """Increment the retry counter."""
        self.retry_count += 1

    async def with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function execution

        Raises:
            Exception: If all retries fail
        """
        last_error = None

        while True:
            try:
                result = await func(*args, **kwargs)
                # Reset retry count on success
                self.retry_count = 0
                return result
            except Exception as e:
                last_error = e

                # Update error statistics
                error_type = type(e).__name__
                self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
                self._last_error_times[error_type] = datetime.now()

                # Check if we should retry
                if not await self._should_retry(e):
                    break

                # Calculate delay and wait
                delay = self._get_retry_delay()
                logger.info(
                    f"Retrying after {delay:.2f}s (attempt {self.retry_count + 1}/{self.retry_config.max_retries})"
                )
                await asyncio.sleep(delay)

                # Increment retry counter
                self.increment_retry_count()

        # If we get here, all retries failed
        raise last_error
