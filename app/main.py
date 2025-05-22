"""
Main FastAPI application entry point.
"""

import argparse
import logging
import os
import pathlib
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import api_router
from app.config.models_config import ModelConfigManager
from app.config.settings import settings
from app.core.exceptions import setup_exception_handlers

# Import the Orchestrator class for type hints
from app.services.orchestrator import Orchestrator
from app.utils.logging import get_logger, setup_logging

# Global orchestrator instance
_orchestrator = None

# Set up logging
logging.basicConfig(level=logging.DEBUG)

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """

    print("Creating FastAPI application...", file=sys.stderr)

    # Set up logging with DEBUG level
    setup_logging(level=logging.DEBUG)

    from app.services.model_registry import ModelRegistryService

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print("Lifespan context manager - startup", file=sys.stderr)
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

        # Define the models directory path based on the environment
        models_dir = pathlib.Path("/app/config/local/models")

        # Ensure the directory exists
        if not models_dir.exists():
            logger.warning(f"Models directory does not exist, creating: {models_dir}")
            try:
                models_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created models directory: {models_dir}")
            except Exception as e:
                logger.error(f"Failed to create models directory: {e}")

        # Verify the directory exists and is accessible
        if not models_dir.exists() or not models_dir.is_dir():
            logger.error(f"Models directory is not accessible: {models_dir}")
        else:
            logger.info(f"Using models directory: {models_dir}")
            # List the contents of the directory for debugging
            try:
                files = [f.name for f in models_dir.iterdir() if f.is_file()]
                yaml_files = [f for f in files if f.endswith((".yaml", ".yml"))]
                logger.info(f"Found {len(yaml_files)} YAML files in {models_dir}")
                if yaml_files:
                    logger.info(f"YAML files: {yaml_files}")
            except Exception as e:
                logger.error(f"Error listing contents of {models_dir}: {e}")

        # Set the models directory in settings and environment
        settings.MODELS_DIR = str(models_dir)
        os.environ["MODELS_DIR"] = str(models_dir)

        # Log the final configuration
        logger.info(f"Configuration - MODELS_DIR: {settings.MODELS_DIR}")
        logger.info(f"Environment - MODELS_DIR: {os.getenv('MODELS_DIR')}")

        # Set up model registry service
        model_registry_service = ModelRegistryService()
        # Create config manager for registry if needed
        if (
            hasattr(model_registry_service, "config_manager")
            and model_registry_service.config_manager is None
        ):
            model_registry_service.config_manager = ModelConfigManager(settings.MODELS_DIR)
        await model_registry_service.startup()

        # Ensure the directory exists
        if not models_dir.exists():
            logger.warning(f"Models directory does not exist, creating: {models_dir}")
            try:
                models_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created models directory: {models_dir}")
            except Exception as e:
                logger.error(f"Failed to create models directory: {e}")

        # Verify the directory exists and is accessible
        if not models_dir.exists() or not models_dir.is_dir():
            logger.error(f"Models directory is not accessible: {models_dir}")
        else:
            logger.info(f"Using models directory: {models_dir}")
            # List the contents of the directory for debugging
            try:
                files = [f.name for f in models_dir.iterdir() if f.is_file()]
                yaml_files = [f for f in files if f.endswith((".yaml", ".yml"))]
                logger.info(f"Found {len(yaml_files)} YAML files in {models_dir}")
                if yaml_files:
                    logger.info(f"YAML files: {yaml_files}")
            except Exception as e:
                logger.error(f"Error listing contents of {models_dir}: {e}")

        # Set the models directory in settings and environment
        settings.MODELS_DIR = str(models_dir)
        os.environ["MODELS_DIR"] = str(models_dir)

        # Log the final configuration
        logger.info(f"Configuration - MODELS_DIR: {settings.MODELS_DIR}")
        logger.info(f"Environment - MODELS_DIR: {os.getenv('MODELS_DIR')}")

        # Initialize the orchestrator with the correct config directory
        global _orchestrator
        _orchestrator = Orchestrator(config_dir=str(models_dir))
        await _orchestrator.startup()

        # Initialize the orchestrator
        try:

            from app.api.routers.orchestrator import get_orchestrator
            from app.config.models_config import ModelConfigManager

            logger.info("Initializing orchestrator...")
            _orchestrator = await get_orchestrator()

            # Update the router's orchestrator instance
            from app.api.routers.orchestrator import router as orchestrator_router

            orchestrator_router._orchestrator = _orchestrator

            # Debug: List all files in the models directory
            try:
                logger.info(f"Contents of {models_dir}:")
                if models_dir.exists():
                    for f in models_dir.glob("**/*"):
                        logger.info(f"  - {f.relative_to(models_dir)}")
                else:
                    logger.error(f"Models directory does not exist: {models_dir}")
            except Exception as e:
                logger.error(f"Error listing models directory: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise

            # Initialize the ModelConfigManager with the config directory
            config_manager = ModelConfigManager(config_dir=str(settings.BASE_DIR / "config"))

            # Load configurations
            _, loaded_models = await config_manager.load_configs()

            if loaded_models:
                logger.info(f"Successfully loaded {len(loaded_models)} models from configuration")

                # Convert loaded models to ModelConfig objects and add to orchestrator
                for model_id, model_config in loaded_models.items():
                    # Ensure the model is active
                    if not hasattr(model_config, "active") or model_config.active:
                        _orchestrator._models[model_id] = model_config
                        logger.info(
                            f"Added model to orchestrator: {model_id} (active: {getattr(model_config, 'active', True)})"
                        )
                    else:
                        logger.info(f"Skipping inactive model: {model_id}")

                logger.info(f"Total models loaded into orchestrator: {len(_orchestrator.models)}")
            else:
                logger.warning("No models found in configuration")

        except Exception as e:
            logger.error(f"Error loading models from config: {str(e)}")
            logger.exception("Detailed error:")

        # Log all loaded models
        if _orchestrator.models:
            logger.info(
                f"Successfully loaded {len(_orchestrator.models)} active models: {list(_orchestrator.models.keys())}"
            )
            for model_id, model in _orchestrator.models.items():
                logger.info(f"  - Model: {model_id}")
                logger.info(f"    Active: {getattr(model, 'active', False)}")
                logger.info(f"    Endpoint: {getattr(model, 'endpoint_url', 'N/A')}")
        else:
            logger.error(
                "No models were loaded into the orchestrator. Check configuration files and logs for errors."
            )

        # Verify models are properly set
        logger.info(f"Final _orchestrator.models: {_orchestrator.models}")

        # Initialize error handlers
        await _orchestrator.initialize_error_handlers()
        logger.info("Orchestrator initialization complete")
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

    # Set up exception handlers
    setup_exception_handlers(app)

    # Include API routes
    app.include_router(api_router)

    return app


# Create the application instance
print("Starting app/main.py...", file=sys.stderr)
app = create_app()
print("Main application instance created, app variable set", file=sys.stderr)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the FastAPI application server")
    parser.add_argument("--host", default=settings.HOST, help="Host to bind the server to")
    parser.add_argument(
        "--port", type=int, default=settings.PORT, help="Port to bind the server to"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--workers", type=int, default=settings.WORKERS, help="Number of worker processes"
    )

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
        reload=settings.DEBUG,
    )
