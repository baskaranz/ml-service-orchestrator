"""
HTTP client utilities.
"""

import asyncio
from typing import Any, Dict, Optional, Tuple, Union

import httpx
from pydantic import BaseModel

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
        auth_config: Optional[AuthConfig] = None
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
        self.auth_config = auth_config or AuthConfig()
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Union[Dict[str, Any], BaseModel]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
        """
        Make an HTTP request with retries and authentication.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            headers: Optional headers
            json_data: Optional JSON body (dict or Pydantic model)
            params: Optional query parameters
            timeout: Optional timeout override
            
        Returns:
            Tuple of (status_code, response_json, response_headers)
        """
        # Convert Pydantic model to dict if needed
        if isinstance(json_data, BaseModel):
            json_data = json_data.model_dump()
        
        # Initialize headers
        request_headers = headers.copy() if headers else {}
        
        # Apply authentication
        self._apply_auth(request_headers, params)
        
        # Set timeout
        request_timeout = httpx.Timeout(timeout or self.timeout)
        
        # Retry with backoff
        retry_count = 0
        
        while True:
            try:
                async with httpx.AsyncClient(timeout=request_timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=request_headers,
                        json=json_data,
                        params=params
                    )
                    
                    # Try to parse response as JSON, fallback to empty dict on error
                    try:
                        response_json = response.json()
                    except ValueError:
                        response_json = {}
                    
                    # Convert headers to dict
                    response_headers = dict(response.headers)
                    
                    return response.status_code, response_json, response_headers
                    
            except (httpx.RequestError, httpx.TimeoutException) as e:
                retry_count += 1
                
                if retry_count > self.max_retries:
                    logger.error(f"Request failed after {self.max_retries} retries: {str(e)}")
                    raise
                
                # Calculate backoff delay with exponential backoff
                delay = self.backoff_factor * (2 ** (retry_count - 1))
                logger.warning(f"Request failed, retrying in {delay:.2f}s ({retry_count}/{self.max_retries})")
                
                # Wait before retrying
                await asyncio.sleep(delay)
    
    def _apply_auth(
        self, 
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Apply authentication to the request.
        
        Args:
            headers: Headers dictionary to modify
            params: Query parameters dictionary to modify
        """
        if not self.auth_config or self.auth_config.type == AuthType.NONE:
            return
            
        # Initialize params if needed
        params_dict = params if params is not None else {}
        
        if self.auth_config.type == AuthType.API_KEY:
            key_name = self.auth_config.key_name or "X-API-Key"
            key_value = self.auth_config.key_value or ""
            
            if self.auth_config.location == AuthLocation.HEADER:
                headers[key_name] = key_value
            else:  # QUERY
                params_dict[key_name] = key_value
                
        elif self.auth_config.type == AuthType.BEARER_TOKEN:
            token = self.auth_config.key_value or ""
            headers["Authorization"] = f"Bearer {token}"
            
        elif self.auth_config.type == AuthType.BASIC_AUTH:
            # Basic auth is handled by httpx, not implemented here
            pass