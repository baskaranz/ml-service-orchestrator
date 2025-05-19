from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from app.services.model_registry import ModelRegistryService
from app.services.orchestrator import Orchestrator
from app.services.errors import ModelRequestError
from app.api.dependencies.model_registry import get_model_registry
from app.api.dependencies.orchestrator import get_orchestrator_async as get_orchestrator
from typing import Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/{model_id}")
async def predict(
    model_id: str,
    request: Request,
    model_registry: ModelRegistryService = Depends(get_model_registry),
):
    """
    Make a prediction using the specified model.
    
    Args:
        model_id: The ID of the model to use for prediction
        request: The incoming request object
        model_registry: The model registry service
        
    Returns:
        The prediction result from the model
        
    Raises:
        HTTPException: If there's an error processing the request
    """
    try:
        # Get model config
        model_config = model_registry.get_model_config(model_id)
        if not model_config:
            raise HTTPException(
                status_code=404,
                detail=f"Model {model_id} not found"
            )

        # Get request data
        request_data = await request.json()
        
        # Get the orchestrator instance asynchronously
        orchestrator = await get_orchestrator()

        # Make prediction
        response = await orchestrator.proxy_request(
            model_config=model_config,
            request=request,
            path_suffix=""  # Remove the path suffix as it's already included in the model config
        )

        # Add model name to metadata
        response_data = response.body
        if isinstance(response_data, dict):
            if "metadata" not in response_data:
                response_data["metadata"] = {}
            response_data["metadata"]["model_name"] = model_id

        return response_data

    except ModelRequestError as e:
        logger.error(f"Model request error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=e.status_code or 400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in predict endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        ) 