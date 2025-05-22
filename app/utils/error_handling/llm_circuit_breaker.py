"""
LLM-based circuit breaker implementation.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, cast

import pybreaker

from app.models.config_models import LLMProviderConfig
from app.utils.error_handling.llm_errors import LLMErrorClassifier
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LLMCircuitBreakerState(pybreaker.CircuitBreakerState):
    """Enhanced circuit breaker state with LLM-based error analysis."""

    def __init__(
        self,
        cb: "LLMCircuitBreaker",
        name: str,
        prev_state: Optional[pybreaker.CircuitBreakerState] = None,
        notify: bool = False,
    ):
        """Initialize the LLM circuit breaker state."""
        super().__init__(cb, name)
        self._error_patterns: Dict[str, Any] = {}
        self._original_reset_timeout = cb.reset_timeout
        self._original_fail_max = cb.fail_max

    async def _analyze_error_pattern(self, error: BaseException) -> None:
        """Analyze error pattern using LLM."""
        try:
            # Cast to LLMCircuitBreaker to access error_classifier
            breaker = cast(LLMCircuitBreaker, self._breaker)

            # Convert BaseException to Exception if needed
            error_to_analyze = error if isinstance(error, Exception) else Exception(str(error))

            classification = await breaker.error_classifier.classify_error(
                error_to_analyze,
                {
                    "circuit_state": self._breaker.current_state,
                    "failure_count": self._breaker.fail_counter,
                    "reset_timeout": self._breaker.reset_timeout,
                    "fail_max": self._breaker.fail_max,
                },
            )

            if classification["type"] == "rate_limit":
                # Adjust circuit breaker parameters for rate limits
                self._breaker.reset_timeout = min(
                    self._original_reset_timeout * 1.5, 300
                )  # Max 5 minutes
                logger.info(
                    f"Rate limit detected, adjusted reset timeout to {self._breaker.reset_timeout}s"
                )
            elif classification["type"] == "transient":
                # Be more lenient with transient errors
                self._breaker.fail_max = min(self._original_fail_max + 1, 10)
                logger.info(
                    f"Transient error detected, adjusted fail_max to {self._breaker.fail_max}"
                )
            elif classification["type"] == "permanent":
                # Be more strict with permanent errors
                self._breaker.fail_max = max(self._original_fail_max - 1, 3)
                logger.info(
                    f"Permanent error detected, adjusted fail_max to {self._breaker.fail_max}"
                )

            # Store the error pattern
            self._error_patterns[type(error).__name__] = {
                "classification": classification,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error in LLM analysis: {str(e)}")
            # Reset to original values if analysis fails
            self._breaker.reset_timeout = self._original_reset_timeout
            self._breaker.fail_max = self._original_fail_max

    def _handle_error(self, exc: BaseException, reraise: bool = True) -> None:
        """Handle a failed call to the guarded operation."""
        if self._breaker.is_system_error(exc):
            self._breaker._inc_counter()
            for listener in self._breaker.listeners:
                listener.failure(self._breaker, exc)

            # Run the async analysis in the event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a new event loop if the current one is running
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(self._analyze_error_pattern(exc))
            except Exception as e:
                logger.error(f"Error in failure analysis: {str(e)}")

            self.on_failure(exc)
        else:
            self._handle_success()

        if reraise:
            raise exc

    def get_error_patterns(self) -> Dict[str, Any]:
        """Get the current error patterns."""
        return self._error_patterns


class LLMCircuitBreaker(pybreaker.CircuitBreaker):
    """Enhanced circuit breaker with LLM-based error analysis."""

    def __init__(self, *args, llm_config: Optional[LLMProviderConfig] = None, **kwargs):
        """Initialize the LLM circuit breaker."""
        super().__init__(*args, **kwargs)
        self.error_classifier = LLMErrorClassifier(config=llm_config)
        self._state = LLMCircuitBreakerState(self, self.current_state)

    def get_error_patterns(self) -> Dict[str, Any]:
        """Get the current error patterns."""
        return self._state.get_error_patterns()
