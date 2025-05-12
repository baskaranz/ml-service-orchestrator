from typing import Any, Callable, Optional, TypeVar, Generic, Dict
import time
import logging
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from app.core.circuit_breaker import CircuitBreaker, CircuitState
from app.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

class LLMErrorType(Enum):
    """Types of LLM-specific errors."""
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    MODEL_OVERLOAD = "model_overload"
    UNKNOWN = "unknown"

@dataclass
class LLMCircuitBreakerConfig:
    """Configuration for the LLM circuit breaker."""
    failure_threshold: int = 5
    reset_timeout: int = 60
    half_open_timeout: int = 30
    max_retries: int = 2
    retry_delay: float = 0.5  # seconds
    error_thresholds: Dict[LLMErrorType, int] = field(default_factory=lambda: {
        LLMErrorType.RATE_LIMIT: 3,
        LLMErrorType.TIMEOUT: 2,
        LLMErrorType.INVALID_REQUEST: 1,
        LLMErrorType.MODEL_OVERLOAD: 2,
        LLMErrorType.UNKNOWN: 5
    })

class LLMCircuitBreaker(CircuitBreaker, Generic[T]):
    """
    Circuit breaker implementation specifically for LLM calls.
    
    This implementation adds:
    1. LLM-specific error handling
    2. Async support
    3. Detailed logging
    4. Error type-based thresholds
    """
    
    def __init__(self, llm: Any, config: LLMCircuitBreakerConfig):
        super().__init__(
            failure_threshold=config.failure_threshold,
            reset_timeout=config.reset_timeout,
            half_open_timeout=config.half_open_timeout
        )
        self.llm = llm
        self.config = config
        self._error_counts: Dict[LLMErrorType, int] = {
            error_type: 0 for error_type in LLMErrorType
        }

    def _classify_error(self, error: Exception) -> LLMErrorType:
        """Classify the error type based on the exception."""
        error_str = str(error).lower()
        
        if "rate limit" in error_str or "too many requests" in error_str:
            return LLMErrorType.RATE_LIMIT
        elif "timeout" in error_str or "timed out" in error_str:
            return LLMErrorType.TIMEOUT
        elif "invalid request" in error_str or "bad request" in error_str:
            return LLMErrorType.INVALID_REQUEST
        elif "overload" in error_str or "capacity" in error_str:
            return LLMErrorType.MODEL_OVERLOAD
        else:
            return LLMErrorType.UNKNOWN

    def _should_retry(self, error_type: LLMErrorType) -> bool:
        """Determine if we should retry based on error type and thresholds."""
        self._error_counts[error_type] += 1
        threshold = self.config.error_thresholds[error_type]
        return self._error_counts[error_type] <= threshold

    def execute(self, prompt: Any, *args: Any, **kwargs: Any) -> T:
        """
        Execute an LLM call with circuit breaker protection.
        
        Args:
            prompt: The input prompt for the LLM
            *args: Additional positional arguments for the LLM call
            **kwargs: Additional keyword arguments for the LLM call
            
        Returns:
            The LLM response
            
        Raises:
            Exception: If the circuit is open or all retries are exhausted
        """
        if not self._can_execute():
            logger.warning("Circuit breaker is open, request rejected")
            raise Exception("Circuit is open")

        last_error: Optional[Exception] = None
        retries = 0
        while retries <= self.config.max_retries:
            try:
                logger.debug(f"Attempting LLM call (attempt {retries + 1}/{self.config.max_retries + 1})")
                result: T = self.llm.generate(prompt, *args, **kwargs)
                self._record_success()
                logger.debug("LLM call successful")
                return result
            except Exception as e:
                error_type = self._classify_error(e)
                logger.warning(f"LLM call failed with error type {error_type}: {str(e)}")
                
                self._record_failure()
                last_error = e
                if retries < self.config.max_retries and self._should_retry(error_type):
                    logger.info(f"Retrying after {self.config.retry_delay} seconds...")
                    time.sleep(self.config.retry_delay)
                    retries += 1
                else:
                    logger.error(f"LLM call failed after {retries + 1} attempts")
                    raise last_error

    async def execute_async(self, prompt: Any, *args: Any, **kwargs: Any) -> T:
        """
        Execute an LLM call asynchronously with circuit breaker protection.
        
        Args:
            prompt: The input prompt for the LLM
            *args: Additional positional arguments for the LLM call
            **kwargs: Additional keyword arguments for the LLM call
            
        Returns:
            The LLM response
            
        Raises:
            Exception: If the circuit is open or all retries are exhausted
        """
        if not self._can_execute():
            logger.warning("Circuit breaker is open, request rejected")
            raise Exception("Circuit is open")

        last_error: Optional[Exception] = None
        retries = 0
        while retries <= self.config.max_retries:
            try:
                logger.debug(f"Attempting async LLM call (attempt {retries + 1}/{self.config.max_retries + 1})")
                result: T = await self.llm.generate_async(prompt, *args, **kwargs)
                self._record_success()
                logger.debug("Async LLM call successful")
                return result
            except Exception as e:
                error_type = self._classify_error(e)
                logger.warning(f"Async LLM call failed with error type {error_type}: {str(e)}")
                
                self._record_failure()
                last_error = e
                if retries < self.config.max_retries and self._should_retry(error_type):
                    logger.info(f"Retrying after {self.config.retry_delay} seconds...")
                    await asyncio.sleep(self.config.retry_delay)
                    retries += 1
                else:
                    logger.error(f"Async LLM call failed after {retries + 1} attempts")
                    raise last_error 