"""
HTTP client utilities.
"""

import asyncio
import base64
from typing import Any, Dict, Optional, Tuple, Union

import httpx
from pydantic import BaseModel
from fastapi import HTTPException
from app.core.exceptions import ModelRequestError

from app.models.config_models import AuthConfig, AuthLocation, AuthType
from app.utils.logging import get_logger

logger = get_logger(__name__)


class HttpClient:
    """
    HTTP client wrapper with authentication and retry logic.
    """
    
    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        auth_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the HTTP client.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for retries
            auth_config: Authentication configuration
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.auth_config = auth_config or {}
    
    def _apply_auth(self, headers: Dict[str, str], params: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """Apply authentication to request headers and parameters."""
        auth = self.auth_config
        # Accept both dict and AuthConfig or MagicMock
        if hasattr(auth, '__dict__') or 'MagicMock' in str(type(auth)):
            auth_type = getattr(auth, 'type', None)
            if auth_type is not None and hasattr(auth_type, 'value'):
                auth_type = auth_type.value
            key = getattr(auth, 'key_name', None) or getattr(auth, 'key', "")
            value = getattr(auth, 'key_value', None) or getattr(auth, 'value', "")
            location = getattr(auth, 'location', None)
            if location is not None and hasattr(location, 'value'):
                location = location.value
            location = location or "header"
            username = getattr(auth, 'username', "")
            password = getattr(auth, 'password', "")
        else:
            auth_type = auth.get("type")
            key = auth.get("key", "")
            value = auth.get("value", "")
            location = auth.get("location", "header")
            username = auth.get("username", "")
            password = auth.get("password", "")
        if not auth_type:
            return headers, params
        if auth_type in ("api_key", AuthType.API_KEY, "API_KEY"):
            if key and value:
                if location == "header":
                    headers[key] = value
                else:
                    params[key] = value
        elif auth_type in ("bearer", AuthType.BEARER_TOKEN, "BEARER_TOKEN"):
            token = value
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif auth_type in ("basic", AuthType.BASIC_AUTH, "BASIC_AUTH"):
            if username and password:
                auth_str = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {auth_str}"
        return headers, params
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        data: Optional[Dict[str, Any]] = None,
        content: Optional[bytes] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Tuple[int, Any, Dict[str, str]]:
        """
        Make an HTTP request with retries and authentication.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            json_data: JSON request body (dict or Pydantic model)
            data: Form data (dict)
            content: Raw bytes
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (status_code, response_body, response_headers)
            
        Raises:
            ModelRequestError: If the request fails
        """
        headers = headers or {}
        params = params or {}
        
        # Convert Pydantic model to dict if needed
        if isinstance(json_data, BaseModel):
            json_data = json_data.model_dump()
        
        # Apply authentication
        if self.auth_config:
            headers, params = self._apply_auth(headers, params)
        
        # Make request with retries
        for attempt in range(self.max_retries):
            try:
                async with create_httpx_client(timeout=timeout or self.timeout) as client:
                    if content is not None:
                        response = await client.request(
                            method=method,
                            url=url,
                            headers=headers,
                            content=content,
                            params=params
                        )
                    else:
                        response = await client.request(
                            method=method,
                            url=url,
                            headers=headers,
                            json=json_data,
                            data=data,
                            params=params
                        )
                    response.raise_for_status()
                    try:
                        return response.status_code, response.json(), dict(response.headers)
                    except ValueError:
                        return response.status_code, response.content, dict(response.headers)
            except httpx.TimeoutException as e:
                if attempt == self.max_retries - 1:
                    raise ModelRequestError(
                        message=f"Request timed out after {timeout or self.timeout} seconds",
                        model_id=url
                    )
                await asyncio.sleep(self.backoff_factor * (2 ** attempt))
            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    raise ModelRequestError(
                        message=f"Request failed: {str(e)}",
                        model_id=url
                    )
                await asyncio.sleep(self.backoff_factor * (2 ** attempt))
            except httpx.HTTPStatusError as e:
                raise ModelRequestError(
                    message=f"HTTP error {e.response.status_code}: {str(e)}",
                    model_id=url
                )
            except Exception as e:
                raise ModelRequestError(
                    message=f"Unexpected error: {str(e)}",
                    model_id=url
                )
        
        # This should never be reached due to raises in the loop
        raise ModelRequestError(
            message="Request failed after all retries",
            model_id=url
        )

def build_url(base_url: str, path: Optional[str] = None, query_params: Optional[Dict[str, Any]] = None) -> str:
    """Build a URL from components."""
    url = base_url.rstrip('/')
    if path:
        url = f"{url}/{path.lstrip('/')}"
    if query_params:
        query_string = '&'.join(f"{k}={v}" for k, v in query_params.items())
        url = f"{url}?{query_string}"
    return url

async def make_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    content: Optional[bytes] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> httpx.Response:
    """Make an HTTP request and return the response."""
    async with httpx.AsyncClient() as client:
        try:
            if content is not None:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=content,
                    params=params,
                    timeout=timeout,
                )
            else:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    data=data,
                    params=params,
                    timeout=timeout,
                )
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            raise ModelRequestError(
                message=f"Request timed out after {timeout} seconds",
                model_id=url
            )
        except httpx.RequestError as e:
            raise ModelRequestError(
                message=f"Request failed: {str(e)}",
                model_id=url
            )
        except httpx.HTTPStatusError as e:
            raise ModelRequestError(
                message=f"HTTP error {e.response.status_code}: {str(e)}",
                model_id=url
            )
        except Exception as e:
            raise ModelRequestError(
                message=f"Unexpected error: {str(e)}",
                model_id=url
            )

def handle_request_error(error: Exception, model_id: str) -> Exception:
    """Handle HTTP request errors and convert to appropriate exceptions."""
    if isinstance(error, httpx.TimeoutException):
        raise ModelRequestError(
            message=f"Request to {model_id} timed out",
            model_id=model_id
        )
    elif isinstance(error, httpx.RequestError):
        raise ModelRequestError(
            message=f"Failed to connect to {model_id}: {str(error)}",
            model_id=model_id
        )
    elif isinstance(error, httpx.HTTPStatusError):
        raise ModelRequestError(
            message=f"HTTP error {error.response.status_code}: {str(error)}",
            model_id=model_id
        )
    else:
        raise ModelRequestError(
            message=f"Unexpected error: {str(error)}",
            model_id=model_id
        )

def create_httpx_client(timeout: float = 30.0, follow_redirects: bool = True, headers: Optional[Dict[str, str]] = None) -> httpx.AsyncClient:
    """Create an httpx client with default settings."""
    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=follow_redirects,
        headers=headers
    )