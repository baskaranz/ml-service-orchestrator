"""
Tests for LLM provider implementations.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.config_models import LLMProviderConfig
from app.utils.llm_providers import (
    HuggingFaceProvider,
    OllamaProvider,
    get_llm_provider,
)


@pytest.fixture
def huggingface_config():
    """Create a Hugging Face provider configuration."""
    return LLMProviderConfig(
        type="huggingface",
        model_name="mistralai/Mistral-7B-Instruct-v0.2",
        timeout=30,
        max_retries=3,
        api_key="test-key",
    )


@pytest.fixture
def ollama_config():
    """Create an Ollama provider configuration."""
    return LLMProviderConfig(
        type="ollama",
        model_name="mistral",
        timeout=30,
        max_retries=3,
        api_key=None,  # Ollama doesn't require an API key
    )


@pytest.mark.asyncio
async def test_huggingface_provider_generate(huggingface_config):
    """Test Hugging Face provider generate method."""
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[{"generated_text": "Test response"}])
        mock_post.return_value.__aenter__.return_value = mock_response

        provider = HuggingFaceProvider(
            model_id=huggingface_config.model_name,
            timeout=huggingface_config.timeout,
            max_retries=huggingface_config.max_retries,
            api_key=huggingface_config.api_key,
        )

        response = await provider.generate("Test prompt")
        assert response == "Test response"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_huggingface_provider_rate_limit(huggingface_config):
    """Test Hugging Face provider rate limit handling."""
    with patch("aiohttp.ClientSession.post") as mock_post:
        # First call: rate limit, second call: success
        mock_response1 = AsyncMock()
        mock_response1.status = 503
        mock_response1.__aenter__.return_value = mock_response1

        mock_response2 = AsyncMock()
        mock_response2.status = 200
        mock_response2.json = AsyncMock(return_value=[{"generated_text": "Test response"}])
        mock_response2.__aenter__.return_value = mock_response2

        mock_post.side_effect = [mock_response1, mock_response2]

        provider = HuggingFaceProvider(
            model_id=huggingface_config.model_name,
            timeout=huggingface_config.timeout,
            max_retries=huggingface_config.max_retries,
            api_key=huggingface_config.api_key,
        )

        response = await provider.generate("Test prompt")
        assert response == "Test response"
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_ollama_provider_generate(ollama_config):
    """Test Ollama provider generate method."""
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Test response"})
        mock_post.return_value.__aenter__.return_value = mock_response

        provider = OllamaProvider(
            model_name=ollama_config.model_name,
            timeout=ollama_config.timeout,
            max_retries=ollama_config.max_retries,
            api_key=ollama_config.api_key,
        )

        response = await provider.generate("Test prompt")
        assert response == "Test response"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_ollama_provider_retry(ollama_config):
    """Test Ollama provider retry mechanism."""
    with patch("aiohttp.ClientSession.post") as mock_post:
        # First call: error, second call: success
        mock_response1 = AsyncMock()
        mock_response1.status = 500
        mock_response1.__aenter__.return_value = mock_response1

        mock_response2 = AsyncMock()
        mock_response2.status = 200
        mock_response2.json = AsyncMock(return_value={"response": "Test response"})
        mock_response2.__aenter__.return_value = mock_response2

        mock_post.side_effect = [mock_response1, mock_response2]

        provider = OllamaProvider(
            model_name=ollama_config.model_name,
            timeout=ollama_config.timeout,
            max_retries=ollama_config.max_retries,
            api_key=ollama_config.api_key,
        )

        response = await provider.generate("Test prompt")
        assert response == "Test response"
        assert mock_post.call_count == 2


def test_get_llm_provider_huggingface(huggingface_config):
    """Test getting Hugging Face provider."""
    provider = get_llm_provider(huggingface_config)
    assert isinstance(provider, HuggingFaceProvider)
    assert provider.model_id == huggingface_config.model_name
    assert provider.timeout.total == huggingface_config.timeout
    assert provider.max_retries == huggingface_config.max_retries


def test_get_llm_provider_ollama(ollama_config):
    """Test getting Ollama provider."""
    provider = get_llm_provider(ollama_config)
    assert isinstance(provider, OllamaProvider)
    assert provider.model_name == ollama_config.model_name
    assert provider.timeout.total == ollama_config.timeout
    assert provider.max_retries == ollama_config.max_retries


def test_get_llm_provider_invalid_type():
    """Test getting provider with invalid type."""
    config = LLMProviderConfig(
        type="invalid", model_name="test-model", timeout=30, max_retries=3, api_key=None
    )
    with pytest.raises(ValueError, match="Unsupported LLM provider type"):
        get_llm_provider(config)
