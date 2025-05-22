"""
Orchestrator for managing model requests.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Union

from fastapi import HTTPException, Request
from pydantic import AnyUrl

from app.config.models_config import ModelConfigManager
from app.core.exceptions import CircuitBreakerError, ModelRequestError
from app.core.global_circuit_breaker import CircuitBreaker, global_circuit_breaker
from app.models.config_models import ModelConfig, PlatformConfig
from app.utils.error_handling import ModelErrorHandler, RetryConfig
from app.utils.http import HttpClient

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a StreamHandler that writes to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

# Create a formatter and add it to the handler
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)
logger.debug("Orchestrator module loaded and logger configured for DEBUG level")


class Orchestrator:
    """
    Orchestrator for managing model requests.

    This class is responsible for:
    1. Managing circuit breakers for each model
    2. Forwarding requests to the appropriate model
    3. Handling retries and timeouts
    """

    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """Initialize the orchestrator."""
        self.config_dir = Path(config_dir) if config_dir else None
        self.models: Dict[str, ModelConfig] = {}
        self.platform_config = PlatformConfig()
        self._http_client = HttpClient()
        self._model_config_manager = ModelConfigManager()
        self._http_clients: Dict[str, HttpClient] = {}
        self._error_handlers: Dict[str, ModelErrorHandler] = {}

        # Initialize global circuit breaker with platform config
        global_circuit_breaker.configure(self.platform_config.circuit_breaker.model_dump())

    async def startup(self) -> None:
        """Initialize the orchestrator asynchronously."""
        logger.info(f"Starting orchestrator initialization for instance {id(self)}...")

        try:
            # Log environment information
            logger.info(f"Environment: {os.getenv('APP_ENV', 'local')}")
            logger.info(f"Working directory: {os.getcwd()}")
            logger.info(f"Config directory: {self._model_config_manager.config_dir}")

            # Load models
            await self._load_models()

            # Initialize error handlers
            await self.initialize_error_handlers()

            logger.info("Orchestrator initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {str(e)}")
            logger.exception("Error details:")
            raise

    async def reload_configs(self) -> bool:
        """Reload model configurations from disk.

        This method reloads all model configurations from the configured directory,
        updating the in-memory models dictionary with the latest configurations.

        If the reload fails, the existing models are preserved.

        Returns:
            bool: True if the reload was successful, False otherwise
        """
        logger.info("Reloading model configurations...")

        # Store current state for rollback if needed
        old_models = self.models.copy()
        old_error_handlers = self._error_handlers.copy()

        try:
            # Clear current models and error handlers
            self.models.clear()
            self._error_handlers.clear()

            # Clear any cached state in the model config manager
            if hasattr(self._model_config_manager, "models"):
                self._model_config_manager.models.clear()
            if hasattr(self._model_config_manager, "last_modified"):
                self._model_config_manager.last_modified.clear()

            # Reload models using the existing config manager
            await self._load_models()

            # Reinitialize error handlers
            await self.initialize_error_handlers()

            logger.info(f"Successfully reloaded {len(self.models)} model configurations")
            return True

        except Exception as e:
            # Rollback on error
            self.models = old_models
            self._error_handlers = old_error_handlers
            logger.error(f"Failed to reload model configurations: {str(e)}")
            logger.exception("Error details:")
            return False

    async def _load_models(self) -> None:
        """Load models from configuration."""
        try:
            logger.info("Loading models using ModelConfigManager...")
            registry, loaded_models = await self._model_config_manager.load_configs()

            if loaded_models:
                # Filter active models and update the models dictionary
                self.models = {
                    mid: model
                    for mid, model in loaded_models.items()
                    if getattr(model, "active", True)
                }
                logger.info(f"Successfully loaded {len(self.models)} models")

                # Log loaded models
                for model_id, model in self.models.items():
                    logger.info(
                        f"  - {model_id}: {getattr(model, 'name', 'Unnamed')} "
                        f"(active: {getattr(model, 'active', True)})"
                    )
            else:
                logger.warning("No models found in configuration")

        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")
            logger.exception("Error details:")
            raise RuntimeError("Failed to load model configurations") from e

    async def initialize_error_handlers(self) -> None:
        """Initialize error handlers for all models."""
        try:
            for model_id, model_config in self.models.items():
                if model_config.active:
                    self._get_error_handler(model_config)
                    logger.info(f"Initialized error handler for model {model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize error handlers: {str(e)}")
            raise

    def _get_error_handler(self, model_config: ModelConfig) -> ModelErrorHandler:
        """Get or create an error handler for a model.

        Args:
            model_config: The model configuration

        Returns:
            ModelErrorHandler: The error handler for the model

        Raises:
            ValueError: If the model configuration is invalid
        """
        if not model_config.id:
            raise ValueError("Model configuration must have an ID")

        if model_config.id not in self._error_handlers:
            # Create a retry config from the model's platform config if available
            retry_config = None
            if model_config.platform:
                retry_config = RetryConfig(
                    max_retries=getattr(model_config.platform, "max_retries", 3),
                    initial_delay=1.0,  # Default initial delay
                    max_delay=10.0,  # Default max delay
                )

            # Initialize the error handler with the model config
            self._error_handlers[model_config.id] = ModelErrorHandler(
                model_config=model_config, retry_config=retry_config
            )

        return self._error_handlers[model_config.id]

    def get_circuit_breaker(self, model_config: ModelConfig) -> CircuitBreaker:
        """Get or create a circuit breaker for a model.

        Args:
            model_config: The model configuration

        Returns:
            CircuitBreaker: The circuit breaker instance for the model

        Raises:
            ValueError: If the model configuration is invalid
        """
        if not model_config.id:
            raise ValueError("Model configuration must have an ID")

        # Get platform-specific overrides if any
        circuit_breaker_config = {}
        if model_config.platform and model_config.platform.circuit_breaker:
            # Handle both Pydantic models and dictionaries
            if hasattr(model_config.platform.circuit_breaker, "dict"):
                circuit_breaker_config = model_config.platform.circuit_breaker.dict()
            elif isinstance(model_config.platform.circuit_breaker, dict):
                circuit_breaker_config = model_config.platform.circuit_breaker
            else:
                logger.warning(
                    f"Unexpected circuit_breaker type: {type(model_config.platform.circuit_breaker)}"
                )

        # Get or create the circuit breaker from global instance
        return global_circuit_breaker.get_circuit_breaker(
            model_id=model_config.id, config_override=circuit_breaker_config
        )

    async def execute_with_circuit_breaker(
        self, model_config: ModelConfig, func: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Execute a function with circuit breaker protection."""
        circuit_breaker = self.get_circuit_breaker(model_config)
        try:
            return await circuit_breaker.execute_async(func)
        except CircuitBreakerError as e:
            # Re-raise with model context if missing
            if not getattr(e, "model_id", None) and hasattr(circuit_breaker, "model_id"):
                e.model_id = circuit_breaker.model_id
            raise

    async def proxy_request(
        self, model_config: ModelConfig, request: Request, path_suffix: str = ""
    ) -> Any:
        """Proxy a request to a model endpoint with circuit breaker protection.

        Args:
            model_config: The model configuration
            request: The incoming HTTP request
            path_suffix: Optional path suffix to append to the model's endpoint URL

        Returns:
            The response from the model

        Raises:
            ModelRequestError: If the model is not found, not active, or the request fails
        """
        model_id = getattr(model_config, "id", "unknown")

        # Check if model is active first (don't check existence if we have the config directly)
        if not getattr(model_config, "active", True):
            raise ModelRequestError(
                f"Model '{model_id}' is not active",
                status_code=409,
                model_id=model_id,
                details={"status": "not active"},
            )

        # Check if model exists in the orchestrator's models (only if we don't have the config directly)
        if model_id not in self.models and model_config not in self.models.values():
            raise ModelRequestError(
                f"Model '{model_id}' not found or not available", status_code=404, model_id=model_id
            )

        # If we get here, the model is either in self.models or was passed directly and is active

        async def _execute_request():
            # Get HTTP client with connection pooling
            http_client = self._get_http_client(model_config)

            # Build target URL
            target_url = self._build_target_url(model_config.endpoint_url, path_suffix)

            # Get content type from request headers
            content_type = request.headers.get("content-type", "")
            is_json = (
                content_type == "application/json"
            )  # Only set is_json for exact JSON content type

            # Prepare base request arguments
            request_args = {
                "method": request.method,
                "url": target_url,
                "headers": dict(request.headers),
                "params": dict(request.query_params),
                "timeout": getattr(model_config, "timeout", 30.0),
            }

            # Handle request body for methods that typically have a body
            if request.method in ("POST", "PUT", "PATCH"):
                if is_json:
                    # For JSON content type, parse and use the json parameter
                    try:
                        json_data = await request.json()
                        if json_data:  # Only add json parameter if there's actual data
                            request_args["json"] = json_data
                    except json.JSONDecodeError:
                        # If JSON parsing fails, fall back to raw body
                        body = await request.body()
                        if body:
                            request_args["data"] = body
                else:
                    # For non-JSON content, use the raw body
                    body = await request.body()
                    if body:
                        request_args["data"] = body

            # Log the request details for debugging
            logger.debug(
                f"Sending request to {request_args['url']} with method {request_args['method']}"
            )
            logger.debug(f"Request headers: {request_args['headers']}")
            logger.debug(f"Request params: {request_args['params']}")

            if "json" in request_args:
                logger.debug(f"Request JSON data: {request_args['json']}")
            elif "data" in request_args:
                logger.debug(f"Request raw data: {request_args['data']}")

            try:
                # Make the request
                response = await http_client.request(**request_args)

                # Log the response type for debugging
                logger.debug(f"Response type: {type(response)}")
                logger.debug(f"Response content: {response}")

                # Handle tuple response (status_code, content, headers) from http_client.request()
                if isinstance(response, tuple) and len(response) == 3:
                    status_code, content, headers = response
                    logger.debug(
                        f"Received tuple response - Status: {status_code}, Content: {content}"
                    )
                    return {
                        "status_code": status_code,
                        "content": content,
                        "headers": dict(headers) if headers is not None else {},
                    }

                # Handle HTTP response object (for backward compatibility)
                if hasattr(response, "status_code"):
                    content = response.text if hasattr(response, "text") else str(response.content)
                    return {
                        "status_code": response.status_code,
                        "content": content,
                        "headers": dict(response.headers) if hasattr(response, "headers") else {},
                    }

                # Handle dictionary response (mocked response or already processed)
                if isinstance(response, dict):
                    logger.debug(f"Received dict response: {response}")
                    return response

                # If we get here, it's an unexpected response type
                error_msg = f"Unexpected response type: {type(response)}"
                logger.error(error_msg)
                raise ModelRequestError(error_msg)

            except Exception as e:
                error_msg = f"Error making request to model: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise ModelRequestError(error_msg) from e

        # Define a wrapper function to ensure consistent response format
        async def execute_with_format():
            # Execute the request
            response = await _execute_request()

            # Ensure the response is in the correct format
            if isinstance(response, dict) and "status_code" in response and "content" in response:
                return response
            elif isinstance(response, tuple) and len(response) == 3:
                status_code, content, headers = response
                return {
                    "status_code": status_code,
                    "content": content,
                    "headers": dict(headers) if headers is not None else {},
                }
            elif hasattr(response, "status_code"):
                content = response.text if hasattr(response, "text") else str(response.content)
                return {
                    "status_code": response.status_code,
                    "content": content,
                    "headers": dict(response.headers) if hasattr(response, "headers") else {},
                }
            else:
                return {"status_code": 200, "content": response, "headers": {}}

        # Execute the request with circuit breaker protection
        try:
            # Execute the request and format the response
            response = await self.execute_with_circuit_breaker(model_config, _execute_request)

            # Log the response for debugging
            logger.debug(f"Response from execute_with_circuit_breaker: {response}")

            # Ensure we have a valid response
            if (
                not isinstance(response, dict)
                or "status_code" not in response
                or "content" not in response
            ):
                error_msg = f"Unexpected response format from circuit breaker: {response}"
                logger.error(error_msg)
                raise ModelRequestError(error_msg)

            # Process the response through the error handler
            error_handler = self._get_error_handler(model_config)

            # Return the response directly since we already have it in the correct format
            return response

        except Exception as e:
            logger.error(f"Error in proxy_request: {str(e)}", exc_info=True)
            raise ModelRequestError(
                f"Failed to proxy request to model: {str(e)}", status_code=500, model_id=model_id
            )

    async def _prepare_request_data(self, request: Request) -> Dict[str, Any]:
        """Extract and parse request body.

        If the content type is 'application/json', returns the parsed JSON as a dictionary.
        For other content types, returns the raw body in a dictionary with a 'raw' key.
        """
        try:
            logger.debug(f"Preparing request data. Headers: {dict(request.headers)}")
            content_type = request.headers.get("content-type", "").lower()
            logger.debug(f"Content-Type: {content_type}")

            if "application/json" in content_type:
                # For JSON content type, parse and return the JSON directly
                try:
                    json_data = await request.json()
                    logger.debug(f"Successfully parsed JSON: {json_data}")
                    return json_data
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error in request.json(): {str(e)}")
                    raise
            else:
                # For non-JSON content, return the raw body in a dictionary with a 'raw' key
                try:
                    body = await request.body()
                    logger.debug(f"Got raw body: {body}")
                    return {"raw": body}
                except Exception as e:
                    logger.error(f"Error reading request body: {str(e)}")
                    raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON request body: {str(e)}")
            raise ModelRequestError(f"Failed to parse request body: {str(e)}", status_code=400)
        except Exception as e:
            logger.error(f"Error parsing request body: {str(e)}", exc_info=True)
            raise ModelRequestError(f"Failed to parse request body: {str(e)}", status_code=400)

    def _build_target_url(self, base_url: Union[str, AnyUrl], path_suffix: str) -> str:
        """Build the target URL for the request."""
        url_str = str(base_url).rstrip("/")
        if not path_suffix or path_suffix == "/":
            return url_str

        clean_suffix = path_suffix.lstrip("/")
        return f"{url_str}/{clean_suffix}"

    def _get_http_client(self, model_config: ModelConfig) -> HttpClient:
        """Get or create an HTTP client for a model with connection pooling.

        Args:
            model_config: The model configuration

        Returns:
            HttpClient: An HTTP client instance
        """
        if not model_config.id:
            return self._http_client

        if model_config.id not in self._http_clients:
            # Get retry configuration from model config or use defaults
            max_retries = 3
            if model_config.platform and hasattr(model_config.platform, "retry"):
                max_retries = model_config.platform.retry.get("max_retries", 3)

            # Get timeout from model config or use default
            timeout = 30.0
            if hasattr(model_config, "timeout"):
                timeout = model_config.timeout

            # Get HTTP/2 setting from model config or default to False
            http2 = False
            if hasattr(model_config, "http2"):
                http2 = model_config.http2

            # Create the HTTP client with the correct parameters
            self._http_clients[model_config.id] = HttpClient(
                timeout=timeout, max_retries=max_retries, http2=http2
            )

        return self._http_clients[model_config.id]

    async def check_model_health(self, model_id: str) -> Dict[str, Any]:
        """Check the health of a specific model.

        Args:
            model_id: The ID of the model to check

        Returns:
            Dict containing health status and details

        Raises:
            HTTPException: If the model is not found or health check fails
        """
        if model_id not in self.models:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        model_config = self.models[model_id]

        # Get the health check endpoint from the model's platform config if available
        health_check_path = "/health"  # Default health check path
        if hasattr(model_config, "platform") and hasattr(model_config.platform, "health_check"):
            health_check = model_config.platform.health_check
            if hasattr(health_check, "endpoint"):
                health_check_path = health_check.endpoint

        # Build the full health check URL
        base_url = model_config.endpoint_url.split("/predict")[
            0
        ]  # Remove /predict suffix if present
        health_endpoint = f"{base_url.rstrip('/')}{health_check_path}"

        try:
            client = self._get_http_client(model_config)
            response = await client.request(
                method="GET",
                url=health_endpoint,
                headers={"Content-Type": "application/json"},
                timeout=10.0,  # Shorter timeout for health checks
            )

            # Handle response based on return type
            if isinstance(response, tuple):
                # Tuple format: (status_code, response_data, headers)
                status_code, response_data, _ = response
                response_json = response_data if isinstance(response_data, dict) else {}
            else:
                # httpx.Response object
                status_code = (
                    response[0]
                    if isinstance(response, tuple) and len(response) >= 1
                    else response.status_code
                )
                try:
                    response_json = response.json() if response.content else {}
                except Exception:
                    response_json = {}

            if status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Health check failed for model {model_id} with status {status_code}",
                )

            return {"status": "healthy", "model_id": model_id, "details": response_json}

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Health check failed for model {model_id}: {str(e)}")
            logger.exception("Error details:")
            raise HTTPException(
                status_code=500, detail=f"Health check failed for model {model_id}: {str(e)}"
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get system and model metrics.

        Returns:
            Dict containing system and model metrics
        """
        # Create a simple dictionary with basic types that can be JSON-serialized
        metrics = {
            "system": {
                "models_loaded": len(self.models),
                "active_models": [
                    str(model_id)
                    for model_id, model in self.models.items()
                    if getattr(model, "active", False)
                ],
                "http_clients": len(self._http_clients),
                "error_handlers": len(self._error_handlers),
            },
            "models": {},
        }

        # Add per-model metrics
        for model_id, model in self.models.items():
            endpoint_url = getattr(model, "endpoint_url", "N/A")
            if hasattr(endpoint_url, "host"):
                endpoint_url = str(endpoint_url)

            metrics["models"][str(model_id)] = {
                "active": bool(getattr(model, "active", False)),
                "endpoint": endpoint_url,
                "timeout": float(getattr(model, "timeout", 30.0)),
                "max_retries": int(getattr(model, "max_retries", 3)),
                "has_error_handler": bool(model_id in self._error_handlers),
                "has_http_client": bool(model_id in self._http_clients),
            }

        return metrics

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system and model statistics.

        Returns:
            Dict containing system and model statistics
        """
        stats = {
            "system": {
                "models_loaded": len(self.models),
                "active_models": [
                    str(model_id)
                    for model_id, model in self.models.items()
                    if getattr(model, "active", False)
                ],
                "http_clients": len(self._http_clients),
                "error_handlers": len(self._error_handlers),
            },
            "models": {},
        }

        # Add per-model statistics
        for model_id, model in self.models.items():
            endpoint_url = getattr(model, "endpoint_url", "N/A")
            if hasattr(endpoint_url, "host"):
                endpoint_url = str(endpoint_url)

            stats["models"][str(model_id)] = {
                "active": bool(getattr(model, "active", False)),
                "endpoint": endpoint_url,
                "timeout": float(getattr(model, "timeout", 30.0)),
                "max_retries": int(getattr(model, "max_retries", 3)),
            }

        return stats

    async def refresh_models(self) -> Dict[str, Any]:
        """Refresh model configurations by reloading from disk.

        Returns:
            Dict containing refresh status and results
        """
        try:
            success = await self.reload_configs()
            return {
                "status": "success" if success else "partial_success",
                "message": "Model configurations refreshed successfully",
                "models_loaded": len(self.models),
            }
        except Exception as e:
            logger.error(f"Failed to refresh models: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to refresh models: {str(e)}",
                "models_loaded": len(self.models),
            }

    async def discover_models(self) -> Dict[str, Any]:
        """Discover and register available models.

        This is a placeholder that can be extended to scan for new model configurations
        in the configured directories.

        Returns:
            Dict containing discovery results
        """
        try:
            # For now, just return the current models
            # In a real implementation, this would scan directories for new model configs
            return {
                "status": "success",
                "message": "Model discovery completed",
                "models_found": len(self.models),
                "models": list(self.models.keys()),
            }
        except Exception as e:
            logger.error(f"Model discovery failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Model discovery failed: {str(e)}",
                "models_found": 0,
            }
