"""
Tests for LLM-based error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from app.utils.error_handling.llm_errors import LLMErrorClassifier, SmartRetryHandler
from app.models.config_models import LLMProviderConfig
from app.utils.error_handling.base import RetryConfig

class MockLLMProvider:
    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self._call_count = 0

    async def generate(self, prompt: str) -> str:
        self._call_count += 1
        if self._call_count == 1:
            return "Classification: rate_limit\nReasoning: Too many requests"
        elif self._call_count == 2:
            return "Classification: transient\nReasoning: Network timeout"
        elif self._call_count == 3:
            return "Classification: permanent\nReasoning: Invalid input format"
        elif self._call_count == 4:
            return "Classification: authentication\nReasoning: Invalid API key"
        elif self._call_count == 5:
            return "Classification: input_validation\nReasoning: Invalid input format"
        else:
            return "Classification: success\nReasoning: Operation successful"

class MockErrorClassifier(LLMErrorClassifier):
    def __init__(self, llm: MockLLMProvider):
        super().__init__(config=None)
        self.llm = llm

    async def classify_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        response = await self.llm.generate("")
        lines = response.strip().split("\n")
        classification = lines[0].split(":", 1)[1].strip()
        reasoning = lines[1].split(":", 1)[1].strip()
        return {
            "classification": classification,
            "reasoning": reasoning,
            "timestamp": "2024-03-21T00:00:00Z"
        }

@pytest.fixture
def test_llm_config():
    return LLMProviderConfig(
        type="huggingface",
        model_name="mistralai/Mistral-7B-Instruct-v0.2",
        timeout=30,
        max_retries=3,
        api_key="test-key"
    )

@pytest.fixture
def mock_llm(test_llm_config):
    return MockLLMProvider(test_llm_config)

@pytest.fixture
def error_classifier(mock_llm):
    return MockErrorClassifier(mock_llm)

@pytest.fixture
def error_handler(error_classifier, test_llm_config):
    handler = SmartRetryHandler(
        retry_config=RetryConfig(
            max_retries=3,
            initial_delay=0.01,  # speed up tests
            max_delay=0.05
        ),
        llm_config=test_llm_config
    )
    handler.error_classifier = error_classifier
    return handler

@pytest.mark.asyncio
async def test_llm_error_handling(error_handler):
    async def mock_operation():
        llm = error_handler.error_classifier.llm
        await llm.generate("")
        if llm._call_count >= 4:
            return "Success"
        raise Exception(f"Simulated error {llm._call_count - 1}")

    result = await error_handler.with_retry(mock_operation)
    assert result == "Success"

@pytest.mark.asyncio
async def test_classify_transient_error(error_classifier):
    error = ConnectionError("Connection timed out")
    context = {"attempt": 1, "max_retries": 3}
    # First call to generate returns rate_limit, second returns transient
    await error_classifier.llm.generate("")  # advance to transient
    result = await error_classifier.classify_error(error, context)
    assert result["classification"] == "transient"
    assert "Network timeout" in result["reasoning"]

@pytest.mark.asyncio
async def test_classify_permanent_error(error_classifier):
    error = ValueError("Invalid input format")
    context = {"input": "invalid_data"}
    # Advance to permanent (third call)
    await error_classifier.llm.generate("")  # rate_limit
    await error_classifier.llm.generate("")  # transient
    result = await error_classifier.classify_error(error, context)
    assert result["classification"] == "permanent"
    assert "Invalid input format" in result["reasoning"]

@pytest.mark.asyncio
async def test_classify_rate_limit_error(error_classifier):
    error = ConnectionError("429 Too Many Requests")
    context = {"endpoint": "api/v1/predict"}
    # First call to generate returns rate_limit
    result = await error_classifier.classify_error(error, context)
    assert result["classification"] == "rate_limit"
    assert "Too many requests" in result["reasoning"]

@pytest.mark.asyncio
async def test_classify_authentication_error(error_classifier):
    error = ConnectionError("401 Unauthorized")
    context = {"endpoint": "api/v1/predict"}
    # Advance to authentication (fourth call)
    await error_classifier.llm.generate("")  # rate_limit
    await error_classifier.llm.generate("")  # transient
    await error_classifier.llm.generate("")  # permanent
    result = await error_classifier.classify_error(error, context)
    assert result["classification"] == "authentication"
    assert "Invalid API key" in result["reasoning"]

@pytest.mark.asyncio
async def test_classify_input_validation_error(error_classifier):
    error = ValueError("Invalid input format")
    context = {"input": "invalid_data"}
    # Advance to input validation (fifth call)
    await error_classifier.llm.generate("")  # rate_limit
    await error_classifier.llm.generate("")  # transient
    await error_classifier.llm.generate("")  # permanent
    await error_classifier.llm.generate("")  # authentication
    result = await error_classifier.classify_error(error, context)
    assert result["classification"] == "input_validation"
    assert "Invalid input format" in result["reasoning"]

@pytest.mark.asyncio
async def test_smart_retry_handler_transient_error(error_handler):
    error = ConnectionError("Connection timed out")
    context = {"attempt": 1, "max_retries": 3}
    should_retry = await error_handler.should_retry(error, context)
    assert should_retry is True
    assert error_handler.retry_count == 1 