import pytest
import time
from app.core.circuit_breaker import CircuitBreaker, CircuitState

class TestCircuitBreaker(CircuitBreaker):
    """Concrete implementation of CircuitBreaker for testing."""
    def execute(self, func, *args, **kwargs):
        if not self._can_execute():
            raise Exception("Circuit is open")
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise e

def test_circuit_breaker_initial_state():
    """Test initial state of circuit breaker."""
    cb = TestCircuitBreaker()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.failure_threshold == 5
    assert cb.reset_timeout == 60
    assert cb.half_open_timeout == 30

def test_circuit_breaker_successful_execution():
    """Test successful execution through circuit breaker."""
    cb = TestCircuitBreaker()
    
    def success_func():
        return "success"
    
    result = cb.execute(success_func)
    assert result == "success"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0

def test_circuit_breaker_failure_threshold():
    """Test circuit breaker opens after reaching failure threshold."""
    cb = TestCircuitBreaker(failure_threshold=2)
    
    def failing_func():
        raise Exception("Test failure")
    
    # First failure
    with pytest.raises(Exception):
        cb.execute(failing_func)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1
    
    # Second failure - should open circuit
    with pytest.raises(Exception):
        cb.execute(failing_func)
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2

def test_circuit_breaker_reset_timeout():
    """Test circuit breaker transitions to half-open after reset timeout, and reopens on failure."""
    cb = TestCircuitBreaker(failure_threshold=1, reset_timeout=1)
    
    def failing_func():
        raise Exception("Test failure")
    
    # Cause circuit to open
    with pytest.raises(Exception):
        cb.execute(failing_func)
    assert cb.state == CircuitState.OPEN
    
    # Wait for reset timeout
    time.sleep(1.1)
    
    # Try to execute - this should trigger the state change to HALF_OPEN, but since it fails, it goes back to OPEN
    with pytest.raises(Exception):
        cb.execute(failing_func)
    assert cb.state == CircuitState.OPEN

def test_circuit_breaker_half_open_success():
    """Test circuit breaker closes after successful execution in half-open state."""
    cb = TestCircuitBreaker(failure_threshold=1, reset_timeout=1)
    
    def failing_func():
        raise Exception("Test failure")
    
    def success_func():
        return "success"
    
    # Cause circuit to open
    with pytest.raises(Exception):
        cb.execute(failing_func)
    
    # Wait for reset timeout
    time.sleep(1.1)
    
    # Execute successful function
    result = cb.execute(success_func)
    assert result == "success"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0

def test_circuit_breaker_half_open_failure():
    """Test circuit breaker reopens after failure in half-open state."""
    cb = TestCircuitBreaker(failure_threshold=1, reset_timeout=1)
    
    def failing_func():
        raise Exception("Test failure")
    
    # Cause circuit to open
    with pytest.raises(Exception):
        cb.execute(failing_func)
    
    # Wait for reset timeout
    time.sleep(1.1)
    
    # Try failing function again
    with pytest.raises(Exception):
        cb.execute(failing_func)
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2 