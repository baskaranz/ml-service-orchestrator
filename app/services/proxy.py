"""
Proxy service for forwarding requests to model endpoints.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, Response, Depends
from httpx import Response
import json
from starlette.responses import Response as StarletteResponse

from app.models.config_models import ModelConfig
from app.utils.http import HttpClient
from app.utils.logging import get_logger
from app.core.exceptions import ModelRequestError, CircuitBreakerError
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.services.orchestrator import Orchestrator

logger = get_logger(__name__)

class ProxyService:
    """
    Service for proxying requests to model endpoints.
    
    This class is responsible for:
    1. Managing HTTP clients for each model
    2. Forwarding requests to model endpoints
    3. Handling authentication and headers
    """
    
    def __init__(
        self,
        model_registry: Optional[ModelRegistryService] = None,
        orchestrator: Optional[Orchestrator] = None
    ):
        """Initialize the proxy service."""
        self.model_registry = model_registry or get_model_registry_service()
        self.orchestrator = orchestrator or Orchestrator()
        self._clients: Dict[str, HttpClient] = {}
    
    def _get_client(self, model_config: ModelConfig) -> HttpClient:
        """
        Get or create an HTTP client for a model.
        
        Args:
            model_config: Model configuration
            
        Returns:
            HTTP client instance
        """
        if model_config.id not in self._clients:
            client = HttpClient(
                timeout=model_config.timeout,
                max_retries=model_config.max_retries
            )
            self._clients[model_config.id] = client
            
        return self._clients[model_config.id]
    
    async def forward_request(
        self,
        model_config: ModelConfig,
        request_data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Forward a request to a model endpoint.
        
        Args:
            model_config: Model configuration
            request_data: Request data
            headers: Request headers
            
        Returns:
            Model response
            
        Raises:
            HTTPException: If the request fails
        """
        client = self._get_client(model_config)
        
        try:
            # Merge model headers with request headers
            all_headers = {**model_config.headers}
            if headers:
                all_headers.update(headers)
            
            # Make the request
            status_code, response_json, response_headers = await client.request(
                method="POST",
                url=model_config.endpoint_url,
                headers=all_headers,
                json_data=request_data,
                params=None
            )
            
            return response_json
            
        except Exception as e:
            logger.error(f"Error forwarding request to model {model_config.id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error forwarding request to model {model_config.id}"
            )

    async def proxy_to_model(self, model_id: str, request: Request, path_suffix: str = "") -> StarletteResponse:
        """
        Proxy a request to a model endpoint.
        
        Args:
            model_id: ID of the model to proxy to
            request: The incoming request
            path_suffix: Optional path suffix to append to the model's endpoint URL
            
        Returns:
            Response from the model endpoint
            
        Raises:
            ModelRequestError: If the request fails
            CircuitBreakerError: If the circuit breaker is open
        """
        logger.info(f"Proxying request to model: {model_id}")
        
        try:
            # Get model config
            model_config = self.model_registry.get_model_config(model_id)
            
            # Forward request to orchestrator
            response = await self.orchestrator.proxy_request(
                model_config=model_config,
                request=request,
                path_suffix=path_suffix
            )
            
            return response
            
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker error for model {model_id}: {str(e)}")
            raise ModelRequestError(
                message=f"circuit breaker is open for model {model_id}",
                model_id=model_id
            )
        except ModelRequestError as e:
            logger.error(f"Error proxying request to model '{model_id}': {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error proxying request to model '{model_id}': {str(e)}")
            raise ModelRequestError(
                message=str(e),
                model_id=model_id
            )

def get_proxy_service() -> ProxyService:
    """Get the proxy service instance."""
    return ProxyService()