"""
Global circuit breaker implementation for managing model endpoints.

This module provides a singleton GlobalCircuitBreaker that manages circuit breakers
for all model endpoints with platform-level configuration and per-model overrides.
"""

import logging
import time
from enum import Enum
from threading import Lock
from typing import Awaitable, Callable, Dict, Optional, TypeVar

from app.core.exceptions import CircuitBreakerError
from app.models.config_models import CircuitBreakerConfig

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker implementation for individual model endpoints."""

    def __init__(self, model_id: str, config: CircuitBreakerConfig, parent: "GlobalCircuitBreaker"):
        """Initialize the circuit breaker.

        Args:
            model_id: Unique identifier for the model
            config: Circuit breaker configuration
            parent: Reference to the global circuit breaker instance
        """
        self.model_id = model_id
        self.config = config
        self.parent = parent

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self._last_state_change = time.time()
        self._lock = Lock()

    def _can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        if not self.config.basic.enabled:
            return True

        current_time = time.time()

        with self._lock:
            logger.debug(
                f"Checking if execution is allowed for {self.model_id}. "
                f"Current state: {self.state}, "
                f"Time since state change: {current_time - self._last_state_change:.2f}s"
            )

            if self.state == CircuitState.OPEN:
                # Check if we should transition to half-open
                time_since_state_change = current_time - self._last_state_change
                if time_since_state_change >= self.config.basic.reset_timeout:
                    logger.debug(
                        f"{time_since_state_change:.2f}s since state change, "
                        f"transitioning to HALF_OPEN for model {self.model_id}"
                    )
                    self._transition(CircuitState.HALF_OPEN, current_time)
                    return True
                logger.debug(
                    f"Circuit breaker OPEN for model {self.model_id}, "
                    f"waiting {self.config.basic.reset_timeout - time_since_state_change:.2f}s "
                    f"before trying HALF_OPEN"
                )
                return False

            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.HALF_OPEN:
                time_in_half_open = current_time - self._last_state_change
                if time_in_half_open >= self.config.basic.half_open_timeout:
                    logger.debug(
                        f"In HALF_OPEN state for {time_in_half_open:.2f}s, "
                        f"which exceeds half_open_timeout of {self.config.basic.half_open_timeout}s. "
                        f"Transitioning back to OPEN state."
                    )
                    self._transition(CircuitState.OPEN, current_time)
                    return False
                return True

            logger.warning(f"Unexpected circuit breaker state: {self.state}")
            return False

    def _transition(self, new_state: CircuitState, timestamp: float):
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state
        self._last_state_change = timestamp

        # Reset counters when transitioning to HALF_OPEN state
        if new_state == CircuitState.HALF_OPEN:
            self.failure_count = 0
            self.success_count = 0

        logger.info(
            f"Circuit breaker for {self.model_id} transitioned from {old_state} to {new_state}",
            extra={
                "model_id": self.model_id,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
            },
        )

    def _record_success(self):
        """Record a successful execution."""
        if not self.config.basic.enabled:
            return

        current_time = time.time()
        with self._lock:
            logger.debug(
                f"Recording success for model {self.model_id}: "
                f"state={self.state}, "
                f"success_count={self.success_count + 1}/"
                f"{self.config.basic.success_threshold}"
            )

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                logger.debug(
                    f"In HALF_OPEN state, success count incremented to {self.success_count} "
                    f"(threshold: {self.config.basic.success_threshold})"
                )
                if self.success_count >= self.config.basic.success_threshold:
                    logger.debug(
                        f"Success threshold reached for model {self.model_id}, "
                        f"transitioning to CLOSED state"
                    )
                    self._transition(CircuitState.CLOSED, current_time)
                    self.failure_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0
                logger.debug("In CLOSED state, reset failure count to 0")

    def _record_failure(self):
        """Record a failed execution."""
        if not self.config.basic.enabled:
            logger.debug(f"Circuit breaker is disabled for model {self.model_id}")
            return

        current_time = time.time()

        with self._lock:
            self.failure_count += 1
            self.last_failure_time = current_time

            logger.debug(
                f"Recording failure for model {self.model_id}: "
                f"state={self.state}, "
                f"failure_count={self.failure_count}/"
                f"{self.config.basic.failure_threshold}"
            )

            if self.state == CircuitState.HALF_OPEN:
                logger.debug(f"Transitioning from HALF_OPEN to OPEN for model {self.model_id}")
                self._transition(CircuitState.OPEN, current_time)
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.basic.failure_threshold:
                    logger.debug(
                        f"Failure threshold reached for model {self.model_id}, "
                        f"transitioning to OPEN state"
                    )
                    self._transition(CircuitState.OPEN, current_time)
                else:
                    logger.debug(
                        f"Failure count {self.failure_count} below threshold "
                        f"{self.config.basic.failure_threshold} for model {self.model_id}"
                    )
            else:
                logger.debug(
                    f"No state transition needed for model {self.model_id} in state {self.state}"
                )

    def get_state(self) -> dict:
        """Get the current state of the circuit breaker."""
        with self._lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
                "last_state_change": self._last_state_change,
                "config": self.config.model_dump(),
            }

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a function with circuit breaker protection."""
        if not self._can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker is open for model {self.model_id}", model_id=self.model_id
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            if isinstance(e, CircuitBreakerError):
                if not getattr(e, "model_id", None):
                    e.model_id = self.model_id
                raise
            # Wrap non-CircuitBreakerError exceptions in a CircuitBreakerError
            raise CircuitBreakerError(
                f"Circuit breaker error for model {self.model_id}: {str(e)}", model_id=self.model_id
            ) from e

    async def execute_async(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute an async function with circuit breaker protection."""
        if not self._can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker is open for model {self.model_id}", model_id=self.model_id
            )

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            if isinstance(e, CircuitBreakerError):
                if not getattr(e, "model_id", None):
                    e.model_id = self.model_id
                raise
            # Wrap non-CircuitBreakerError exceptions in a CircuitBreakerError
            raise CircuitBreakerError(
                f"Circuit breaker error for model {self.model_id}: {str(e)}", model_id=self.model_id
            ) from e


class GlobalCircuitBreaker:
    """Global circuit breaker manager.

    This class manages circuit breakers for all model endpoints with platform-level
    configuration and per-model overrides.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config=None):
        """Initialize the global circuit breaker."""
        if self._initialized:
            return

        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._config = config or {}
        self._lock = Lock()
        self._initialized = True

    def configure(self, config: dict):
        """Update the global configuration.

        Args:
            config: The configuration dictionary. Can be either a direct configuration
                   or a dictionary with a "default" key containing the configuration.
        """
        with self._lock:
            # If the config has a 'default' key, use that as the base config
            # Otherwise, use the entire config as the base config
            if "default" in config or "per_model_overrides" in config:
                self._config = config
            else:
                self._config = {"default": config}

    def get_circuit_breaker(
        self, model_id: str, config_override: Optional[dict] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a model.

        Args:
            model_id: Unique identifier for the model
            config_override: Optional model-specific configuration override

        Returns:
            CircuitBreaker: The circuit breaker instance for the model
        """
        with self._lock:
            if model_id not in self._circuit_breakers:
                # Get the base config from global settings
                global_config = self._config.get("default", {})

                # Apply model-specific overrides if any
                model_overrides = self._config.get("per_model_overrides", {}).get(model_id, {})

                # Merge configs (override takes precedence)
                config = {**global_config, **model_overrides}
                if config_override:
                    config.update(config_override)

                # Convert to Pydantic model
                cb_config = CircuitBreakerConfig(**config)

                self._circuit_breakers[model_id] = CircuitBreaker(
                    model_id=model_id, config=cb_config, parent=self
                )

                logger.info(
                    f"Created new circuit breaker for model {model_id}",
                    extra={"model_id": model_id, "config": config},
                )

            return self._circuit_breakers[model_id]

    def get_all_states(self) -> dict:
        """Get the state of all circuit breakers."""
        with self._lock:
            return {model_id: cb.get_state() for model_id, cb in self._circuit_breakers.items()}

    def reset(self, model_id: Optional[str] = None):
        """Reset circuit breaker(s).

        Args:
            model_id: If provided, reset only this model's circuit breaker.
                     If None, reset all circuit breakers.
        """
        with self._lock:
            if model_id:
                if model_id in self._circuit_breakers:
                    self._circuit_breakers[model_id]._transition(CircuitState.CLOSED, time.time())
            else:
                for cb in self._circuit_breakers.values():
                    cb._transition(CircuitState.CLOSED, time.time())


# Global instance
global_circuit_breaker = GlobalCircuitBreaker()
