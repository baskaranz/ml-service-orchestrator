from typing import Optional
from pydantic import BaseModel, Field

class AuthConfig(BaseModel):
    """Authentication configuration."""
    enabled: bool = Field(default=False, description="Whether authentication is enabled")
    type: str = Field(default="api_key", description="Authentication type (api_key, bearer, basic)")
    header_name: Optional[str] = Field(default=None, description="Header name for API key")
    query_param: Optional[str] = Field(default=None, description="Query parameter name for API key")
    value: Optional[str] = Field(default=None, description="Authentication value (API key, token, etc.)") 