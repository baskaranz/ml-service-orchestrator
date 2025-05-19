"""
Base circuit breaker implementation.
"""

from abc import ABC, abstractmethod
import time
from typing import Any, Callable, Dict, Optional
from enum import Enum
from app.utils.logging import get_logger

logger = get_logger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker(ABC):
    """Base class for circuit breaker implementations."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_timeout: float = 30.0,
        success_threshold: int = 2,
        model_id: Optional[str] = None
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        self.success_threshold = success_threshold
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
        self._last_state_change = time.time()
        self.model_id = model_id

    def _can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        current_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True
            
        if self.state == CircuitState.OPEN:
            if current_time - self._last_state_change >= self.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                self._last_state_change = current_time
                self.success_count = 0
                return True
            return False
            
        if self.state == CircuitState.HALF_OPEN:
            return True
            
            if current_time - self._last_state_change >= self.half_open_timeout:
                return True
            return False
            
        return False

    def _record_success(self):
        """Record a successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self._last_state_change = time.time()
                self.success_count = 0
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self._last_state_change = time.time()
            self.success_count = 0

    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the circuit breaker."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_state_change": self._last_state_change,
            "failure_threshold": self.failure_threshold,
            "reset_timeout": self.reset_timeout,
            "half_open_timeout": self.half_open_timeout,
            "success_threshold": self.success_threshold
        }

    @abstractmethod
    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute the function with circuit breaker protection."""
        pass

class BasicCircuitBreaker(CircuitBreaker):
    """Basic circuit breaker implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_timeout: float = 30.0,
        success_threshold: int = 2,
        model_id: Optional[str] = None
    ):
        super().__init__(failure_threshold, reset_timeout, half_open_timeout, success_threshold, model_id)
    
    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute the function with basic circuit breaker protection."""
        if not self._can_execute():
            logger.warning("Circuit breaker is open, request rejected")
            raise Exception("Circuit is open")

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise e

class LLMCircuitBreaker(CircuitBreaker):
    """LLM-based circuit breaker implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_timeout: float = 30.0,
        success_threshold: int = 2,
        max_threshold: int = 10,
        min_threshold: int = 3,
        max_timeout: float = 300.0,
        min_timeout: float = 30.0,
        error_types: Optional[Dict[str, Dict[str, float]]] = None,
        model_id: Optional[str] = None
    ):
        super().__init__(failure_threshold, reset_timeout, half_open_timeout, success_threshold, model_id)
        self.max_threshold = max_threshold
        self.min_threshold = min_threshold
        self.max_timeout = max_timeout
        self.min_timeout = min_timeout
        self.error_types = error_types or {}
        self._error_counts: Dict[str, int] = {}

    def _adjust_thresholds(self, error_type: str):
        """Adjust thresholds based on error type."""
        if error_type in self.error_types:
            config = self.error_types[error_type]
            self.failure_threshold = min(
                self.max_threshold,
                max(
                    self.min_threshold,
                    int(self.failure_threshold * config["threshold_multiplier"])
                )
            )
            self.reset_timeout = min(
                self.max_timeout,
                max(
                    self.min_timeout,
                    self.reset_timeout * config["timeout_multiplier"]
                )
            )

    def _classify_error(self, error: Exception) -> str:
        """Classify the error type."""
        error_str = str(error).lower()
        
        if "rate limit" in error_str or "too many requests" in error_str:
            return "rate_limit"
        elif "timeout" in error_str or "timed out" in error_str:
            return "transient"
        elif "invalid" in error_str or "bad request" in error_str:
            return "permanent"
        else:
            return "unknown"

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute the function with LLM-based circuit breaker protection."""
        if not self._can_execute():
            logger.warning("Circuit breaker is open, request rejected")
            raise Exception("Circuit is open")

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            error_type = self._classify_error(e)
            self._adjust_thresholds(error_type)
            self._record_failure()
            raise e

    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the LLM circuit breaker."""
        state = super().get_state()
        state.update({
            "max_threshold": self.max_threshold,
            "min_threshold": self.min_threshold,
            "max_timeout": self.max_timeout,
            "min_timeout": self.min_timeout,
            "error_counts": self._error_counts
        })
        return state 