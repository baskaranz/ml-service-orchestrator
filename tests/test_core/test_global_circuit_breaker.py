"""
Tests for the global circuit breaker implementation.
"""

import logging
import time

import pytest

from app.core.global_circuit_breaker import CircuitBreaker, CircuitState, global_circuit_breaker

# Set up logger for tests
logger = logging.getLogger(__name__)


@pytest.fixture
def reset_global_circuit_breaker():
    """Reset the global circuit breaker before each test."""
    global_circuit_breaker._circuit_breakers = {}
    global_circuit_breaker._config = {}
    yield
    global_circuit_breaker._circuit_breakers = {}
    global_circuit_breaker._config = {}


class TestGlobalCircuitBreaker:
    """Test cases for the global circuit breaker functionality."""

    def test_get_circuit_breaker_creates_new_instance(self, reset_global_circuit_breaker):
        """Test getting a circuit breaker creates a new instance if it doesn't exist."""
        cb = global_circuit_breaker.get_circuit_breaker("test-model")
        assert isinstance(cb, CircuitBreaker)
        assert cb.model_id == "test-model"
        assert "test-model" in global_circuit_breaker._circuit_breakers

    def test_get_circuit_breaker_returns_existing_instance(self, reset_global_circuit_breaker):
        """Test getting a circuit breaker returns the same instance for the same model ID."""
        cb1 = global_circuit_breaker.get_circuit_breaker("test-model")
        cb2 = global_circuit_breaker.get_circuit_breaker("test-model")
        assert cb1 is cb2

    def test_configure_updates_global_config(self, reset_global_circuit_breaker):
        """Test that configure updates the global configuration."""
        config = {
            "basic": {
                "enabled": True,
                "failure_threshold": 3,
                "reset_timeout": 10.0,
                "half_open_timeout": 5.0,
                "success_threshold": 2,
            },
            "llm": {
                "enabled": True,
                "failure_threshold": 3,
                "reset_timeout": 10.0,
                "half_open_timeout": 5.0,
                "success_threshold": 2,
                "model_timeout_multiplier": 1.5,
                "max_timeout": 60.0,
                "error_type_weights": {"temporary": 1.0, "throttling": 2.0, "permanent": 3.0},
            },
        }
        global_circuit_breaker.configure(config)
        # The config should be wrapped in a 'default' key
        expected_config = {"default": config}
        assert global_circuit_breaker._config == expected_config

    def test_circuit_breaker_execution_success(self, reset_global_circuit_breaker):
        """Test successful execution through the circuit breaker."""
        # Configure the circuit breaker with a basic configuration
        config = {
            "basic": {
                "enabled": True,
                "failure_threshold": 3,
                "reset_timeout": 10.0,
                "half_open_timeout": 5.0,
                "success_threshold": 2,
            },
            "llm": {
                "enabled": True,
                "failure_threshold": 3,
                "reset_timeout": 10.0,
                "half_open_timeout": 5.0,
                "success_threshold": 2,
                "model_timeout_multiplier": 1.5,
                "max_timeout": 60.0,
                "error_type_weights": {"temporary": 1.0, "throttling": 2.0, "permanent": 3.0},
            },
        }
        global_circuit_breaker.configure(config)

        cb = global_circuit_breaker.get_circuit_breaker("test-model")

        def success_func():
            return "success"

        result = cb.execute(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_execution_failure(self, reset_global_circuit_breaker):
        """Test failed execution through the circuit breaker."""
        # Configure a low failure threshold for testing
        config = {
            "basic": {
                "enabled": True,
                "failure_threshold": 1,  # Low threshold for testing
                "reset_timeout": 10.0,
                "half_open_timeout": 5.0,
                "success_threshold": 2,
            },
            "llm": {
                "enabled": True,
                "failure_threshold": 3,
                "reset_timeout": 10.0,
                "half_open_timeout": 5.0,
                "success_threshold": 2,
                "model_timeout_multiplier": 1.5,
                "max_timeout": 60.0,
                "error_type_weights": {"temporary": 1.0, "throttling": 2.0, "permanent": 3.0},
            },
        }
        global_circuit_breaker.configure(config)

        cb = global_circuit_breaker.get_circuit_breaker("test-model")

        def failing_func():
            raise Exception("Test failure")

        # First failure should be allowed
        with pytest.raises(Exception):
            cb.execute(failing_func)

        # Second failure should trigger circuit open
        with pytest.raises(Exception) as exc_info:
            cb.execute(failing_func)

        assert "Circuit breaker is open for model test-model" in str(exc_info.value)
        assert cb.state == CircuitState.OPEN

    def test_circuit_breaker_reset(self, reset_global_circuit_breaker, monkeypatch):
        """Test resetting the circuit breaker."""
        # Configure a low failure threshold and short timeouts for testing
        config = {
            "basic": {
                "enabled": True,
                "failure_threshold": 1,  # Low threshold for testing
                "reset_timeout": 1.0,  # Minimum allowed timeout is 1.0
                "half_open_timeout": 1.0,  # Minimum allowed timeout is 1.0
                "success_threshold": 2,
            },
            "llm": {
                "enabled": True,
                "failure_threshold": 3,
                "reset_timeout": 10.0,
                "half_open_timeout": 5.0,
                "success_threshold": 2,
                "model_timeout_multiplier": 1.5,
                "max_timeout": 60.0,
                "error_type_weights": {"temporary": 1.0, "throttling": 2.0, "permanent": 3.0},
            },
        }
        global_circuit_breaker.configure(config)

        cb = global_circuit_breaker.get_circuit_breaker("test-model")

        def failing_func():
            raise Exception("Test failure")

        # Trigger circuit open
        with pytest.raises(Exception):
            cb.execute(failing_func)

        logger.debug(f"Initial state after failure: {cb.state}")
        logger.debug(f"Last state change: {cb._last_state_change}")
        logger.debug(f"Current time: {time.time()}")
        logger.debug(f"Reset timeout: {cb.config.basic.reset_timeout}")

        # Wait for reset timeout plus a small buffer
        sleep_duration = cb.config.basic.reset_timeout + 0.1
        logger.debug(f"Sleeping for {sleep_duration} seconds...")
        time.sleep(sleep_duration)

        # Log state after sleep
        logger.debug(f"State after sleep: {cb.state}")
        logger.debug(f"Time since state change: {time.time() - cb._last_state_change}")

        # Call _can_execute to trigger the state transition to HALF_OPEN
        can_execute = cb._can_execute()
        logger.debug(f"After _can_execute(), state: {cb.state}, can_execute: {can_execute}")

        # Verify we're in HALF_OPEN state
        assert cb.state == CircuitState.HALF_OPEN, f"Expected HALF_OPEN state, but got {cb.state}"

        # First successful execution (should increment success_count but stay in HALF_OPEN)
        def success_func():
            return "success"

        # Execute the success function and verify the result - first time
        result = cb.execute(success_func)
        assert result == "success"

        # Should still be in HALF_OPEN state after first success (need 2 successes)
        assert (
            cb.state == CircuitState.HALF_OPEN
        ), f"Expected HALF_OPEN state after first success, but got {cb.state}"
        assert (
            cb.success_count == 1
        ), f"Expected success_count to be 1 after first success, but got {cb.success_count}"

        # Second successful execution should transition to CLOSED
        result = cb.execute(success_func)
        assert result == "success"

        # Now the circuit should be CLOSED after two successful executions
        assert (
            cb.state == CircuitState.CLOSED
        ), f"Expected CLOSED state after second successful execution, but got {cb.state}"
        assert (
            cb.success_count == 2
        ), f"Expected success_count to be 2 after second success, but got {cb.success_count}"

        # Verify failure count was reset
        assert cb.failure_count == 0, f"Expected failure_count to be 0, but got {cb.failure_count}"

    def test_per_model_overrides(self, reset_global_circuit_breaker):
        """Test that per-model overrides work correctly."""
        # Set up global config with basic and llm settings
        global_circuit_breaker.configure(
            {
                "basic": {
                    "enabled": True,
                    "failure_threshold": 5,
                    "reset_timeout": 60.0,
                    "half_open_timeout": 30.0,
                    "success_threshold": 2,
                },
                "llm": {
                    "enabled": True,
                    "failure_threshold": 3,
                    "reset_timeout": 10.0,
                    "half_open_timeout": 5.0,
                    "success_threshold": 2,
                    "model_timeout_multiplier": 1.5,
                    "max_timeout": 60.0,
                    "error_type_weights": {"temporary": 1.0, "throttling": 2.0, "permanent": 3.0},
                },
                "per_model_overrides": {"special-model": {"basic": {"failure_threshold": 2}}},
            }
        )

        # Default model should use global config
        default_cb = global_circuit_breaker.get_circuit_breaker("default-model")
        assert default_cb.config.basic.failure_threshold == 5

        # Special model should use override
        special_cb = global_circuit_breaker.get_circuit_breaker("special-model")
        assert special_cb.config.basic.failure_threshold == 2
