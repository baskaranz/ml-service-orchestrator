"""
API routers package.
"""

from fastapi import APIRouter

from app.api.routers import admin, health, orchestrator
from app.config.settings import settings

# Create the main API router
api_router = APIRouter()

# Include health routers
api_router.include_router(health.router)

# Include orchestrator routers
api_router.include_router(
    orchestrator.router, 
    prefix="/orchestrator"
)

# Include admin routers if enabled
if settings.ADMIN_API_ENABLED:
    api_router.include_router(admin.router)