"""
Tests for platform configuration management.
"""

from unittest.mock import mock_open, patch

import pytest

from app.config.platform_config import PlatformConfig
from app.models.config_models import LLMProviderConfig


@pytest.fixture
def mock_config_yaml() -> str:
    """Create a mock YAML configuration."""
    return """
    # Default provider configuration
    default_provider:
      type: "huggingface"
      model_name: "mistralai/Mistral-7B-Instruct-v0.2"
      timeout: 30.0
      max_retries: 3

    # Environment-specific overrides
    environments:
      development:
        type: "ollama"
        model_name: "mistral"
        timeout: 30
        max_retries: 3

      production:
        type: "huggingface"
        model_name: "mistralai/Mistral-7B-Instruct-v0.2"
        timeout: 45
        max_retries: 5

      test:
        type: "huggingface"
        model_name: "google/flan-t5-small"
        timeout: 10
        max_retries: 2
    """


@pytest.fixture
def platform_config(mock_config_yaml: str) -> PlatformConfig:
    """Create a test platform config instance."""
    with patch("builtins.open", mock_open(read_data=mock_config_yaml)):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("os.getenv", return_value="development"):
                config = PlatformConfig()
                return config


def test_platform_config_initialization(platform_config: PlatformConfig) -> None:
    """Test platform config initialization."""
    assert platform_config.config_dir == "config/platform"
    assert platform_config._llm_config is not None
    assert isinstance(platform_config._llm_config, LLMProviderConfig)
    assert platform_config._llm_config.type == "ollama"  # Development environment


def test_platform_config_load_config(platform_config: PlatformConfig) -> None:
    """Test loading platform configuration."""
    assert platform_config._llm_config is not None
    assert platform_config._llm_config.type == "ollama"
    assert platform_config._llm_config.model_name == "mistral"
    assert platform_config._llm_config.timeout == 30
    assert platform_config._llm_config.max_retries == 3


def test_platform_config_get_llm_config(platform_config: PlatformConfig) -> None:
    """Test getting LLM provider configuration."""
    llm_config = platform_config.llm_config
    assert llm_config is not None
    assert llm_config.type == "ollama"
    assert llm_config.model_name == "mistral"
    assert llm_config.timeout == 30
    assert llm_config.max_retries == 3


def test_platform_config_missing_config_file() -> None:
    """Test handling missing configuration file."""
    with patch("pathlib.Path.exists", return_value=False):
        config = PlatformConfig()
        assert config._llm_config is None


def test_platform_config_invalid_yaml() -> None:
    """Test handling invalid YAML configuration."""
    with patch("builtins.open", mock_open(read_data="invalid: yaml: content")):
        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(Exception):
                PlatformConfig()


def test_platform_config_missing_llm_provider() -> None:
    """Test handling missing LLM provider configuration."""
    with patch("builtins.open", mock_open(read_data="{}")):
        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(Exception):
                PlatformConfig()
