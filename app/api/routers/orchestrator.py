"""
Orchestrator API routers for proxying requests to model endpoints.
"""

from fastapi import APIRouter, Depends, Request, Response

from app.core.exceptions import ModelRequestError
from app.services.proxy import ProxyService, get_proxy_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["orchestrator"])


@router.api_route(
    "/{model_id}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    summary="Proxy request to model endpoint",
    description="Proxies the request to the specified model endpoint"
)
async def proxy_to_model(
    model_id: str,
    request: Request,
    proxy_service: ProxyService = Depends(get_proxy_service)
) -> Response:
    """
    Proxy a request to a model endpoint.
    
    Args:
        model_id: Model ID to route to
        request: Original FastAPI request
        proxy_service: Proxy service for forwarding requests
        
    Returns:
        Response from the model endpoint
    """
    return await proxy_service.proxy_to_model(model_id, request)


@router.api_route(
    "/{model_id}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    summary="Proxy request to model endpoint with path",
    description="Proxies the request to the specified model endpoint with an additional path"
)
async def proxy_to_model_with_path(
    model_id: str,
    path: str,
    request: Request,
    proxy_service: ProxyService = Depends(get_proxy_service)
) -> Response:
    """
    Proxy a request to a model endpoint with additional path.
    
    Args:
        model_id: Model ID to route to
        path: Additional path to append to the model endpoint URL
        request: Original FastAPI request
        proxy_service: Proxy service for forwarding requests
        
    Returns:
        Response from the model endpoint
    """
    return await proxy_service.proxy_to_model(model_id, request, path)