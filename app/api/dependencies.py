"""
FastAPI dependencies for the API.
"""

from typing import Optional
from pathlib import Path

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config.settings import settings
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

# API key security scheme for admin endpoints
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    Validate the API key for admin endpoints.
    
    Args:
        api_key: API key from request header
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If the API key is invalid
    """
    # Skip validation if admin API key is not configured
    if not settings.ADMIN_API_KEY:
        return ""
    
    # Check if the provided API key matches the configured key
    if api_key == settings.ADMIN_API_KEY:
        return api_key
    
    # Invalid API key
    logger.warning("Invalid API key attempt")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key"
    )


# Use the service singleton from model_registry.py
def get_model_registry() -> ModelRegistryService:
    """
    Get the singleton instance of ModelRegistryService.
    
    Returns:
        ModelRegistryService: The singleton instance of ModelRegistryService
    """
    return get_model_registry_service()