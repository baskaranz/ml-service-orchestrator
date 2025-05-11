"""
Orchestrator router for model requests.
"""

import json
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import Response

from app.models.config_models import ModelConfig
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.services.orchestrator import Orchestrator
from app.services.proxy import ProxyService
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/models",
    tags=["models"],
    responses={404: {"description": "Model not found"}}
)

def get_orchestrator(
    proxy_service: ProxyService = Depends(lambda: ProxyService())
) -> Orchestrator:
    """
    Dependency for getting the orchestrator service.
    
    Args:
        proxy_service: Proxy service
        
    Returns:
        Orchestrator service
    """
    return Orchestrator()

@router.post(
    "/{model_id}",
    response_model=Dict[str, Any],
    summary="Forward request to model",
    description="Forwards a request to the specified model endpoint"
)
async def forward_request(
    model_id: str,
    request: Request,
    model_registry: ModelRegistryService = Depends(get_model_registry_service),
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Forward a request to a model.
    
    Args:
        model_id: Model ID
        request: Original FastAPI request
        model_registry: Model registry service
        orchestrator: Orchestrator service
        
    Returns:
        Model response
        
    Raises:
        HTTPException: If the request fails
    """
    logger.info(
        f"Forwarding request to model: {model_id}",
        extra={"path": request.url.path, "method": request.method}
    )
    
    try:
        # Get the model configuration
        model_config = model_registry.get_model_config(model_id)
        
        # Forward the request
        response = await orchestrator.proxy_request(
            model_config=model_config,
            request=request,
            path_suffix="/predict"
        )
        
        # Parse and return the response
        return json.loads(response.body)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Error forwarding request to model '{model_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error forwarding request: {str(e)}"
        )