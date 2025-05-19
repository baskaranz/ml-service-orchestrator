import pytest
from unittest.mock import Mock, patch
from app.core.llm_circuit_breaker import LLMCircuitBreaker, LLMCircuitBreakerConfig
from app.core.circuit_breaker import CircuitState

@pytest.fixture
def mock_llm():
    return Mock()

@pytest.fixture
def llm_circuit_breaker(mock_llm):
    config = LLMCircuitBreakerConfig(
        failure_threshold=2,
        reset_timeout=1,
        half_open_timeout=1,
        max_retries=1,
        retry_delay=0.1
    )
    return LLMCircuitBreaker(mock_llm, config)

def test_llm_circuit_breaker_initialization(mock_llm):
    """Test LLM circuit breaker initialization."""
    config = LLMCircuitBreakerConfig()
    cb = LLMCircuitBreaker(mock_llm, config)
    
    assert cb.llm == mock_llm
    assert cb.config == config
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0

def test_llm_circuit_breaker_successful_execution(llm_circuit_breaker, mock_llm):
    """Test successful execution through LLM circuit breaker."""
    mock_llm.generate.return_value = "successful response"
    
    result = llm_circuit_breaker.execute("test prompt")
    assert result == "successful response"
    assert llm_circuit_breaker.state == CircuitState.CLOSED
    assert llm_circuit_breaker.failure_count == 0
    mock_llm.generate.assert_called_once_with("test prompt")

def test_llm_circuit_breaker_failure_threshold(llm_circuit_breaker, mock_llm):
    """Test LLM circuit breaker opens after reaching failure threshold."""
    mock_llm.generate.side_effect = Exception("LLM error")
    
    # First failure (with 1 retry, so 2 failures)
    with pytest.raises(Exception):
        llm_circuit_breaker.execute("test prompt")
    assert llm_circuit_breaker.state == CircuitState.OPEN
    assert llm_circuit_breaker.failure_count == 2

def test_llm_circuit_breaker_retry_mechanism(llm_circuit_breaker, mock_llm):
    """Test LLM circuit breaker retry mechanism."""
    # First call fails, second succeeds
    mock_llm.generate.side_effect = [Exception("LLM error"), "successful response"]
    
    result = llm_circuit_breaker.execute("test prompt")
    assert result == "successful response"
    assert llm_circuit_breaker.state == CircuitState.CLOSED
    assert llm_circuit_breaker.failure_count == 0
    assert mock_llm.generate.call_count == 2

def test_llm_circuit_breaker_max_retries_exceeded(llm_circuit_breaker, mock_llm):
    """Test LLM circuit breaker when max retries are exceeded."""
    mock_llm.generate.side_effect = Exception("LLM error")
    
    with pytest.raises(Exception):
        llm_circuit_breaker.execute("test prompt")
    
    assert mock_llm.generate.call_count == 2  # Initial attempt + 1 retry
    assert llm_circuit_breaker.state == CircuitState.OPEN

def test_llm_circuit_breaker_half_open_success(llm_circuit_breaker, mock_llm):
    """Test LLM circuit breaker closes after successful execution in half-open state."""
    # First call fails to open circuit
    mock_llm.generate.side_effect = Exception("LLM error")
    with pytest.raises(Exception):
        llm_circuit_breaker.execute("test prompt")
    
    # Wait for reset timeout
    import time
    time.sleep(1.1)
    
    # Next two calls should succeed (success_threshold=2)
    mock_llm.generate.side_effect = None
    mock_llm.generate.return_value = "successful response"
    result1 = llm_circuit_breaker.execute("test prompt")
    assert result1 == "successful response"
    assert llm_circuit_breaker.state == CircuitState.HALF_OPEN
    result2 = llm_circuit_breaker.execute("test prompt")
    assert result2 == "successful response"
    assert llm_circuit_breaker.state == CircuitState.CLOSED
    assert llm_circuit_breaker.failure_count == 0

def test_llm_circuit_breaker_half_open_failure(llm_circuit_breaker, mock_llm):
    """Test LLM circuit breaker reopens after failure in half-open state."""
    # First call fails to open circuit
    mock_llm.generate.side_effect = Exception("LLM error")
    with pytest.raises(Exception):
        llm_circuit_breaker.execute("test prompt")
    
    # Wait for reset timeout
    import time
    time.sleep(1.1)
    
    # Next call should fail again (with 1 retry, so 2 more failures)
    with pytest.raises(Exception):
        llm_circuit_breaker.execute("test prompt")
    assert llm_circuit_breaker.state == CircuitState.OPEN
    assert llm_circuit_breaker.failure_count == 4 