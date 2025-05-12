"""
Orchestrator service for managing model requests.
"""

import pybreaker
import json
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, Request, Response

from app.models.config_models import ModelConfig
from app.utils.logging import get_logger
from app.core.exceptions import ModelRequestError, CircuitBreakerError
from app.utils.http import HttpClient, build_url

logger = get_logger(__name__)

class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """Listener for circuit breaker events."""
    
    def on_success(self, cb: pybreaker.CircuitBreaker) -> None:
        """Called when a call succeeds."""
        logger.debug(f"Circuit breaker {cb.name} succeeded")
    
    def on_failure(self, cb: pybreaker.CircuitBreaker, exc: Exception) -> None:
        """Called when a call fails."""
        logger.debug(f"Circuit breaker {cb.name} failed: {exc}")
    
    def on_open(self, cb: pybreaker.CircuitBreaker) -> None:
        """Called when the circuit breaker opens."""
        logger.warning(f"Circuit breaker {cb.name} opened")
    
    def on_close(self, cb: pybreaker.CircuitBreaker) -> None:
        """Called when the circuit breaker closes."""
        logger.info(f"Circuit breaker {cb.name} closed")
    
    def on_half_open(self, cb: pybreaker.CircuitBreaker) -> None:
        """Called when the circuit breaker half-opens."""
        logger.info(f"Circuit breaker {cb.name} half-opened")

class Orchestrator:
    """
    Orchestrator for managing model requests.
    
    This class is responsible for:
    1. Managing circuit breakers for each model
    2. Forwarding requests to the appropriate model
    3. Handling retries and timeouts
    """
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.circuit_breakers: Dict[str, pybreaker.CircuitBreaker] = {}
        self._clients: Dict[str, HttpClient] = {}
    
    def _get_client(self, model_config: ModelConfig) -> HttpClient:
        """Get or create an HTTP client for a model."""
        if not model_config.id:
            raise ValueError("Model configuration must have an ID")
        if model_config.id not in self._clients:
            self._clients[model_config.id] = HttpClient(
                timeout=model_config.timeout if hasattr(model_config, 'timeout') else 30.0
            )
        return self._clients[model_config.id]

    def _build_target_url(self, base_url: str, path_suffix: str = "") -> str:
        """Build the target URL for a request."""
        return build_url(base_url, path_suffix)

    def _get_exclude_exceptions(self, model_config: ModelConfig) -> List[type]:
        """Get the list of exceptions to exclude from circuit breaker."""
        exclude_exceptions = []
        if model_config.circuit_breaker and hasattr(model_config.circuit_breaker, 'exclude_exceptions'):
            for exc_name in model_config.circuit_breaker.exclude_exceptions:
                try:
                    exc = eval(exc_name)  # Convert string to exception class
                    exclude_exceptions.append(exc)
                except (NameError, SyntaxError):
                    pass
        return exclude_exceptions

    def get_circuit_breaker(self, model_config: ModelConfig) -> pybreaker.CircuitBreaker:
        """Get or create a circuit breaker for a model."""
        if not model_config.id:
            raise ValueError("Model configuration must have an ID")
        if model_config.id not in self.circuit_breakers:
            exclude_exceptions = self._get_exclude_exceptions(model_config)
            self.circuit_breakers[model_config.id] = pybreaker.CircuitBreaker(
                fail_max=model_config.circuit_breaker.failure_threshold if model_config.circuit_breaker else 5,
                reset_timeout=model_config.circuit_breaker.reset_timeout if model_config.circuit_breaker else 60.0,
                exclude=exclude_exceptions
            )
        return self.circuit_breakers[model_config.id]

    async def _get_request_body(self, request: Request) -> Union[Dict[str, Any], Dict[str, bytes]]:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body = await request.json()
                if not isinstance(body, dict):
                    raise ModelRequestError("Request body must be a JSON object")
                return body
            except Exception as e:
                raise ModelRequestError(f"Failed to parse request body: {str(e)}")
        else:
            body = await request.body()
            return {"raw": body}

    async def _execute_proxied_request(
        self,
        http_client: HttpClient,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Union[Dict[str, Any], Dict[str, bytes]],
        params: Dict[str, Any],
        model_id: str
    ) -> Response:
        """Execute a proxied request to a model endpoint."""
        try:
            logger.debug(f"Proxying request to {url} with method {method}")
            
            # Remove content-length header as it will be set by the HTTP client
            headers = {k: v for k, v in headers.items() if k.lower() != 'content-length'}
            
            logger.debug(f"Request headers: {headers}")
            logger.debug(f"Request data type: {type(data)}")
            if isinstance(data, dict):
                logger.debug(f"Request data (dict): {data}")
            elif isinstance(data, bytes):
                logger.debug(f"Request data (bytes): {data!r}")
            else:
                logger.debug(f"Request data (other): {data}")

            if isinstance(data, dict) and "raw" in data:
                status_code, response_body, response_headers = await http_client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=data["raw"],
                    params=params
                )
            else:
                if isinstance(data, dict):
                    status_code, response_body, response_headers = await http_client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json_data=data,
                        params=params
                    )
                else:
                    raise ModelRequestError(
                        f"Unsupported request body type for JSON: {type(data)}",
                        model_id=model_id
                    )
            if isinstance(response_body, dict):
                content = json.dumps(response_body).encode()
            elif isinstance(response_body, (bytes, bytearray, memoryview)):
                content = bytes(response_body)
            else:
                content = str(response_body).encode()
            return Response(
                content=content,
                status_code=status_code,
                headers=response_headers,
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Proxy request error: {e}")
            raise ModelRequestError(
                f"Failed to execute request to model {model_id}: {str(e)}",
                model_id=model_id
            )

    async def proxy_request(
        self,
        model_config: ModelConfig,
        request: Request,
        path_suffix: str = ""
    ) -> Response:
        """Proxy a request to a model endpoint."""
        if not model_config.id:
            raise ValueError("Model configuration must have an ID")

        # Check if model is active
        if not model_config.active:
            raise ModelRequestError(
                f"Model {model_config.id} is not active",
                model_id=model_config.id
            )

        # Get circuit breaker and HTTP client
        circuit_breaker = self.get_circuit_breaker(model_config)
        http_client = self._get_client(model_config)

        try:
            # Get request body
            body = await self._get_request_body(request)

            # Build target URL
            target_url = self._build_target_url(model_config.endpoint_url, path_suffix)

            # Execute request through circuit breaker
            return await circuit_breaker.call(
                self._execute_proxied_request,
                http_client=http_client,
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                data=body,
                params=dict(request.query_params),
                model_id=model_config.id
            )
        except pybreaker.CircuitBreakerError as e:
            raise CircuitBreakerError(
                message=f"Circuit breaker is open for model {model_config.id}",
                model_id=model_config.id
            )
        except Exception as e:
            if isinstance(e, (ModelRequestError, CircuitBreakerError)):
                raise
            raise ModelRequestError(
                f"Failed to proxy request to model {model_config.id}: {str(e)}",
                model_id=model_config.id
            ) 