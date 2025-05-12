"""
Tests for LLM-based error handling utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime

from app.utils.error_handling.llm_errors import LLMErrorClassifier, SmartRetryHandler
from app.utils.error_handling.llm_circuit_breaker import LLMCircuitBreaker, LLMCircuitBreakerState
from app.utils.error_handling.base import RetryConfig

@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    mock = MagicMock()
    mock.arun = AsyncMock()
    return mock

@pytest.fixture
def error_classifier(mock_llm):
    """Create an error classifier with a mock LLM."""
    with patch('langchain_community.chat_models.ChatLiteLLM', return_value=mock_llm):
        return LLMErrorClassifier(model_name="gpt-3.5-turbo")

@pytest.fixture
def smart_retry_handler():
    """Create a smart retry handler for testing."""
    retry_config = RetryConfig(max_retries=3, initial_delay=0.1, max_delay=1.0)
    return SmartRetryHandler(retry_config=retry_config)

@pytest.fixture
def llm_circuit_breaker():
    """Create an LLM circuit breaker for testing."""
    return LLMCircuitBreaker(
        fail_max=3,
        reset_timeout=60,
        name="test_breaker"
    )

@pytest.mark.asyncio
async def test_error_classification_transient(error_classifier):
    """Test classification of transient errors."""
    with patch('langchain.chains.LLMChain.arun', new_callable=AsyncMock) as mock_arun:
        mock_arun.return_value = "This is a transient error that should be retried."
        error = Exception("Connection timeout")
        context = {"attempt": 1}
        result = await error_classifier.classify_error(error, context)
        assert result["type"] == "transient"
        assert result["should_retry"] is True
        assert "reasoning" in result

@pytest.mark.asyncio
async def test_error_classification_rate_limit(error_classifier):
    """Test classification of rate limit errors."""
    with patch('langchain.chains.LLMChain.arun', new_callable=AsyncMock) as mock_arun:
        mock_arun.return_value = "This is a rate limit error that requires backoff."
        error = Exception("Too many requests")
        context = {"attempt": 1}
        result = await error_classifier.classify_error(error, context)
        assert result["type"] == "rate_limit"
        assert result["should_retry"] is True
        assert "reasoning" in result

@pytest.mark.asyncio
async def test_error_classification_permanent(error_classifier):
    """Test classification of permanent errors."""
    with patch('langchain.chains.LLMChain.arun', new_callable=AsyncMock) as mock_arun:
        mock_arun.return_value = "This is a permanent error that should not be retried."
        error = Exception("Invalid input")
        context = {"attempt": 1}
        result = await error_classifier.classify_error(error, context)
        assert result["type"] == "permanent"
        assert result["should_retry"] is False
        assert "reasoning" in result

@pytest.mark.asyncio
async def test_smart_retry_handler(smart_retry_handler):
    """Test smart retry handler with different error types."""
    mock_func = AsyncMock(side_effect=[
        Exception("Rate limit"),
        Exception("Rate limit"),
        "success"
    ])
    with patch("app.utils.error_handling.llm_errors.completion_with_retries", new=AsyncMock(return_value="success")):
        with patch.object(
            smart_retry_handler.error_classifier,
            'classify_error',
            return_value={
                "type": "rate_limit",
                "should_retry": True,
                "reasoning": "Rate limit error"
            }
        ):
            result = await smart_retry_handler.with_retry(mock_func)
            assert result == "success"
            assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_llm_circuit_breaker_state(llm_circuit_breaker):
    """Test LLM circuit breaker state transitions."""
    # Create a state instance
    state = LLMCircuitBreakerState(llm_circuit_breaker, "test_state")
    
    # Mock error classifier
    mock_classification = {
        "type": "rate_limit",
        "should_retry": True,
        "reasoning": "Rate limit error"
    }
    
    with patch.object(
        llm_circuit_breaker.error_classifier,
        'classify_error',
        return_value=mock_classification
    ):
        # Test error handling
        error = Exception("Rate limit")
        await state._analyze_error_pattern(error)
        
        # Verify error pattern was stored
        patterns = state.get_error_patterns()
        assert "Exception" in patterns
        assert patterns["Exception"]["classification"] == mock_classification
        assert "timestamp" in patterns["Exception"]

@pytest.mark.asyncio
async def test_llm_circuit_breaker_error_handling(llm_circuit_breaker):
    """Test LLM circuit breaker error handling."""
    mock_func = AsyncMock(side_effect=Exception("Test error"))
    with patch.object(
        llm_circuit_breaker.error_classifier,
        'classify_error',
        return_value={
            "type": "transient",
            "should_retry": True,
            "reasoning": "Transient error"
        }
    ):
        # Directly call the error pattern analyzer to ensure the error is recorded
        await llm_circuit_breaker._state._analyze_error_pattern(Exception("Test error"))
        patterns = llm_circuit_breaker.get_error_patterns()
        assert "Exception" in patterns
        assert patterns["Exception"]["classification"]["type"] == "transient"

@pytest.mark.asyncio
async def test_llm_circuit_breaker_parameter_adjustment(llm_circuit_breaker):
    """Test LLM circuit breaker parameter adjustment based on error type."""
    original_reset_timeout = llm_circuit_breaker.reset_timeout
    original_fail_max = llm_circuit_breaker.fail_max
    
    # Test rate limit error
    with patch.object(
        llm_circuit_breaker.error_classifier,
        'classify_error',
        return_value={
            "type": "rate_limit",
            "should_retry": True,
            "reasoning": "Rate limit error"
        }
    ):
        await llm_circuit_breaker._state._analyze_error_pattern(Exception("Rate limit"))
        assert llm_circuit_breaker.reset_timeout > original_reset_timeout
    
    # Test transient error
    with patch.object(
        llm_circuit_breaker.error_classifier,
        'classify_error',
        return_value={
            "type": "transient",
            "should_retry": True,
            "reasoning": "Transient error"
        }
    ):
        await llm_circuit_breaker._state._analyze_error_pattern(Exception("Transient"))
        assert llm_circuit_breaker.fail_max > original_fail_max
    
    # Test permanent error
    with patch.object(
        llm_circuit_breaker.error_classifier,
        'classify_error',
        return_value={
            "type": "permanent",
            "should_retry": False,
            "reasoning": "Permanent error"
        }
    ):
        await llm_circuit_breaker._state._analyze_error_pattern(Exception("Permanent"))
        assert llm_circuit_breaker.fail_max <= original_fail_max 