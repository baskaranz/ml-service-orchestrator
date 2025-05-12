"""
LLM provider implementations.
"""

import os
from typing import Optional, Dict, Any
import aiohttp
from aiohttp import ClientTimeout
import asyncio

from app.models.config_models import LLMProviderConfig
from app.utils.logging import get_logger

logger = get_logger(__name__)

class BaseLLMProvider:
    """Base class for LLM providers."""
    
    async def generate(self, prompt: str) -> str:
        """Generate a response for the given prompt."""
        raise NotImplementedError

class HuggingFaceProvider(BaseLLMProvider):
    """Hugging Face API provider."""
    
    def __init__(
        self,
        model_id: Optional[str] = "mistralai/Mistral-7B-Instruct-v0.2",
        timeout: Optional[int] = 30,
        max_retries: Optional[int] = 3,
        api_key: Optional[str] = None
    ):
        """Initialize the Hugging Face provider."""
        self.model_id = model_id
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY")
        self.timeout = ClientTimeout(total=int(timeout or 30))
        self.max_retries = int(max_retries or 3)
        self.base_url = "https://api-inference.huggingface.co/models"
    
    async def generate(self, prompt: str) -> str:
        """Generate a response using Hugging Face API."""
        if not self.api_key:
            raise ValueError("Hugging Face API key not found")
        
        url = f"{self.base_url}/{self.model_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"inputs": prompt}
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for attempt in range(self.max_retries):
                try:
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result[0]["generated_text"]
                        elif response.status == 503:
                            # Model is loading
                            await asyncio.sleep(1)
                            continue
                        else:
                            response.raise_for_status()
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(1)
        
        raise Exception("Failed to generate response after all retries")

class OllamaProvider(BaseLLMProvider):
    """Ollama local provider."""
    
    def __init__(
        self,
        model_name: Optional[str] = "mistral",
        timeout: Optional[int] = 30,
        max_retries: Optional[int] = 3,
        api_key: Optional[str] = None
    ):
        """Initialize the Ollama provider."""
        self.model_name = model_name
        self.timeout = ClientTimeout(total=int(timeout or 30))
        self.max_retries = int(max_retries or 3)
        self.base_url = "http://localhost:11434/api/generate"
    
    async def generate(self, prompt: str) -> str:
        """Generate a response using Ollama API."""
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for attempt in range(self.max_retries):
                try:
                    async with session.post(self.base_url, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result["response"]
                        else:
                            response.raise_for_status()
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(1)
        
        raise Exception("Failed to generate response after all retries")

def get_llm_provider(config: LLMProviderConfig) -> BaseLLMProvider:
    """Get an LLM provider instance based on configuration."""
    if config.type == "huggingface":
        return HuggingFaceProvider(
            model_id=config.model_name,
            timeout=config.timeout,
            max_retries=config.max_retries,
            api_key=config.api_key
        )
    elif config.type == "ollama":
        return OllamaProvider(
            model_name=config.model_name,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
    else:
        raise ValueError(f"Unsupported LLM provider type: {config.type}") 