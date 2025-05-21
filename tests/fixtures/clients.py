"""API client fixtures for testing the ML Service Orchestrator."""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import create_app


@pytest.fixture(scope="module")
def app():
    """Create a test FastAPI app instance with admin API enabled.
    
    Returns:
        A configured FastAPI application for testing
    """
    # Import settings and enable admin API
    from app.config import settings

    # Configure test-specific settings
    settings.ADMIN_API_ENABLED = True
    settings.ADMIN_API_KEY = "test-admin-key"
    
    # Create the test app
    test_app = create_app()
    
    # Create a new router for admin endpoints without the prefix
    from fastapi import APIRouter
    from app.api.routers.admin import router as admin_router

    # Copy all routes from the original admin router but without the prefix
    test_admin_router = APIRouter()
    for route in admin_router.routes:
        test_admin_router.routes.append(route)

    # Include the test admin router without the prefix
    test_app.include_router(
        test_admin_router, prefix=""  # No prefix for easier testing
    )
    
    # Only print routes in debug mode
    if settings.DEBUG:
        print("\nRegistered routes:")
        for route in test_app.routes:
            if hasattr(route, "path"):
                methods = ", ".join(route.methods) if hasattr(route, "methods") else "N/A"
                print(f"- {route.path} ({methods})")

    return test_app


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for synchronous API testing.
    
    Args:
        app: The FastAPI application fixture
        
    Returns:
        A TestClient instance for making synchronous requests
    """
    return TestClient(app)


@pytest_asyncio.fixture(scope="function")
async def async_client(app):
    """Create an async test client for asynchronous API testing.
    
    Args:
        app: The FastAPI application fixture
        
    Yields:
        An AsyncClient instance for making asynchronous requests
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def admin_headers():
    """Create headers with admin API key for authenticated requests.
    
    Returns:
        A dictionary with the admin API key header
    """
    from app.config import settings
    
    return {"X-API-Key": settings.ADMIN_API_KEY}
