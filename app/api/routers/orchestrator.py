"""
Orchestrator router for handling model requests.
"""

import asyncio
from typing import Any, Dict, List, Optional
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.responses import Response as StarletteResponse

from app.core.exceptions import ModelRequestError, CircuitBreakerError
from app.models.config_models import ModelConfig
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.services.orchestrator import Orchestrator
from app.utils.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)
router = APIRouter(tags=["orchestrator"])

# Singleton instance of the orchestrator
_orchestrator: Optional[Orchestrator] = None
_orchestrator_lock = asyncio.Lock()

async def get_orchestrator() -> Orchestrator:
    """
    Get or create the singleton orchestrator instance with async initialization.
    
    Returns:
        Orchestrator: The singleton orchestrator instance
        
    Raises:
        HTTPException: If the orchestrator fails to initialize
    """
    global _orchestrator
    
    if _orchestrator is not None:
        return _orchestrator
        
    async with _orchestrator_lock:
        if _orchestrator is not None:  # Double-checked locking pattern
            return _orchestrator
            
        logger.info("Initializing orchestrator...")
        try:
            # Create the orchestrator instance
            _orchestrator = Orchestrator(config_path=str(settings.models_dir_path))
            
            # Get the current event loop
            try:
                loop = asyncio.get_running_loop()
                loop_running = True
            except RuntimeError:
                # No running event loop, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop_running = False
            
            try:
                # If we're in a running event loop, run startup in a new thread
                if loop_running and loop.is_running():
                    # Create a new event loop for the startup
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        await _orchestrator.startup()
                    finally:
                        # Restore the original loop
                        asyncio.set_event_loop(loop)
                        new_loop.close()
                else:
                    # Use the current event loop
                    await _orchestrator.startup()
                
                logger.info("Orchestrator initialized successfully")
                return _orchestrator
                
            except Exception as e:
                logger.error(f"Error initializing orchestrator: {str(e)}", exc_info=True)
                _orchestrator = None
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initialize orchestrator: {str(e)}"
                )
                
        except Exception as e:
            logger.error(f"Error creating orchestrator: {str(e)}", exc_info=True)
            _orchestrator = None
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create orchestrator: {str(e)}"
            )
    
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
        
        # Parse the response body
        if isinstance(response, StarletteResponse):
            response_body = json.loads(response.body)
        elif isinstance(response, tuple):
            # Handle tuple response (status_code, body, headers)
            status_code = response[0]
            response_body = response[1]
            if status_code != 200:
                raise HTTPException(status_code=status_code, detail=response_body)
            # Always return just the response body for FastAPI
            logger.debug(f"Returning response_body: {response_body}")
            return response_body
        else:
            response_body = response
        logger.debug(f"Returning response_body: {response_body}")
        return response_body
        
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
        return [model.model_dump() for model in models]
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing models: {str(e)}"
        )

@router.get(
    "/models/{model_id}/info",
    response_model=Dict[str, Any],
    summary="Get model information",
    description="Retrieve detailed information about a specific model"
)
async def get_model_info(
    model_id: str,
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific model.
    
    Args:
        model_id: Model ID
        model_registry: Model registry service
        
    Returns:
        Detailed model information
        
    Raises:
        HTTPException: If the model is not found or if there's an error
    """
    try:
        model_config = model_registry.get_model_config(model_id)
        return model_config.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting info for model '{model_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting model info: {str(e)}"
        )

@router.get(
    "/models/{model_id}/health",
    response_model=Dict[str, Any],
    summary="Get model health status",
    description="Check the health status of a specific model"
)
async def get_model_health(
    model_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Get the health status of a specific model.
    
    Args:
        model_id: Model ID
        orchestrator: Orchestrator service
        
    Returns:
        Model health status
        
    Raises:
        HTTPException: If the model is not found or if there's an error
    """
    try:
        health = await orchestrator.check_model_health(model_id)
        return {"status": "healthy" if health else "unhealthy", "model_id": model_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting health for model '{model_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting model health: {str(e)}"
        )

@router.get(
    "/metrics",
    response_model=Dict[str, Any],
    summary="Get system metrics",
    description="Retrieve system and model metrics"
)
async def get_metrics(
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Get system and model metrics.
    
    Args:
        orchestrator: Orchestrator service
        
    Returns:
        System and model metrics
    """
    try:
        return orchestrator.get_metrics()
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting metrics: {str(e)}"
        )

@router.get(
    "/discover",
    response_model=Dict[str, Any],
    summary="Discover available models",
    description="Discover and register available models"
)
async def discover_models(
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Discover and register available models.
    
    Args:
        orchestrator: Orchestrator service
        
    Returns:
        Discovery results
    """
    try:
        discovered = await orchestrator.discover_models()
        return {"status": "success", "discovered_models": discovered}
    except Exception as e:
        logger.error(f"Error discovering models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error discovering models: {str(e)}"
        )

@router.post(
    "/refresh",
    response_model=Dict[str, Any],
    summary="Refresh model configurations",
    description="Reload model configurations from disk"
)
async def refresh_models(
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Refresh model configurations by reloading from disk.
    
    Args:
        orchestrator: Orchestrator service
        
    Returns:
        Refresh status
    """
    try:
        await orchestrator.refresh_models()
        return {"status": "success", "message": "Model configurations refreshed successfully"}
    except Exception as e:
        logger.error(f"Error refreshing models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error refreshing models: {str(e)}"
        )

@router.get(
    "/stats",
    response_model=Dict[str, Any],
    summary="Get system statistics",
    description="Retrieve system and model statistics"
)
async def get_system_stats(
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Get system and model statistics.
    
    Args:
        orchestrator: Orchestrator service
        
    Returns:
        System and model statistics
    """
    try:
        return orchestrator.get_system_stats()
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting system stats: {str(e)}"
        )

@router.get(
    "/models/{model_id}/config",
    response_model=Dict[str, Any],
    summary="Get model configuration",
    description="Retrieve the configuration for a specific model"
)
async def get_model_config(
    model_id: str,
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> Dict[str, Any]:
    """
    Get the configuration for a specific model.
    
    Args:
        model_id: Model ID
        model_registry: Model registry service
        
    Returns:
        Model configuration
        
    Raises:
        HTTPException: If the model is not found or if there's an error
    """
    try:
        model_config = model_registry.get_model_config(model_id)
        return model_config.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting config for model '{model_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting model config: {str(e)}"
        )