"""
ML Orchestrator Request/Response Transformation Pattern

This example demonstrates the transformation patterns used in the ML Orchestrator
for standardizing and adapting requests and responses between different formats.
"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

# --- Data Models ---

class ModelInputFormat(str, Enum):
    """Supported input formats for model requests."""
    JSON = "json"
    TENSOR = "tensor"
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"


class ModelOutputFormat(str, Enum):
    """Supported output formats for model responses."""
    JSON = "json"
    TENSOR = "tensor"
    TEXT = "text"
    EMBEDDINGS = "embeddings"
    PROBABILITIES = "probabilities"


class TransformConfig(BaseModel):
    """Configuration for request/response transformations."""
    input_format: ModelInputFormat = Field(..., description="Expected input format for the model")
    output_format: ModelOutputFormat = Field(..., description="Output format produced by the model")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="JSON Schema for input validation")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="JSON Schema for output validation")
    preprocess_config: Optional[Dict[str, Any]] = Field(None, description="Configuration for preprocessing")
    postprocess_config: Optional[Dict[str, Any]] = Field(None, description="Configuration for postprocessing")


class StandardModelRequest(BaseModel):
    """Standard request format for ML Orchestrator API."""
    inputs: Any = Field(..., description="Model inputs")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters for model inference")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class StandardModelResponse(BaseModel):
    """Standard response format for ML Orchestrator API."""
    outputs: Any = Field(..., description="Model outputs")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")


# --- Transformation Interfaces ---

class RequestTransformer(ABC):
    """Base class for request transformers."""
    
    @abstractmethod
    async def transform(self, request: StandardModelRequest) -> Any:
        """
        Transform a standard request to model-specific format.
        
        Args:
            request: Standard ML Orchestrator request
            
        Returns:
            Transformed request in model-specific format
        """
        pass


class ResponseTransformer(ABC):
    """Base class for response transformers."""
    
    @abstractmethod
    async def transform(self, response: Any) -> StandardModelResponse:
        """
        Transform a model-specific response to standard format.
        
        Args:
            response: Model-specific response
            
        Returns:
            Transformed response in standard format
        """
        pass


# --- JSON Transformers ---

class JsonRequestTransformer(RequestTransformer):
    """Request transformer for JSON format."""
    
    def __init__(self, transform_config: TransformConfig):
        """
        Initialize the transformer.
        
        Args:
            transform_config: Configuration for the transformation
        """
        self.config = transform_config
    
    async def transform(self, request: StandardModelRequest) -> Dict[str, Any]:
        """
        Transform a standard request to JSON format.
        
        Args:
            request: Standard ML Orchestrator request
            
        Returns:
            Dict in the format expected by the model
        """
        # Start with the inputs
        transformed = request.inputs
        
        # Apply preprocessing if configured
        if self.config.preprocess_config:
            # Apply preprocessing steps based on configuration
            if "flatten" in self.config.preprocess_config and self.config.preprocess_config["flatten"]:
                transformed = self._flatten_json(transformed)
                
            if "add_parameters" in self.config.preprocess_config and self.config.preprocess_config["add_parameters"]:
                # Add parameters to the request if specified
                if request.parameters:
                    if isinstance(transformed, dict):
                        transformed.update(request.parameters)
                    else:
                        # If inputs is not a dict, wrap it
                        transformed = {
                            "data": transformed,
                            **request.parameters
                        }
        
        # Return the transformed request
        return transformed
    
    def _flatten_json(self, data: Any) -> Dict[str, Any]:
        """
        Flatten nested JSON into a single level dictionary.
        
        Args:
            data: Nested JSON data
            
        Returns:
            Flattened dictionary
        """
        result = {}
        
        def _flatten(x: Any, name: str = ""):
            if isinstance(x, dict):
                for k, v in x.items():
                    _flatten(v, f"{name}.{k}" if name else k)
            elif isinstance(x, list):
                for i, v in enumerate(x):
                    _flatten(v, f"{name}[{i}]")
            else:
                result[name] = x
                
        _flatten(data)
        return result


class JsonResponseTransformer(ResponseTransformer):
    """Response transformer for JSON format."""
    
    def __init__(self, transform_config: TransformConfig):
        """
        Initialize the transformer.
        
        Args:
            transform_config: Configuration for the transformation
        """
        self.config = transform_config
    
    async def transform(self, response: Any) -> StandardModelResponse:
        """
        Transform a JSON response to standard format.
        
        Args:
            response: JSON response from model
            
        Returns:
            Standardized response
        """
        # Basic validation
        if response is None:
            return StandardModelResponse(
                outputs=None,
                metadata={"error": "Model returned null response"}
            )
        
        # Apply postprocessing if configured
        outputs = response
        if self.config.postprocess_config:
            # Apply postprocessing steps based on configuration
            if "extract_key" in self.config.postprocess_config:
                key = self.config.postprocess_config["extract_key"]
                if isinstance(response, dict) and key in response:
                    outputs = response[key]
                else:
                    logger.warning(f"Could not extract key '{key}' from response")
            
            if "format" in self.config.postprocess_config:
                format_type = self.config.postprocess_config["format"]
                if format_type == "probabilities" and isinstance(outputs, list):
                    # Ensure probabilities sum to 1.0
                    total = sum(outputs)
                    if total > 0:
                        outputs = [p / total for p in outputs]
        
        # Collect metadata if available
        metadata = {}
        if isinstance(response, dict):
            # Extract metadata from response
            for meta_key in ["model_version", "timing", "model_id"]:
                if meta_key in response:
                    metadata[meta_key] = response[meta_key]
        
        # Build standard response
        return StandardModelResponse(
            outputs=outputs,
            metadata=metadata
        )


# --- Tensor Transformers ---

class TensorRequestTransformer(RequestTransformer):
    """Request transformer for tensor format."""
    
    def __init__(self, transform_config: TransformConfig):
        """
        Initialize the transformer.
        
        Args:
            transform_config: Configuration for the transformation
        """
        self.config = transform_config
    
    async def transform(self, request: StandardModelRequest) -> Dict[str, Any]:
        """
        Transform a standard request to tensor format.
        
        Args:
            request: Standard ML Orchestrator request
            
        Returns:
            Dict with inputs in tensor format
        """
        # For a real implementation, this would convert to specific tensor format
        # like numpy arrays, TensorFlow tensors, PyTorch tensors, etc.
        # For this example, we'll use a simple list-based representation
        
        inputs = request.inputs
        parameters = request.parameters or {}
        
        # Example transformation for text to token IDs
        if self.config.input_format == ModelInputFormat.TEXT:
            # In a real implementation, this would use a tokenizer
            if isinstance(inputs, str):
                # Simulate tokenization
                tokens = inputs.split()
                # Convert to integers (this is just a simulation)
                token_ids = [hash(token) % 50000 for token in tokens]
                
                transformed = {
                    "input_ids": token_ids,
                    "attention_mask": [1] * len(token_ids)
                }
            elif isinstance(inputs, list) and all(isinstance(x, str) for x in inputs):
                # Batch of strings
                batch_token_ids = []
                batch_attention_masks = []
                
                for text in inputs:
                    tokens = text.split()
                    token_ids = [hash(token) % 50000 for token in tokens]
                    batch_token_ids.append(token_ids)
                    batch_attention_masks.append([1] * len(token_ids))
                
                # In a real implementation, we would pad sequences to same length
                transformed = {
                    "input_ids": batch_token_ids,
                    "attention_mask": batch_attention_masks
                }
            else:
                raise ValueError(f"Expected string or list of strings, got {type(inputs)}")
        
        # Example transformation for JSON to tensors
        elif self.config.input_format == ModelInputFormat.JSON:
            if not isinstance(inputs, dict):
                raise ValueError(f"Expected dict for JSON input format, got {type(inputs)}")
            
            # Convert each value to a tensor-like format if needed
            transformed = {}
            for key, value in inputs.items():
                if isinstance(value, list):
                    # Keep lists as is (would be converted to tensors in real impl)
                    transformed[key] = value
                elif isinstance(value, (int, float)):
                    # Wrap scalars in lists
                    transformed[key] = [value]
                else:
                    # Convert other types to strings and encode
                    transformed[key] = str(value)
        
        else:
            # For other formats, keep as is
            transformed = inputs
        
        # Add any required parameters
        result = {"inputs": transformed}
        if parameters:
            result["parameters"] = parameters
        
        return result


class TensorResponseTransformer(ResponseTransformer):
    """Response transformer for tensor format."""
    
    def __init__(self, transform_config: TransformConfig):
        """
        Initialize the transformer.
        
        Args:
            transform_config: Configuration for the transformation
        """
        self.config = transform_config
    
    async def transform(self, response: Any) -> StandardModelResponse:
        """
        Transform a tensor response to standard format.
        
        Args:
            response: Tensor response from model
            
        Returns:
            Standardized response
        """
        # For a real implementation, this would convert from specific tensor format
        
        # Extract outputs based on output format
        if self.config.output_format == ModelOutputFormat.PROBABILITIES:
            # Convert raw logits to probabilities
            if isinstance(response, dict) and "logits" in response:
                import math
                logits = response["logits"]
                
                # Apply softmax
                if isinstance(logits[0], list):
                    # Batch of logits
                    outputs = []
                    for batch_logits in logits:
                        exp_logits = [math.exp(x) for x in batch_logits]
                        sum_exp = sum(exp_logits)
                        probs = [x / sum_exp for x in exp_logits]
                        outputs.append(probs)
                else:
                    # Single set of logits
                    exp_logits = [math.exp(x) for x in logits]
                    sum_exp = sum(exp_logits)
                    outputs = [x / sum_exp for x in exp_logits]
            else:
                outputs = response
                
        elif self.config.output_format == ModelOutputFormat.EMBEDDINGS:
            # Extract embeddings
            if isinstance(response, dict):
                outputs = response.get("embeddings", response.get("last_hidden_state", response))
            else:
                outputs = response
                
        elif self.config.output_format == ModelOutputFormat.TEXT:
            # Extract text output
            if isinstance(response, dict) and "predictions" in response:
                outputs = response["predictions"]
            else:
                outputs = response
                
        else:
            # For other formats, keep as is
            outputs = response
        
        # Collect metadata if available
        metadata = {}
        if isinstance(response, dict):
            for meta_key in ["model_name", "model_version", "timing"]:
                if meta_key in response:
                    metadata[meta_key] = response[meta_key]
        
        return StandardModelResponse(
            outputs=outputs,
            metadata=metadata
        )


# --- Factory for Creating Transformers ---

class TransformerFactory:
    """Factory for creating request and response transformers."""
    
    @staticmethod
    def create_request_transformer(
        transform_config: TransformConfig
    ) -> RequestTransformer:
        """
        Create a request transformer based on configuration.
        
        Args:
            transform_config: Configuration for the transformation
            
        Returns:
            Appropriate request transformer
            
        Raises:
            ValueError: If no transformer is available for the format
        """
        if transform_config.input_format == ModelInputFormat.JSON:
            return JsonRequestTransformer(transform_config)
        elif transform_config.input_format in [ModelInputFormat.TENSOR, ModelInputFormat.TEXT]:
            return TensorRequestTransformer(transform_config)
        else:
            raise ValueError(f"No request transformer available for {transform_config.input_format}")
    
    @staticmethod
    def create_response_transformer(
        transform_config: TransformConfig
    ) -> ResponseTransformer:
        """
        Create a response transformer based on configuration.
        
        Args:
            transform_config: Configuration for the transformation
            
        Returns:
            Appropriate response transformer
            
        Raises:
            ValueError: If no transformer is available for the format
        """
        if transform_config.output_format == ModelOutputFormat.JSON:
            return JsonResponseTransformer(transform_config)
        elif transform_config.output_format in [ModelOutputFormat.TENSOR, ModelOutputFormat.EMBEDDINGS, 
                                               ModelOutputFormat.PROBABILITIES, ModelOutputFormat.TEXT]:
            return TensorResponseTransformer(transform_config)
        else:
            raise ValueError(f"No response transformer available for {transform_config.output_format}")


# --- Transformation Pipeline ---

class TransformationPipeline:
    """
    Pipeline for transforming requests and responses.
    
    This class handles the full request/response transformation cycle.
    """
    
    def __init__(self, transform_config: TransformConfig):
        """
        Initialize the pipeline.
        
        Args:
            transform_config: Configuration for transformations
        """
        self.config = transform_config
        self.request_transformer = TransformerFactory.create_request_transformer(transform_config)
        self.response_transformer = TransformerFactory.create_response_transformer(transform_config)
    
    async def transform_request(self, request: StandardModelRequest) -> Any:
        """
        Transform a standard request to model-specific format.
        
        Args:
            request: Standard ML Orchestrator request
            
        Returns:
            Transformed request in model-specific format
        """
        try:
            transformed = await self.request_transformer.transform(request)
            return transformed
        except Exception as e:
            logger.error(f"Error transforming request: {str(e)}", exc_info=True)
            raise ValueError(f"Request transformation failed: {str(e)}")
    
    async def transform_response(self, response: Any) -> StandardModelResponse:
        """
        Transform a model-specific response to standard format.
        
        Args:
            response: Model-specific response
            
        Returns:
            Transformed response in standard format
        """
        try:
            transformed = await self.response_transformer.transform(response)
            return transformed
        except Exception as e:
            logger.error(f"Error transforming response: {str(e)}", exc_info=True)
            # Return error response instead of raising
            return StandardModelResponse(
                outputs=None,
                metadata={"error": f"Response transformation failed: {str(e)}"}
            )


# --- Usage in FastAPI Endpoint ---

async def process_model_request(
    model_id: str,
    request: StandardModelRequest,
    transform_config: TransformConfig
) -> StandardModelResponse:
    """
    Process a model request with transformations.
    
    Args:
        model_id: ID of the model to use
        request: Standard request
        transform_config: Configuration for transformations
        
    Returns:
        Standard response
    """
    # Create transformation pipeline
    pipeline = TransformationPipeline(transform_config)
    
    # Transform request
    transformed_request = await pipeline.transform_request(request)
    
    # Call model (simulated here)
    # In a real implementation, this would call an actual model service
    await asyncio.sleep(0.1)  # Simulate model inference time
    model_response = {
        "predictions": [0.2, 0.7, 0.1],
        "model_version": "1.0.0",
        "timing": {
            "preprocessing_ms": 5,
            "inference_ms": 95,
            "total_ms": 100
        }
    }
    
    # Transform response
    standard_response = await pipeline.transform_response(model_response)
    
    return standard_response


"""
# Example FastAPI endpoint
from fastapi import APIRouter, Depends, FastAPI

app = FastAPI()
router = APIRouter()

# Get transform config from model registry
async def get_transform_config(model_id: str) -> TransformConfig:
    # In a real implementation, this would get the config from a registry or database
    return TransformConfig(
        input_format=ModelInputFormat.JSON,
        output_format=ModelOutputFormat.PROBABILITIES,
        preprocess_config={"add_parameters": True},
        postprocess_config={"extract_key": "predictions"}
    )

@router.post("/models/{model_id}/predict")
async def predict(
    model_id: str,
    request: StandardModelRequest,
    transform_config: TransformConfig = Depends(get_transform_config)
):
    response = await process_model_request(model_id, request, transform_config)
    return response

app.include_router(router, prefix="/api")
"""