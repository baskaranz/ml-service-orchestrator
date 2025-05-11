"""
Admin API routers for managing model configurations.
"""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.dependencies import get_api_key
from app.models.config_models import ModelConfig
from app.schemas.api_models import CreateModelRequest, ModelListResponse, ModelSummary
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_api_key)],
    responses={403: {"description": "Not authorized"}}
)


@router.get(
    "/models",
    response_model=ModelListResponse,
    summary="List all models",
    description="Returns a list of all configured models"
)
async def list_models(
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> ModelListResponse:
    """
    List all configured models.
    
    Args:
        model_registry: Model registry service
        
    Returns:
        List of model summaries
    """
    models = model_registry.list_models()
    
    return ModelListResponse(
        models=models,
        count=len(models)
    )


@router.get(
    "/models/{model_id}",
    response_model=ModelConfig,
    summary="Get model configuration",
    description="Returns the configuration for a specific model"
)
async def get_model(
    model_id: str,
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> ModelConfig:
    """
    Get a model configuration by ID.
    
    Args:
        model_id: Model ID
        model_registry: Model registry service
        
    Returns:
        Model configuration
    """
    try:
        return model_registry.get_model_config(model_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post(
    "/models",
    response_model=ModelConfig,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new model",
    description="Adds a new model configuration"
)
async def add_model(
    request: CreateModelRequest,
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> ModelConfig:
    """
    Add a new model configuration.
    
    Args:
        request: Create model request
        model_registry: Model registry service
        
    Returns:
        Created model configuration
    """
    if request.model.id is None:
        raise HTTPException(status_code=400, detail={"error": "Model ID must not be None"})
    try:
        return await model_registry.add_model(request.model.id, request.model)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.put(
    "/models/{model_id}",
    response_model=ModelConfig,
    summary="Update model configuration",
    description="Updates the configuration for a specific model"
)
async def update_model(
    model_id: str,
    request: CreateModelRequest,
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> ModelConfig:
    """
    Update a model configuration.
    
    Args:
        model_id: Model ID
        request: Updated model configuration
        model_registry: Model registry service
        
    Returns:
        Updated model configuration
    """
    if request.model.id != model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Model ID mismatch: {request.model.id} != {model_id}"}
        )
    try:
        return await model_registry.update_model(model_id, request.model)
    except KeyError as e:
        raise HTTPException(status_code=404, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.delete(
    "/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete model configuration",
    description="Deletes the configuration for a specific model"
)
async def delete_model(
    model_id: str,
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> None:
    """
    Delete a model configuration.
    
    Args:
        model_id: Model ID
        model_registry: Model registry service
    """
    try:
        await model_registry.delete_model(model_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post(
    "/reload",
    response_model=Dict[str, str],
    summary="Reload all configurations",
    description="Reloads all model configurations from disk"
)
async def reload_configs(
    model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> Dict[str, str]:
    """
    Reload all model configurations.
    
    Args:
        model_registry: Model registry service
        
    Returns:
        Status message
    """
    try:
        models = await model_registry.reload_configs()
        return {
            "status": "success",
            "message": f"Reloaded {len(models)} model configurations"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})