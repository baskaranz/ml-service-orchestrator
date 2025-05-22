"""
Health API routers for system and registry health endpoints.
"""

import platform

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.orchestrator import get_orchestrator_async as get_orchestrator
from app.config.settings import settings
from app.core.exceptions import ModelNotFoundError
from app.schemas.api_models import ComponentHealth, HealthResponse, HealthStatus, ModelSummary
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Returns the basic health status of the service",
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    This endpoint provides a basic health check of the service.
    For a more detailed health check, use /health/detailed

    Returns:
        Health status response
    """
    try:
        # Get the orchestrator instance asynchronously
        orchestrator = await get_orchestrator()
        logger.info(f"Health check endpoint using orchestrator instance {id(orchestrator)}")

        # Gather active models from orchestrator
        models = []
        if hasattr(orchestrator, "_models") and orchestrator._models:
            models = [
                ModelSummary(id=m.id, name=m.name, active=m.active)
                for m in orchestrator._models.values()
                if hasattr(m, "active") and hasattr(m, "id") and hasattr(m, "name") and m.active
            ]
        else:
            logger.warning("No models found in orchestrator")

        # Always return OK status for basic health check
        return HealthResponse(
            status=HealthStatus.OK, version=settings.APP_VERSION, models=models, components={}
        )
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}", exc_info=True)
        return HealthResponse(
            status=HealthStatus.ERROR,
            version=settings.APP_VERSION,
            models=[],
            components={"error": str(e)},
        )


@router.get(
    "/health/details",
    response_model=HealthResponse,
    summary="Detailed health check",
    description="Returns detailed health information for all components",
)
async def detailed_health_check(
    model_registry: ModelRegistryService = Depends(get_model_registry_service),
) -> HealthResponse:
    """
    Detailed health check endpoint.

    Args:
        model_registry: Model registry service

    Returns:
        Detailed health status response
    """
    # Gather model summaries
    models = model_registry.list_models()
    model_summaries = [
        ModelSummary(id=model.id, name=model.name, active=model.active) for model in models
    ]

    # Get component health
    components = {}
    overall_status = HealthStatus.OK

    # Check system health
    system_health = get_system_health()
    components["system"] = system_health
    overall_status = update_overall_status(overall_status, system_health.status)

    # Check model registry health
    registry_health = get_registry_health(model_registry)
    components["model_registry"] = registry_health
    overall_status = update_overall_status(overall_status, registry_health.status)

    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        models=model_summaries,
        components=components,
    )


@router.get(
    "/health/models/{model_id}",
    response_model=HealthResponse,
    summary="Model health check",
    description="Returns the health status of a specific model",
)
async def model_health_check(
    model_id: str, model_registry: ModelRegistryService = Depends(get_model_registry_service)
) -> HealthResponse:
    """
    Get the health status of a specific model.

    Args:
        model_id: ID of the model to check
        model_registry: Model registry service

    Returns:
        Health status response for the model

    Raises:
        HTTPException: If the model is not found
    """
    try:
        # Get the model from the registry
        model = model_registry.get_model(model_id)

        # Create a simple health response for the model
        return HealthResponse(
            status=HealthStatus.OK if model.active else HealthStatus.UNHEALTHY,
            version=settings.APP_VERSION,
            models=[ModelSummary(id=model.id, name=model.name, active=model.active)],
            components={
                "model": ComponentHealth(
                    status=HealthStatus.OK if model.active else HealthStatus.UNHEALTHY,
                    details={
                        "id": model.id,
                        "name": model.name,
                        "active": model.active,
                        "endpoint_url": model.endpoint_url,
                    },
                )
            },
        )
    except ModelNotFoundError:
        logger.warning(f"Model not found: {model_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Model {model_id} not found"
        )


def get_system_health() -> ComponentHealth:
    """
    Get system health information.

    Returns:
        System health component
    """
    try:
        details = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": platform.machine(),
        }
        return ComponentHealth(status=HealthStatus.OK, details=details)
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}", exc_info=True)
        return ComponentHealth(status=HealthStatus.ERROR, details={"error": str(e)})


def get_registry_health(model_registry: ModelRegistryService) -> ComponentHealth:
    """
    Get model registry health information.

    Args:
        model_registry: Model registry service

    Returns:
        Model registry health component
    """
    try:
        models = model_registry.list_models()
        active_models = [model for model in models if model.active]

        # Warning if no models are loaded
        if not models:
            return ComponentHealth(
                status=HealthStatus.WARNING,
                details={"model_count": 0, "active_models": 0, "warning": "No models loaded"},
            )

        # Warning if no active models
        if not active_models:
            return ComponentHealth(
                status=HealthStatus.WARNING,
                details={
                    "model_count": len(models),
                    "active_models": 0,
                    "warning": "No active models",
                },
            )

        return ComponentHealth(
            status=HealthStatus.OK,
            details={
                "model_count": len(models),
                "active_models": len(active_models),
                "models": [model.id for model in models],
            },
        )
    except Exception as e:
        logger.error(f"Error getting registry health: {str(e)}", exc_info=True)
        return ComponentHealth(status=HealthStatus.ERROR, details={"error": str(e)})


def ensure_details_dict(health: ComponentHealth) -> ComponentHealth:
    if health.details is None:
        health.details = {}
    return health


def patched_get_system_health() -> ComponentHealth:
    return ensure_details_dict(get_system_health())


def patched_get_registry_health(model_registry: ModelRegistryService) -> ComponentHealth:
    return ensure_details_dict(get_registry_health(model_registry))


def update_overall_status(current: HealthStatus, new: HealthStatus) -> HealthStatus:
    """
    Update the overall health status based on component status.

    Args:
        current: Current overall status
        new: New component status

    Returns:
        Updated overall status
    """
    # Error takes precedence over warning, which takes precedence over OK
    if current == HealthStatus.ERROR or new == HealthStatus.ERROR:
        return HealthStatus.ERROR
    elif current == HealthStatus.WARNING or new == HealthStatus.WARNING:
        return HealthStatus.WARNING
    else:
        return HealthStatus.OK
