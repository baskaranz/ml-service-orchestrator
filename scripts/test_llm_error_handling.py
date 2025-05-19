"""
Test script for LLM error handling scenarios.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from app.models.config_models import LLMProviderConfig, ModelConfig, CircuitBreakerConfig
from app.utils.error_handling.llm_errors import LLMErrorClassifier, SmartRetryHandler
from app.utils.error_handling.base import RetryConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Mock configurations
test_llm_config = LLMProviderConfig(
    type="huggingface",
    model_name="mistralai/Mistral-7B-Instruct-v0.2",
    timeout=30,
    max_retries=3,
    api_key="test-key"
)

test_model_config = ModelConfig(
    id="test-model",
    name="Test Model",
    description="A test model for error handling",
    version="1.0.0",
    endpoint_url="http://localhost:8000/test",
    active=True,
    timeout=30.0,
    max_retries=3,
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        reset_timeout=30.0
    ),
    llm_provider=test_llm_config
)

class MockLLMProvider:
    """Mock LLM provider that simulates various error responses."""
    
    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self._call_count = 0
    
    async def generate(self, prompt: str) -> str:
        """Simulate LLM response with different error scenarios."""
        self._call_count += 1
        
        if self._call_count == 1:
            return "Classification: rate_limit\nReasoning: Too many requests"
        elif self._call_count == 2:
            return "Classification: transient\nReasoning: Network timeout"
        elif self._call_count == 3:
            return "Classification: permanent\nReasoning: Invalid input format"
        else:
            return "Classification: success\nReasoning: Operation successful"

class MockErrorClassifier(LLMErrorClassifier):
    """Mock error classifier that simulates error classification."""
    
    def __init__(self, llm: MockLLMProvider):
        super().__init__(config=None)
        self.llm = llm
    
    async def classify_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Classify error based on mock LLM response."""
        response = await self.llm.generate("")
        lines = response.strip().split("\n")
        classification = lines[0].split(":", 1)[1].strip()
        reasoning = lines[1].split(":", 1)[1].strip()
        
        return {
            "classification": classification,
            "reasoning": reasoning,
            "timestamp": "2024-03-21T00:00:00Z"
        }

# Initialize mock components
mock_llm = MockLLMProvider(test_llm_config)
error_classifier = MockErrorClassifier(mock_llm)
error_handler = SmartRetryHandler(
    retry_config=RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=10.0
    ),
    llm_config=test_llm_config
)
error_handler.error_classifier = error_classifier

@app.get("/test-llm")
async def test_llm_error_handling():
    """Test endpoint for LLM error handling."""
    async def mock_operation():
        """Simulate an operation that might fail."""
        llm = error_handler.error_classifier.llm
        if not isinstance(llm, MockLLMProvider):
            raise ValueError("Invalid LLM provider type")
        await llm.generate("")  # increment call count
        if llm._call_count >= 4:
            return "Success"
        raise Exception(f"Simulated error {llm._call_count - 1}")
    
    try:
        result = await error_handler.with_retry(mock_operation)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_llm_tests():
    """Run various tests for LLM error handling."""
    test_cases = [
        "Rate limit error",
        "Transient error",
        "Permanent error",
        "Successful response"
    ]
    
    for test_case in test_cases:
        logger.info(f"\nRunning test: {test_case}")
        try:
            response = await test_llm_error_handling()
            logger.info(f"Test passed: {response}")
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
    
    logger.info("\nAll tests completed")

if __name__ == "__main__":
    asyncio.run(run_llm_tests()) 