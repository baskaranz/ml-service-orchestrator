"""
Main FastAPI application entry point.
"""

import time
from typing import Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, start_http_server
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routers import api_router
from app.config.settings import settings
from app.core.exceptions import setup_exception_handlers
from app.services.model_registry import setup_model_registry
from app.utils.logging import get_logger
from app.config.models_config import ModelConfigManager

logger = get_logger(__name__)

# Metrics
REQUEST_COUNT = Counter(
    "orchestrator_request_count", 
    "Total count of requests by path and method",
    ["path", "method", "status"]
)

REQUEST_TIME = Histogram(
    "orchestrator_request_processing_seconds",
    "Time spent processing requests",
    ["path", "method"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting request metrics.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Start timer
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        status_code = response.status_code
        
        # Extract path pattern from router if possible
        path = request.url.path
        
        # Record request count by path, method, and status
        REQUEST_COUNT.labels(path=path, method=request.method, status=status_code).inc()
        
        # Record request time
        REQUEST_TIME.labels(path=path, method=request.method).observe(duration)
        
        return response


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    
    from app.services.model_registry import ModelRegistryService

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        # Start metrics server if enabled
        if settings.METRICS_ENABLED:
            start_http_server(9090)
            logger.info("Metrics server started on port 9090")
        # Set up model registry service
        model_registry_service = ModelRegistryService(
            ModelConfigManager(settings.CONFIG_DIR, settings.MODELS_REGISTRY_FILE)
        )
        await model_registry_service.startup()
        try:
            yield
        finally:
            logger.info(f"Shutting down {settings.APP_NAME}")
            await model_registry_service.shutdown()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add metrics middleware if enabled
    if settings.METRICS_ENABLED:
        app.add_middleware(MetricsMiddleware)
    
    # Set up exception handlers
    setup_exception_handlers(app)
    
    # Set up model registry
    setup_model_registry(app)
    
    # Include API routes
    app.include_router(api_router)
    
    # Add root path handler
    @app.get("/", tags=["root"])
    async def root() -> Dict[str, str]:
        """Root path handler."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running"
        }
    
    return app


# Create the application instance
app = create_app()