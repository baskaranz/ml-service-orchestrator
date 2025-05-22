"""
Proxy service for forwarding requests to model endpoints.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from starlette.responses import Response as StarletteResponse

from app.core.exceptions import CircuitBreakerError, ModelRequestError
from app.models.config_models import ModelConfig
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.services.orchestrator import Orchestrator
from app.utils.http import HttpClient
from app.utils.logging import get_logger

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
        orchestrator: Optional[Orchestrator] = None,
    ):
        """Initialize the proxy service."""
        self.model_registry = model_registry or get_model_registry_service()
        self.orchestrator = orchestrator or Orchestrator()
        self._clients: Dict[str, HttpClient] = {}

    def _get_client(self, model_config: ModelConfig) -> HttpClient:
        """
        Get or create an HTTP client for a model with connection pooling.

        Args:
            model_config: Model configuration containing connection settings

        Returns:
            Configured HttpClient instance with connection pooling

        Raises:
            ValueError: If model configuration is invalid
        """
        if not model_config.id:
            raise ValueError("Model configuration must have an ID")

        if model_config.id not in self._clients:
            # Create a new HTTP client with connection pooling settings
            self._clients[model_config.id] = HttpClient(
                timeout=model_config.timeout,
                max_retries=model_config.max_retries,
                retry_delay=1.0,  # Default retry delay
                max_retry_delay=30.0,  # Default max retry delay
                backoff_factor=2.0,  # Default backoff factor
                auth_config=model_config.auth if hasattr(model_config, "auth") else None,
                pool_connections=model_config.pool_connections,
                pool_maxsize=model_config.pool_maxsize,
                max_keepalive_connections=model_config.max_keepalive_connections,
                keepalive_expiry=model_config.keepalive_timeout,
                http2=model_config.http2 if hasattr(model_config, "http2") else False,
            )

            logger.debug(
                f"Created HTTP client for model {model_config.id} with settings: "
                f"pool_connections={model_config.pool_connections}, "
                f"pool_maxsize={model_config.pool_maxsize}, "
                f"max_keepalive_connections={model_config.max_keepalive_connections}, "
                f"keepalive_timeout={model_config.keepalive_timeout}, "
                f"http2={getattr(model_config, 'http2', False)}"
            )

        return self._clients[model_config.id]

    async def forward_request(
        self,
        model_config: ModelConfig,
        request_data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
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
                json=request_data,
                content=None,
                params=None,
            )

            return response_json

        except Exception as e:
            logger.error(f"Error forwarding request to model {model_config.id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error forwarding request to model {model_config.id}"
            )

    async def proxy_to_model(
        self, model_id: str, request: Request, path_suffix: str = ""
    ) -> StarletteResponse:
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
                model_config=model_config, request=request, path_suffix=path_suffix
            )

            return response

        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker error for model {model_id}: {str(e)}")
            raise ModelRequestError(
                message=f"circuit breaker is open for model {model_id}", model_id=model_id
            )
        except ModelRequestError as e:
            logger.error(f"Error proxying request to model '{model_id}': {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error proxying request to model '{model_id}': {str(e)}")
            raise ModelRequestError(message=str(e), model_id=model_id)


def get_proxy_service() -> ProxyService:
    """Get the proxy service instance."""
    return ProxyService()
