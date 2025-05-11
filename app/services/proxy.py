"""
Proxy service for forwarding requests to model endpoints.
"""

from typing import Any, Dict, Optional

from fastapi import Depends, Request, Response

from app.core.exceptions import ModelRequestError
from app.models.config_models import ModelConfig
from app.core.orchestrator import Orchestrator
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.utils.logging import get_logger
from app.utils.http import HTTPClient

logger = get_logger(__name__)


class ProxyService:
    """
    Service for proxying requests to model endpoints.
    """
    
    def __init__(
        self,
        model_registry: ModelRegistryService,
        orchestrator: Orchestrator
    ):
        """
        Initialize the proxy service.
        
        Args:
            model_registry: Model registry service
            orchestrator: Orchestrator for request routing
        """
        self.model_registry = model_registry
        self.orchestrator = orchestrator
    
    async def proxy_to_model(
        self,
        model_id: str,
        request: Request,
        path_suffix: str = ""
    ) -> Response:
        """
        Proxy a request to a model endpoint.
        
        Args:
            model_id: Model ID
            request: Original FastAPI request
            path_suffix: Additional path to append to the model endpoint URL
            
        Returns:
            Response from the model endpoint
        """
        logger.info(
            f"Proxying request to model: {model_id}",
            extra={"path": request.url.path, "method": request.method}
        )
        
        try:
            # Get the model configuration
            model_config = self.model_registry.get_model_config(model_id)
            
            # Proxy the request through the orchestrator
            response = await self.orchestrator.proxy_request(
                model_config=model_config,
                request=request,
                path_suffix=path_suffix
            )
            
            return response
            
        except ModelRequestError:
            # Re-raise to use the proper exception handler
            raise
            
        except Exception as e:
            logger.error(f"Error proxying request to model '{model_id}': {str(e)}", exc_info=True)
            raise ModelRequestError(
                message=f"Error proxying request: {str(e)}",
                status_code=500,
                model_id=model_id
            )


def get_proxy_service(
    model_registry: ModelRegistryService = Depends(get_model_registry_service),
    orchestrator: Orchestrator = Depends(lambda: Orchestrator())
) -> ProxyService:
    """
    Dependency for getting the proxy service.
    
    Args:
        model_registry: Model registry service
        orchestrator: Orchestrator instance
        
    Returns:
        Proxy service
    """
    return ProxyService(model_registry, orchestrator)