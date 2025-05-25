"""
API routers package.
"""

from fastapi import APIRouter

from app.api.routers import admin, health, models, orchestrator
from app.config.settings import settings

# Create the main API router
api_router = APIRouter()

# Include health router under /api/v1/health
api_router.include_router(health.router, prefix="/api/v1/health", tags=["health"])

# Include models router under /api/v1/models
api_router.include_router(models.router, prefix="/api/v1/models", tags=["models"])

# Include orchestrator routers under /api/v1/orchestrator for better versioning
api_router.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["orchestrator"])

# Include admin routers if enabled
if settings.ADMIN_API_ENABLED:
    api_router.include_router(admin.router, prefix="/admin")
