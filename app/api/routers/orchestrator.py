"""
Orchestrator router for handling model requests.
"""

from typing import Any, Dict, List
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.exceptions import ModelRequestError, CircuitBreakerError
from app.models.config_models import ModelConfig
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.services.orchestrator import Orchestrator
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["orchestrator"])

# Create a singleton instance of the orchestrator
_orchestrator = Orchestrator()

def get_orchestrator() -> Orchestrator:
    """Get the orchestrator instance."""
    return _orchestrator

@router.post(
    "/models/{model_id}",
    response_model=Dict[str, Any],
    summary="Forward request to model",
    description="Forwards a request to the specified model endpoint"
)
async def forward_request(
    model_id: str,
    request: Request,
    response: Response,
    model_registry: ModelRegistryService = Depends(get_model_registry_service),
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Response:
    """
    Forward a request to a model.
    
    Args:
        model_id: Model ID
        request: Original FastAPI request
        response: FastAPI response object
        model_registry: Model registry service
        orchestrator: Orchestrator service
        
    Returns:
        Model response
        
    Raises:
        HTTPException: If the request fails
    """
    logger.debug(f"forward_request called for model {model_id}")
    try:
        # Get the model configuration
        model_config = model_registry.get_model_config(model_id)
        logger.debug(f"Retrieved model config for {model_id}: {model_config}")
        
        # Forward the request
        response = await orchestrator.proxy_request(
            model_config=model_config,
            request=request,
            path_suffix="/predict"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Error forwarding request to model '{model_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error forwarding request: {str(e)}"
        )

@router.get(
    "/models/{model_id}/stats",
    response_model=Dict[str, Any],
    summary="Get model statistics",
    description="Get statistics and error handling information for a specific model"
)
async def get_model_stats(
    model_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Get statistics for a specific model.
    
    Args:
        model_id: Model ID
        orchestrator: Orchestrator service
        
    Returns:
        Model statistics
        
    Raises:
        HTTPException: If the model is not found or if there's an error
    """
    try:
        return orchestrator.get_model_stats(model_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting stats for model '{model_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting model stats: {str(e)}"
        )

@router.get(
    "/models",
    response_model=List[Dict[str, Any]],
    summary="List registered models",
    description="Retrieve a list of all registered models"
)
async def list_models(
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> List[Dict[str, Any]]:
    """
    List all registered models.
    
    Args:
        model_registry: Model registry service
        
    Returns:
        List of registered models
        
    Raises:
        HTTPException: If there's an error retrieving the models
    """
    try:
        models = model_registry.list_models()
        return [model.dict() for model in models]
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing models: {str(e)}"
        )