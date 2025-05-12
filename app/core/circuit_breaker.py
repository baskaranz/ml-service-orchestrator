from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker(ABC):
    """Base class for circuit breaker implementations."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        half_open_timeout: int = 30
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
        self._last_state_change = time.time()

    def _can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        current_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True
            
        if self.state == CircuitState.OPEN:
            if current_time - self._last_state_change >= self.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                self._last_state_change = current_time
                return True
            return False
            
        if self.state == CircuitState.HALF_OPEN:
            if current_time - self._last_state_change >= self.half_open_timeout:
                return True
            return False
            
        return False

    def _record_success(self):
        """Record a successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self._last_state_change = time.time()
        self.failure_count = 0

    def _record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self._last_state_change = time.time()

    @abstractmethod
    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute the function with circuit breaker protection."""
        pass 