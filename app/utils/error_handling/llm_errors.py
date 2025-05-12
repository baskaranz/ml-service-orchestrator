"""
LLM-based error handling utilities.
"""

from typing import Any, Dict, Optional, Callable
import json
import logging
import asyncio
from datetime import datetime

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatLiteLLM
from litellm import completion_with_retries

from app.utils.error_handling.base import BaseErrorHandler, RetryConfig
from app.utils.logging import get_logger

logger = get_logger(__name__)

class LLMErrorClassifier:
    """Classifies errors using LLM to determine retry strategy."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """Initialize the error classifier."""
        self.llm = ChatLiteLLM(model=model_name)
        self.prompt = PromptTemplate(
            input_variables=["error_message", "error_type", "context"],
            template="""
            Analyze this error and classify it:
            Error Type: {error_type}
            Error Message: {error_message}
            Context: {context}
            
            Classify this error as one of:
            1. Transient (should retry)
            2. Permanent (should not retry)
            3. Rate Limit (should retry with backoff)
            4. Authentication (should not retry)
            5. Input Validation (should not retry)
            
            Provide reasoning for your classification.
            """
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    async def classify_error(self, error: Exception, context: dict) -> dict:
        """Classify an error using LLM."""
        try:
            result = await self.chain.arun(
                error_message=str(error),
                error_type=type(error).__name__,
                context=json.dumps(context)
            )
            return self._parse_classification(result)
        except Exception as e:
            logger.error(f"Error in LLM classification: {str(e)}")
            # Default to transient error if classification fails
            return {
                "type": "transient",
                "should_retry": True,
                "reasoning": "Classification failed, defaulting to transient"
            }

    def _parse_classification(self, result: str) -> dict:
        """Parse the LLM classification result."""
        try:
            # Extract the classification type
            if "transient" in result.lower():
                return {"type": "transient", "should_retry": True, "reasoning": result}
            elif "permanent" in result.lower():
                return {"type": "permanent", "should_retry": False, "reasoning": result}
            elif "rate limit" in result.lower():
                return {"type": "rate_limit", "should_retry": True, "reasoning": result}
            elif "authentication" in result.lower():
                return {"type": "authentication", "should_retry": False, "reasoning": result}
            elif "input validation" in result.lower():
                return {"type": "input_validation", "should_retry": False, "reasoning": result}
            else:
                return {"type": "unknown", "should_retry": True, "reasoning": result}
        except Exception as e:
            logger.error(f"Error parsing classification: {str(e)}")
            return {"type": "unknown", "should_retry": True, "reasoning": "Parsing failed"}

class SmartRetryHandler(BaseErrorHandler):
    """Enhanced retry handler with LLM-based error classification."""
    
    def __init__(self, *args, model_name: str = "gpt-3.5-turbo", **kwargs):
        """Initialize the smart retry handler."""
        super().__init__(*args, **kwargs)
        self.error_classifier = LLMErrorClassifier(model_name=model_name)
        
    async def with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with smart retry logic."""
        context = {
            "function": func.__name__,
            "args": str(args),
            "kwargs": str(kwargs),
            "attempt": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                context["attempt"] = attempt
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                classification = await self.error_classifier.classify_error(e, context)
                
                if not classification["should_retry"]:
                    logger.warning(
                        f"Not retrying due to classification: {classification['type']}. "
                        f"Reason: {classification['reasoning']}"
                    )
                    raise
                    
                if classification["type"] == "rate_limit":
                    # Use LiteLLM's built-in rate limit handling
                    try:
                        return await completion_with_retries(
                            func,
                            *args,
                            **kwargs,
                            max_retries=self.retry_config.max_retries,
                            initial_delay=self.retry_config.initial_delay
                        )
                    except Exception as retry_error:
                        logger.error(f"Rate limit retry failed: {str(retry_error)}")
                        raise
                else:
                    delay = self._get_retry_delay(attempt)
                    logger.info(
                        f"Retry attempt {attempt + 1}/{self.retry_config.max_retries} "
                        f"after {delay:.2f}s. Error: {str(e)}"
                    )
                    await asyncio.sleep(delay)
        
        raise Exception(f"Max retries ({self.retry_config.max_retries}) exceeded") 