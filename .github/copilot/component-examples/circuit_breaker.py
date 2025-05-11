"""
Circuit Breaker implementation for the ML Orchestrator.

This example demonstrates the circuit breaker pattern used in the ML Orchestrator service
to provide fault tolerance for model requests.
"""

import asyncio
import time
from enum import Enum
from typing import Optional, Dict, Any
import logging

# Configure logging
logger = logging.getLogger(__name__)

class CircuitState(str, Enum):
    """Enum for circuit breaker states."""
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance.
    
    The circuit breaker provides fault tolerance by tracking failures and temporarily
    disabling requests to a service when it appears to be failing. This prevents
    cascading failures and allows the service time to recover.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests are allowed through
    - OPEN: Service appears to be failing, requests are blocked
    - HALF_OPEN: Testing if the service has recovered by allowing a single request
    
    Usage:
        circuit_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=30.0)
        
        # For each request
        if circuit_breaker.is_open():
            # Don't make the request, fail fast
            raise CircuitBreakerError(...)
        
        try:
            # Make the request
            response = await make_request()
            
            # Record success
            circuit_breaker.record_success()
            
            return response
        except Exception as e:
            # Record failure
            circuit_breaker.record_failure()
            raise
    """
    
    def __init__(self, failure_threshold: int, reset_timeout: float):
        """Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Seconds to wait before attempting to close the circuit
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
        self.test_request_in_progress = False
        
        # For metrics/monitoring
        self.total_failures = 0
        self.total_successes = 0
        self.open_time = 0
        self.transition_timestamps: Dict[str, float] = {}
    
    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Test request failed, circuit breaker reopened")
            self._transition_to(CircuitState.OPEN)
            self.test_request_in_progress = False
        elif self.failure_count >= self.failure_threshold and self.state == CircuitState.CLOSED:
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            self._transition_to(CircuitState.OPEN)
    
    def record_success(self) -> None:
        """Record a success and potentially close the circuit."""
        self.total_successes += 1
        
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Test request succeeded, circuit breaker closed")
            self._transition_to(CircuitState.CLOSED)
            self.failure_count = 0
            self.test_request_in_progress = False
        else:
            # In closed state, just reset failure count
            self.failure_count = 0
    
    def is_open(self) -> bool:
        """Check if the circuit is open.
        
        Returns:
            True if the circuit is open and requests should be blocked,
            False if requests should be allowed through
        """
        if self.state == CircuitState.OPEN:
            # Check if it's time to try a test request
            if time.time() - self.last_failure_time > self.reset_timeout:
                logger.info(f"Transitioning to half-open state after {self.reset_timeout}s")
                self._transition_to(CircuitState.HALF_OPEN)
                return False  # Allow the test request
            return True  # Still open, block requests
        
        if self.state == CircuitState.HALF_OPEN and self.test_request_in_progress:
            return True  # Only one test request at a time
        
        if self.state == CircuitState.HALF_OPEN:
            # Mark that we're starting a test request
            self.test_request_in_progress = True
            logger.debug("Allowing test request in half-open state")
            return False  # Allow the test request
        
        return False  # Circuit is closed, allow requests
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state and record the timestamp.
        
        Args:
            new_state: The new circuit state
        """
        old_state = self.state
        self.state = new_state
        timestamp = time.time()
        self.transition_timestamps[f"{old_state}_to_{new_state}"] = timestamp
        
        if new_state == CircuitState.OPEN:
            self.open_time = timestamp
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics about the circuit breaker.
        
        Returns:
            Dictionary with metric data
        """
        now = time.time()
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "last_failure_time": self.last_failure_time,
            "time_since_last_failure": now - self.last_failure_time if self.last_failure_time > 0 else None,
            "open_duration": now - self.open_time if self.state == CircuitState.OPEN else None,
            "transitions": self.transition_timestamps
        }

class CircuitBreakerError(Exception):
    """Exception raised when a circuit breaker is open."""
    
    def __init__(self, model_id: str, message: Optional[str] = None):
        """Initialize the exception.
        
        Args:
            model_id: The model ID with the open circuit
            message: Optional error message
        """
        self.model_id = model_id
        self.message = message or f"Circuit breaker is open for model {model_id}"
        super().__init__(self.message)

class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self, default_failure_threshold: int = 5, default_reset_timeout: float = 30.0):
        """Initialize the circuit breaker registry.
        
        Args:
            default_failure_threshold: Default number of failures before opening circuits
            default_reset_timeout: Default seconds to wait before attempting to close circuits
        """
        self.default_failure_threshold = default_failure_threshold
        self.default_reset_timeout = default_reset_timeout
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def get_circuit_breaker(
        self, 
        key: str, 
        failure_threshold: Optional[int] = None, 
        reset_timeout: Optional[float] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker.
        
        Args:
            key: Unique identifier for the circuit breaker
            failure_threshold: Optional override for failure threshold
            reset_timeout: Optional override for reset timeout
            
        Returns:
            The circuit breaker for the key
        """
        if key not in self.circuit_breakers:
            # Use provided values or defaults
            self.circuit_breakers[key] = CircuitBreaker(
                failure_threshold=failure_threshold or self.default_failure_threshold,
                reset_timeout=reset_timeout or self.default_reset_timeout
            )
        
        return self.circuit_breakers[key]
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers.
        
        Returns:
            Dictionary mapping keys to circuit breaker metrics
        """
        return {key: cb.get_metrics() for key, cb in self.circuit_breakers.items()}


# Example usage
async def example_usage():
    """Example usage of the circuit breaker."""
    # Create a circuit breaker registry
    registry = CircuitBreakerRegistry()
    
    # Get a circuit breaker for a specific model
    circuit_breaker = registry.get_circuit_breaker("example_model")
    
    # Simulate some requests
    for i in range(10):
        try:
            if circuit_breaker.is_open():
                print(f"Request {i}: Circuit is open, skipping request")
                continue
            
            # Simulate a request that might fail
            print(f"Request {i}: Making request")
            if i % 3 == 0:  # Simulate failure every 3rd request
                raise Exception("Simulated failure")
            
            # Simulate success
            print(f"Request {i}: Request succeeded")
            circuit_breaker.record_success()
            
        except Exception as e:
            print(f"Request {i}: Request failed - {str(e)}")
            circuit_breaker.record_failure()
        
        # Wait a bit
        await asyncio.sleep(1)
    
    # Print final metrics
    print("\nFinal metrics:")
    import json
    print(json.dumps(circuit_breaker.get_metrics(), indent=2))


# Run the example if executed directly
if __name__ == "__main__":
    asyncio.run(example_usage())