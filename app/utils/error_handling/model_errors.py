"""
Model-specific error handling functionality.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional, Type

import httpx

from app.core.exceptions import ModelRequestError
from app.models.config_models import ModelConfig
from app.utils.error_handling.base import BaseErrorHandler, RetryConfig
from app.utils.error_handling.llm_errors import LLMErrorClassifier
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ModelErrorHandler(BaseErrorHandler):
    """Error handler specifically for model requests."""

    def __init__(
        self,
        model_config: ModelConfig,
        retry_config: Optional[RetryConfig] = None,
        excluded_exceptions: Optional[list[Type[Exception]]] = None,
    ):
        """Initialize the model error handler."""
        # Use error handling configuration from model config if available
        eh = getattr(model_config, "error_handling", None)
        basic = getattr(eh, "basic", None) if eh is not None else None
        if retry_config is None and basic is not None:
            retry_config = RetryConfig(
                max_retries=basic.max_retries,
                initial_delay=basic.retry_delay,
                max_delay=basic.max_retry_delay,
            )
        super().__init__(retry_config, excluded_exceptions)
        self.model_config = model_config
        self.error_classifier = None

        # Initialize LLM error classifier if enabled and configured
        if (
            hasattr(model_config, "error_handling")
            and model_config.error_handling is not None
            and hasattr(model_config.error_handling, "llm")
            and model_config.error_handling.llm is not None
            and model_config.error_handling.llm.enabled
        ):
            self.error_classifier = LLMErrorClassifier()

    async def _should_retry(self, error: Exception) -> bool:
        """Determine if an error should trigger a retry."""
        logger.debug(f"_should_retry called for error: {type(error).__name__}: {error}")
        # First check base retry conditions
        if not await super()._should_retry(error):
            logger.debug("BaseErrorHandler._should_retry returned False")
            return False

        # If LLM classification is enabled, use it
        if self.error_classifier:
            try:
                logger.debug("Calling LLMErrorClassifier.classify_error...")
                # Build error context
                error_context = {
                    "model_id": self.model_config.id,
                    "model_name": self.model_config.name,
                    "retry_count": self.retry_count,
                    "max_retries": self.retry_config.max_retries,
                    "status_code": getattr(error, "status_code", None),
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
                if isinstance(error, httpx.HTTPStatusError):
                    error_context["response"] = {
                        "status_code": error.response.status_code,
                        "headers": dict(error.response.headers),
                        "body": error.response.text,
                    }
                classification = await self.error_classifier.classify_error(error, error_context)
                logger.info(f"LLM classification result: {classification}")
                # Don't retry permanent errors
                if classification["classification"] == "permanent":
                    logger.info("Not retrying permanent error")
                    return False
                if classification["classification"] == "transient":
                    logger.info("Retrying transient error")
                    return True
                if classification["classification"] == "rate_limit":
                    max_retries = (
                        self.model_config.error_handling.basic.max_retries
                        if hasattr(self.model_config, "error_handling")
                        else 3
                    )
                    if self.retry_count < max_retries:
                        logger.info("Retrying rate limit error")
                        return True
                    logger.info("Max retries reached for rate limit error")
                    return False
                if classification["classification"] == "input_validation":
                    logger.info("Not retrying input validation error")
                    return False
                if classification["classification"] == "authentication":
                    logger.info("Not retrying authentication error")
                    return False
            except Exception as e:
                logger.error(f"Error during LLM classification: {str(e)}")
                # Fall back to default behavior if classification fails

        # Default behavior based on error type
        if isinstance(error, ModelRequestError):
            logger.debug("Default ModelRequestError branch taken")
            # Check if the error message contains a 503 status code
            if "503" in str(error):
                logger.info("Retrying 503 Service Unavailable error")
                return True
            # Don't retry client errors (4xx)
            if hasattr(error, "status_code") and 400 <= error.status_code < 500:
                return False
            # Retry server errors (5xx)
            if hasattr(error, "status_code") and 500 <= error.status_code < 600:
                return True
            return True
        logger.debug("Default fallback branch taken")
        return False

    def _update_request_stats(self, success: bool, error: Optional[Exception] = None):
        """Update request statistics."""
        if success:
            self.retry_count = 0
        elif error:
            error_type = type(error).__name__
            self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
            self._last_error_times[error_type] = datetime.now()

    async def with_retry(self, func: Any, *args, **kwargs) -> Any:
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
        logger.debug(
            f"with_retry called with func={getattr(func, '__name__', str(func))}, args={args}, kwargs={kwargs}"
        )
        last_error = None

        while True:
            try:
                result = await func(*args, **kwargs)
                self._update_request_stats(True)
                return result
            except Exception as e:
                last_error = e
                self._update_request_stats(False, e)

                if not await self._should_retry(e):
                    break

                delay = self._get_retry_delay()
                logger.info(
                    f"Retrying after {delay:.2f}s (attempt {self.retry_count + 1}/{self.retry_config.max_retries})"
                )
                await asyncio.sleep(delay)
                self.increment_retry_count()

        raise last_error
