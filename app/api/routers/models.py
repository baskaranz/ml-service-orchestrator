import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies.model_registry import get_model_registry
from app.api.dependencies.orchestrator import get_orchestrator_async as get_orchestrator
from app.core.config_loader import model_config_loader
from app.schemas.models import ModelConfig, ModelConfigList
from app.services.errors import ModelRequestError
from app.services.model_registry import ModelRegistryService

router = APIRouter(tags=["models"])
logger = logging.getLogger(__name__)


@router.get("/configs", response_model=ModelConfigList)
async def list_model_configs() -> Dict[str, Any]:
    """
    List all available model configurations.

    Returns:
        Dictionary containing list of model configurations.
    """
    try:
        configs = model_config_loader.get_all_configs()
        return {"models": list(configs.values())}
    except Exception as e:
        logger.error(f"Error listing model configs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model configurations",
        )


@router.get("/configs/{model_id}", response_model=ModelConfig)
async def get_model_config(model_id: str) -> Dict[str, Any]:
    """
    Get configuration for a specific model.

    Args:
        model_id: The ID of the model to get configuration for.

    Returns:
        Model configuration.

    Raises:
        HTTPException: If model configuration is not found.
    """
    try:
        return model_config_loader.get_config(model_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config for model {model_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration for model {model_id}",
        )


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
        logger.info(f"Received prediction request for model: {model_id}")

        # Get model config from the config loader
        try:
            model_config = model_config_loader.get_config(model_id)
            logger.info(f"Retrieved model config for {model_id}")
        except HTTPException as e:
            logger.error(f"Model {model_id} not found in configurations: {str(e)}")
            raise

        # Get the orchestrator instance asynchronously
        logger.debug("Getting orchestrator instance")
        orchestrator = await get_orchestrator()
        logger.debug("Successfully retrieved orchestrator instance")

        # Log request details
        logger.debug(f"Request method: {request.method}")
        logger.debug(f"Request headers: {dict(request.headers)}")

        try:
            request_json = await request.json()
            logger.debug(f"Request JSON: {request_json}")
        except Exception as json_err:
            logger.warning(f"Could not parse request as JSON: {json_err}")

        # Make prediction
        logger.info(f"Forwarding request to model {model_id} at {model_config.endpoint_url}")
        try:
            response = await orchestrator.proxy_request(
                model_config=model_config,
                request=request,
                path_suffix="",  # Remove the path suffix as it's already included in the model config
            )
            logger.debug(f"Received response from model {model_id}: {response}")
        except Exception as proxy_err:
            logger.error(
                f"Error in proxy_request for model {model_id}: {str(proxy_err)}", exc_info=True
            )
            raise

        # The response from proxy_request is a dictionary with status_code, content, and headers
        response_data = response.get("content", {})
        logger.debug(f"Response data: {response_data}")

        # Add model name to metadata if response_data is a dictionary
        if isinstance(response_data, dict):
            if "metadata" not in response_data:
                response_data["metadata"] = {}
            response_data["metadata"]["model_name"] = model_id
        else:
            logger.warning(f"Unexpected response_data type: {type(response_data)}")

        logger.info(f"Successfully processed prediction request for model {model_id}")
        return response_data

    except HTTPException as http_exc:
        logger.error(f"HTTPException in predict endpoint: {str(http_exc)}", exc_info=True)
        raise
    except ModelRequestError as e:
        logger.error(f"Model request error in predict endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=e.status_code or 400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in predict endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
