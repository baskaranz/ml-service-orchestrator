"""
Tests for LLM-based error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from app.utils.error_handling.llm_errors import LLMErrorClassifier, SmartRetryHandler
from app.models.config_models import LLMProviderConfig
from app.utils.error_handling.base import RetryConfig

@pytest.fixture
def llm_config() -> LLMProviderConfig:
    """Create a test LLM provider configuration."""
    return LLMProviderConfig(
        type="huggingface",
        model_name="mistralai/Mistral-7B-Instruct-v0.2",
        timeout=30,
        max_retries=3,
        api_key="test-key"
    )

@pytest.fixture
def error_classifier(llm_config: LLMProviderConfig) -> LLMErrorClassifier:
    """Create a test LLM error classifier."""
    return LLMErrorClassifier(config=llm_config)

@pytest.fixture
def retry_handler(llm_config: LLMProviderConfig) -> SmartRetryHandler:
    """Create a test smart retry handler."""
    retry_config = RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=10.0
    )
    return SmartRetryHandler(retry_config=retry_config, llm_config=llm_config)

@pytest.mark.asyncio
async def test_classify_transient_error(error_classifier: LLMErrorClassifier) -> None:
    """Test classifying a transient error."""
    with patch('app.utils.llm_providers.HuggingFaceProvider.generate') as mock_generate:
        mock_generate.return_value = "Classification: transient\nReasoning: Network timeout"
        
        error = ConnectionError("Connection timed out")
        context = {"attempt": 1, "max_retries": 3}
        
        result = await error_classifier.classify_error(error, context)
        assert result["classification"] == "transient"
        assert "Network timeout" in result["reasoning"]
        mock_generate.assert_called_once()

@pytest.mark.asyncio
async def test_classify_permanent_error(error_classifier: LLMErrorClassifier) -> None:
    """Test classifying a permanent error."""
    with patch('app.utils.llm_providers.HuggingFaceProvider.generate') as mock_generate:
        mock_generate.return_value = "Classification: permanent\nReasoning: Invalid input format"
        
        error = ValueError("Invalid input format")
        context = {"input": "invalid_data"}
        
        result = await error_classifier.classify_error(error, context)
        assert result["classification"] == "permanent"
        assert "Invalid input format" in result["reasoning"]
        mock_generate.assert_called_once()

@pytest.mark.asyncio
async def test_classify_rate_limit_error(error_classifier: LLMErrorClassifier) -> None:
    """Test classifying a rate limit error."""
    with patch('app.utils.llm_providers.HuggingFaceProvider.generate') as mock_generate:
        mock_generate.return_value = "Classification: rate_limit\nReasoning: Too many requests"
        
        error = ConnectionError("429 Too Many Requests")
        context = {"endpoint": "api/v1/predict"}
        
        result = await error_classifier.classify_error(error, context)
        assert result["classification"] == "rate_limit"
        assert "Too many requests" in result["reasoning"]
        mock_generate.assert_called_once()

@pytest.mark.asyncio
async def test_classify_authentication_error(error_classifier: LLMErrorClassifier) -> None:
    """Test classifying an authentication error."""
    with patch('app.utils.llm_providers.HuggingFaceProvider.generate') as mock_generate:
        mock_generate.return_value = "Classification: authentication\nReasoning: Invalid API key"
        
        error = ConnectionError("401 Unauthorized")
        context = {"endpoint": "api/v1/predict"}
        
        result = await error_classifier.classify_error(error, context)
        assert result["classification"] == "authentication"
        assert "Invalid API key" in result["reasoning"]
        mock_generate.assert_called_once()

@pytest.mark.asyncio
async def test_classify_input_validation_error(error_classifier: LLMErrorClassifier) -> None:
    """Test classifying an input validation error."""
    with patch('app.utils.llm_providers.HuggingFaceProvider.generate') as mock_generate:
        mock_generate.return_value = "Classification: input_validation\nReasoning: Invalid input format"
        
        error = ValueError("Invalid input format")
        context = {"input": "invalid_data"}
        
        result = await error_classifier.classify_error(error, context)
        assert result["classification"] == "input_validation"
        assert "Invalid input format" in result["reasoning"]
        mock_generate.assert_called_once()

@pytest.mark.asyncio
async def test_smart_retry_handler_transient_error(retry_handler: SmartRetryHandler) -> None:
    """Test smart retry handler with transient error."""
    with patch('app.utils.llm_providers.HuggingFaceProvider.generate') as mock_generate:
        mock_generate.return_value = "Classification: transient\nReasoning: Network timeout"
        
        error = ConnectionError("Connection timed out")
        context = {"attempt": 1, "max_retries": 3}
        
        should_retry = await retry_handler.should_retry(error, context)
        assert should_retry is True
        assert retry_handler.retry_count == 1

@pytest.mark.asyncio
async def test_smart_retry_handler_permanent_error(retry_handler: SmartRetryHandler) -> None:
    """Test smart retry handler with permanent error."""
    with patch('app.utils.llm_providers.HuggingFaceProvider.generate') as mock_generate:
        mock_generate.return_value = "Classification: permanent\nReasoning: Invalid input format"
        
        error = ValueError("Invalid input format")
        context = {"input": "invalid_data"}
        
        should_retry = await retry_handler.should_retry(error, context)
        assert should_retry is False
        assert retry_handler.retry_count == 0

@pytest.mark.asyncio
async def test_smart_retry_handler_rate_limit_error(retry_handler: SmartRetryHandler) -> None:
    """Test smart retry handler with rate limit error."""
    with patch('app.utils.llm_providers.HuggingFaceProvider.generate') as mock_generate:
        mock_generate.return_value = "Classification: rate_limit\nReasoning: Too many requests"
        
        error = ConnectionError("429 Too Many Requests")
        context = {"endpoint": "api/v1/predict"}
        
        should_retry = await retry_handler.should_retry(error, context)
        assert should_retry is True
        assert retry_handler.retry_count == 1

@pytest.mark.asyncio
async def test_smart_retry_handler_max_retries_exceeded(retry_handler: SmartRetryHandler) -> None:
    """Test smart retry handler when max retries are exceeded."""
    with patch('app.utils.llm_providers.HuggingFaceProvider.generate') as mock_generate:
        mock_generate.return_value = "Classification: transient\nReasoning: Network timeout"

        error = ConnectionError("Connection timed out")
        context = {"attempt": 3, "max_retries": 3}

        # Set retry count to max retries
        retry_handler.retry_count = retry_handler.retry_config.max_retries

        # Should not retry when max retries is reached
        should_retry = await retry_handler.should_retry(error, context)
        assert should_retry is False

        # Verify retry count was not incremented
        assert retry_handler.retry_count == retry_handler.retry_config.max_retries 