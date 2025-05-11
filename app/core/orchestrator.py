"""
Core orchestration logic for routing requests to model endpoints.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union

import pybreaker
from fastapi import Request, Response, HTTPException

from app.core.exceptions import CircuitBreakerError, ModelRequestError
from app.models.config_models import ModelConfig
from app.services.proxy import ProxyService
from app.utils.http import HttpClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """
    Core orchestration service for routing requests to model endpoints.
    """
    
    def __init__(self):
        """Initialize the orchestrator with empty state."""
        self.circuit_breakers: Dict[str, pybreaker.CircuitBreaker] = {}
    
    def get_circuit_breaker(self, model_config: ModelConfig) -> pybreaker.CircuitBreaker:
        """
        Get or create a circuit breaker for a model.
        
        Args:
            model_config: Model configuration
            
        Returns:
            Circuit breaker for the model
        """
        model_id = model_config.id
        
        if model_id not in self.circuit_breakers:
            # Configure the circuit breaker based on model settings
            cb_settings = model_config.circuit_breaker
            
            # Create a new circuit breaker
            self.circuit_breakers[model_id] = pybreaker.CircuitBreaker(
                fail_max=cb_settings.failure_threshold,
                reset_timeout=cb_settings.reset_timeout,
                exclude=self._get_exclude_exceptions(cb_settings.exclude_exceptions),
                listeners=[CircuitBreakerListener(model_id)]
            )
        
        return self.circuit_breakers[model_id]
    
    def _get_exclude_exceptions(self, exclude_names: List[str]) -> List[type]:
        """
        Convert exception names to exception types.
        
        Args:
            exclude_names: List of exception names to exclude
            
        Returns:
            List of exception types
        """
        result = []
        for name in exclude_names:
            try:
                # Try to get the exception from the built-in exceptions
                exc_type = getattr(__builtins__, name, None)
                if exc_type and issubclass(exc_type, Exception):
                    result.append(exc_type)
            except (AttributeError, TypeError):
                logger.warning(f"Invalid exception name: {name}")
        
        return result
    
    async def proxy_request(
        self,
        model_config: ModelConfig,
        request: Request,
        path_suffix: str = "",
    ) -> Response:
        """
        Proxy a request to a model endpoint with circuit breaking.
        
        Args:
            model_config: Model configuration
            request: Original FastAPI request
            path_suffix: Additional path to append to the endpoint URL
            
        Returns:
            Response from the model endpoint
            
        Raises:
            ModelRequestError: If the model request fails
            CircuitBreakerError: If the circuit breaker is open
        """
        # Check if the model is active
        if not model_config.active:
            raise ModelRequestError(
                message=f"Model '{model_config.id}' is not active",
                status_code=503,
                model_id=model_config.id
            )
        
        # Get circuit breaker for this model
        circuit_breaker = self.get_circuit_breaker(model_config)
        
        # Get the target URL
        target_url = self._build_target_url(model_config.endpoint_url, path_suffix)
        
        # Create HTTP client with model settings
        http_client = HttpClient(
            timeout=model_config.timeout,
            max_retries=model_config.max_retries,
            auth_config=model_config.auth
        )
        
        # Get request content
        request_body = await self._get_request_body(request)
        
        # Get headers, filtering out host header
        headers = dict(request.headers)
        headers.pop("host", None)
        
        # Add any additional headers from model config
        headers.update(model_config.headers)
        
        # Apply circuit breaker
        try:
            # Use the circuit breaker to protect the request
            return await circuit_breaker.call(
                self._execute_proxied_request,
                http_client=http_client,
                method=request.method,
                url=target_url,
                headers=headers,
                data=request_body,
                params=dict(request.query_params),
                model_id=model_config.id
            )
        except pybreaker.CircuitBreakerError:
            # Circuit is open
            raise CircuitBreakerError(model_id=model_config.id)
        except Exception as e:
            # Other errors
            logger.error(
                f"Error proxying request to model '{model_config.id}': {str(e)}",
                exc_info=True
            )
            raise ModelRequestError(
                message=f"Error proxying request: {str(e)}",
                status_code=500,
                model_id=model_config.id
            )
    
    def _build_target_url(self, base_url: str, path_suffix: str) -> str:
        """
        Build the target URL for the proxied request.
        
        Args:
            base_url: Base endpoint URL
            path_suffix: Path suffix to append
            
        Returns:
            Full target URL
        """
        # Remove trailing slash from base URL if present
        base = base_url[:-1] if base_url.endswith("/") else base_url
        
        # Remove leading slash from path suffix if present
        suffix = path_suffix[1:] if path_suffix.startswith("/") else path_suffix
        
        # Combine with a slash
        if suffix:
            return f"{base}/{suffix}"
        else:
            return base
    
    async def _get_request_body(self, request: Request) -> Optional[Union[Dict[str, Any], bytes]]:
        """
        Extract the request body.
        
        Args:
            request: FastAPI request
            
        Returns:
            Request body as dict or bytes, or None if empty
        """
        # Get content type
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # Parse JSON body
            try:
                return await request.json()
            except Exception as e:
                logger.warning(f"Error parsing JSON body: {str(e)}")
                return await request.body()
        else:
            # Return raw body
            return await request.body()
    
    async def _execute_proxied_request(
        self,
        http_client: HttpClient,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Any,
        params: Dict[str, str],
        model_id: str
    ) -> Response:
        """
        Execute the proxied request.
        
        Args:
            http_client: HTTP client to use
            method: HTTP method
            url: Target URL
            headers: Request headers
            data: Request body
            params: Query parameters
            model_id: Model ID
            
        Returns:
            FastAPI response
            
        Raises:
            ModelRequestError: If the request fails
        """
        try:
            # Execute the HTTP request
            status_code, json_data, response_headers = await http_client.request(
                method=method,
                url=url,
                headers=headers,
                json_data=data if isinstance(data, dict) else None,
                params=params
            )
            
            # Create FastAPI response
            return Response(
                content=str(json_data),
                status_code=status_code,
                headers=response_headers,
                media_type="application/json"
            )
            
        except Exception as e:
            logger.error(
                f"Error in proxied request to model '{model_id}': {str(e)}",
                exc_info=True
            )
            raise ModelRequestError(
                message=f"Error in proxied request: {str(e)}",
                status_code=500,
                model_id=model_id
            )


class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """
    Listener for circuit breaker state changes.
    """
    
    def __init__(self, model_id: str):
        """
        Initialize the listener.
        
        Args:
            model_id: Model ID
        """
        self.model_id = model_id
    
    def state_change(self, cb: pybreaker.CircuitBreaker, old_state: str, new_state: str) -> None:
        """
        Handle circuit breaker state changes.
        
        Args:
            cb: The circuit breaker
            old_state: Previous state
            new_state: New state
        """
        logger.warning(
            f"Circuit breaker for model '{self.model_id}' changed from {old_state} to {new_state}"
        )
    
    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception) -> None:
        """
        Handle circuit breaker failures.
        
        Args:
            cb: The circuit breaker
            exc: The exception that caused the failure
        """
        logger.error(
            f"Circuit breaker for model '{self.model_id}' recorded a failure: {str(exc)}",
            exc_info=True
        )
    
    def success(self, cb: pybreaker.CircuitBreaker) -> None:
        """
        Handle circuit breaker successes.
        
        Args:
            cb: The circuit breaker
        """
        # Only log when circuit is half-open to avoid excessive logging
        if cb.current_state == 'half-open':
            logger.info(f"Circuit breaker for model '{self.model_id}' recorded a success")