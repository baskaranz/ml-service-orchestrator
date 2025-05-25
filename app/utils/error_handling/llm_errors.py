"""
LLM-based error handling utilities.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

from app.config.platform_config import platform_config
from app.models.config_models import LLMProviderConfig
from app.utils.error_handling.base import BaseErrorHandler, RetryConfig
from app.utils.llm_providers import get_llm_provider
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LLMErrorClassifier:
    """Classifies errors using LLM to determine retry strategy."""

    def __init__(self, config: Optional[LLMProviderConfig] = None):
        """Initialize the error classifier."""
        if config is None:
            config = platform_config.llm_config or LLMProviderConfig(
                type="huggingface",
                model_name="mistralai/Mistral-7B-Instruct-v0.2",
                timeout=30,
                max_retries=3,
                api_key="test-key",  # Default test key for development
            )

        self.llm = get_llm_provider(config)
        self.prompt_template = """
        Analyze this error and classify it:
        Error Type: {error_type}
        Error Message: {error_message}
        Context: {context}

        Classify this error as one of:
        1. Transient (should retry) - Temporary issues like network timeouts, server overload
        2. Permanent (should not retry) - Issues that won't be resolved by retrying
        3. Rate Limit (should retry with backoff) - API rate limits or quota exceeded
        4. Authentication (should not retry) - Invalid credentials or permissions
        5. Input Validation (should not retry) - Invalid input data or parameters

        Provide your classification and reasoning in this format:
        Classification: <one of the above categories>
        Reasoning: <explanation for the classification>
        """

    async def classify_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Classify an error using LLM."""
        try:
            # Extract error details
            error_type = type(error).__name__
            error_message = str(error)

            # Build context
            error_context = {
                "error_type": error_type,
                "error_message": error_message,
                "status_code": getattr(error, "status_code", None),
                "model_id": context.get("model_id") if context else None,
                "retry_count": context.get("retry_count", 0) if context else 0,
                "max_retries": context.get("max_retries", 3) if context else 3,
            }

            # Add any additional context
            if context:
                error_context.update(context)

            prompt = self.prompt_template.format(
                error_type=error_type,
                error_message=error_message,
                context=json.dumps(error_context, indent=2),
            )

            logger.info(f"Classifying error with prompt:\n{prompt}")

            response = await self.llm.generate(prompt)
            logger.info(f"LLM response:\n{response}")

            # Parse the response to extract classification and reasoning
            lines = response.strip().split("\n")
            classification = None
            reasoning = []

            for line in lines:
                if line.startswith("Classification:"):
                    classification = line.split(":", 1)[1].strip().lower()
                elif line.startswith("Reasoning:"):
                    reasoning.append(line.split(":", 1)[1].strip())

            if not classification:
                raise ValueError("Could not parse classification from LLM response")

            # Normalize classification
            classification = classification.lower()
            if "transient" in classification:
                classification = "transient"
            elif "permanent" in classification:
                classification = "permanent"
            elif "rate limit" in classification:
                classification = "rate_limit"
            elif "auth" in classification:
                classification = "authentication"
            elif "input" in classification or "validation" in classification:
                classification = "input_validation"
            else:
                classification = "unknown"

            result = {
                "classification": classification,
                "reasoning": "\n".join(reasoning) if reasoning else None,
                "timestamp": datetime.utcnow().isoformat(),
                "context": error_context,
            }

            logger.info(f"Error classification result: {json.dumps(result, indent=2)}")
            return result

        except Exception as e:
            logger.error(f"Error in LLM classification: {str(e)}")
            return {
                "classification": "unknown",
                "reasoning": f"Error in classification: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "context": context or {},
            }


class SmartRetryHandler(BaseErrorHandler):
    """Smart retry handler that uses LLM for error classification."""

    def __init__(self, retry_config: RetryConfig, llm_config: Optional[LLMProviderConfig] = None):
        """Initialize the smart retry handler."""
        super().__init__(retry_config)
        self.error_classifier = LLMErrorClassifier(llm_config)

    async def should_retry(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Determine if an error should be retried using LLM classification."""
        # Check if max retries reached
        if self.retry_count >= self.retry_config.max_retries:
            logger.info(f"Max retries ({self.retry_config.max_retries}) reached, not retrying")
            return False

        classification = await self.error_classifier.classify_error(error, context)

        if classification["classification"] == "transient":
            self.increment_retry_count()
            return True
        elif classification["classification"] == "rate_limit":
            # Add exponential backoff for rate limits
            delay = self._get_retry_delay()
            logger.info(f"Rate limit detected, waiting {delay:.2f}s before retry")
            await asyncio.sleep(delay)
            self.increment_retry_count()
            return True
        else:
            logger.info(
                f"Not retrying error: {classification['classification']}\n"
                f"Reasoning: {classification['reasoning']}"
            )
            return False
