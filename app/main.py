"""
Main FastAPI application entry point.
"""

import time
import sys
import argparse
from typing import Dict
from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, start_http_server, CollectorRegistry
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routers import api_router
from app.config.settings import settings
from app.core.exceptions import setup_exception_handlers
from app.utils.logging import get_logger, setup_logging
from app.config.models_config import ModelConfigManager
from app.api.routers.orchestrator import _orchestrator

logging.basicConfig(level=logging.DEBUG)

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting request metrics.
    """
    
    def __init__(self, app, request_count, request_time):
        super().__init__(app)
        self.request_count = request_count
        self.request_time = request_time
    
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
        self.request_count.labels(path=path, method=request.method, status=status_code).inc()
        
        # Record request time
        self.request_time.labels(path=path, method=request.method).observe(duration)
        
        return response


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    
    print("Creating FastAPI application...", file=sys.stderr)
    
    # Set up logging with DEBUG level
    setup_logging(level=logging.DEBUG)
    
    # Create a new registry for metrics to avoid duplicates
    registry = CollectorRegistry()
    
    # Metrics
    request_count = Counter(
        "orchestrator_request_count", 
        "Total count of requests by path and method",
        ["path", "method", "status"],
        registry=registry
    )

    request_time = Histogram(
        "orchestrator_request_processing_seconds",
        "Time spent processing requests",
        ["path", "method"],
        registry=registry
    )
    
    from app.services.model_registry import ModelRegistryService

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print("Lifespan context manager - startup", file=sys.stderr)
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        # Start metrics server if enabled
        if settings.METRICS_ENABLED:
            start_http_server(9090, registry=registry)
            logger.info("Metrics server started on port 9090")
        # Set up model registry service
        model_registry_service = ModelRegistryService()
        # Create config manager for registry if needed
        if hasattr(model_registry_service, 'config_manager') and model_registry_service.config_manager is None:
            model_registry_service.config_manager = ModelConfigManager(
                settings.MODELS_DIR
            )
        await model_registry_service.startup()
        # Initialize orchestrator error handlers
        await _orchestrator.initialize_error_handlers()
        try:
            yield
        finally:
            print("Lifespan context manager - shutdown", file=sys.stderr)
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
    
    print("Configuring middleware...", file=sys.stderr)
    
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
        app.add_middleware(MetricsMiddleware, request_count=request_count, request_time=request_time)
    
    # Set up exception handlers
    setup_exception_handlers(app)
    
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
    
    print("Application created successfully", file=sys.stderr)
    return app


# Create the application instance
print("Starting app/main.py...", file=sys.stderr)
app = create_app()
print("Main application instance created, app variable set", file=sys.stderr)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the FastAPI application server")
    parser.add_argument("--host", default=settings.HOST, help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to bind the server to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--workers", type=int, default=settings.WORKERS, help="Number of worker processes")
    
    args = parser.parse_args()
    
    # Override settings if provided from command line
    if args.debug:
        settings.DEBUG = True
    
    # Run the server
    print(f"Starting server at {args.host}:{args.port}", file=sys.stderr)
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        log_level="debug" if settings.DEBUG else "info",
        workers=args.workers,
        reload=settings.DEBUG
    )