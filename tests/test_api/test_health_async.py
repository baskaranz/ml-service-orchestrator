"""
Tests for health check endpoints using async client.
"""

import platform
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.routers.health import get_registry_health, get_system_health, update_overall_status
from app.schemas.api_models import ComponentHealth, HealthStatus
from app.services.model_registry import ModelRegistryService


@pytest.fixture
def mock_model_registry():
    """Create a mock model registry with test models."""
    registry = ModelRegistryService()
    # Add some test models
    registry._models = {
        "test_model_1": MagicMock(
            id="test_model_1",
            name="Test Model 1",
            description="Test model 1",
            version="1.0.0",
            active=True,
        ),
        "test_model_2": MagicMock(
            id="test_model_2",
            name="Test Model 2",
            description="Test model 2",
            version="1.0.0",
            active=True,
        ),
    }
    return registry


@pytest.mark.asyncio
async def test_basic_health_check_async(app):
    """Test the basic health check endpoint asynchronously."""
    client = TestClient(app)
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert "version" in data
    assert "models" in data
    assert "components" in data


@pytest.mark.asyncio
async def test_detailed_health_check_async(app, mock_settings):
    """Test the detailed health check endpoint asynchronously."""
    # Create a mock registry health response
    from app.schemas.api_models import ComponentHealth, HealthStatus

    mock_registry_health = ComponentHealth(
        status=HealthStatus.OK, details={"models": ["test_model_1"]}
    )

    # Patch the get_registry_health function to return our mock
    with patch("app.api.routers.health.get_registry_health") as mock_get_registry_health:
        mock_get_registry_health.return_value = mock_registry_health

        # Create a TestClient and make the request
        client = TestClient(app)
        response = client.get("/api/v1/health/details")

        # Verify the response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["OK", "WARNING", "ERROR"]
        assert data["version"] == mock_settings.APP_VERSION
        assert "models" in data
        assert "components" in data
        assert "model_registry" in data["components"]
        assert data["components"]["model_registry"]["status"] == "OK"


@pytest.mark.asyncio
async def test_detailed_health_check_with_system_error(app, mock_settings):
    """Test detailed health check when system health has an error."""

    def mock_raise(*args, **kwargs):
        raise Exception("Test system error")

    with patch("platform.python_version", side_effect=mock_raise):
        client = TestClient(app)
        response = client.get("/api/v1/health/details")
        assert response.status_code == 200
        data = response.json()
        # Should reflect an ERROR status if system health fails
        assert data["status"] == "ERROR"

        # Check system component has error
        components = data.get("components", {})
        assert isinstance(components, dict)
        system = components.get("system", {})
        assert isinstance(system, dict)
        assert system["status"] == "ERROR"
        details = system.get("details", {})
        assert isinstance(details, dict)
        assert "error" in details


@pytest.mark.asyncio
async def test_detailed_health_check_with_warning(app, mock_model_registry):
    """Test detailed health check when registry has warning due to inactive models."""
    # Make all models inactive
    for model_id, model in mock_model_registry._models.items():
        model.active = False

    try:
        # Create a TestClient from the app
        client = TestClient(app)

        # Make the request
        response = client.get("/api/v1/health/details")

        # Check response - should reflect the warning
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert data["status"] == "WARNING"  # Overall status should be warning

        # Check registry component has warning
        components = data.get("components", {})
        assert isinstance(components, dict)
        registry = components.get("model_registry", {})
        assert isinstance(registry, dict)
        assert registry["status"] == "WARNING"
        details = registry.get("details", {})
        assert isinstance(details, dict)
        assert "warning" in details
        assert details["warning"] in ["No active models", "No models loaded"]
    finally:
        # Reset models to active for other tests
        for model_id, model in mock_model_registry._models.items():
            model.active = True


def test_get_system_health_with_platform_details():
    """Test get_system_health returns the right platform details."""
    # Patch platform functions to return known values
    with patch.multiple(
        platform,
        python_version=lambda: "3.9.0",
        platform=lambda: "Test Platform",
        machine=lambda: "x86_64",
    ):
        health = get_system_health()

        assert health.status == HealthStatus.OK
        assert health.details["python_version"] == "3.9.0"
        assert health.details["platform"] == "Test Platform"
        assert health.details["cpu_count"] == "x86_64"


def test_get_registry_health_with_mock_registry(mock_model_registry):
    """Test get_registry_health with the mock registry."""
    # Mock list_models method
    mock_model_1 = MagicMock()
    mock_model_1.id = "test_model_1"
    mock_model_1.active = True

    mock_model_2 = MagicMock()
    mock_model_2.id = "test_model_2"
    mock_model_2.active = True

    mock_model_registry.list_models = MagicMock(return_value=[mock_model_1, mock_model_2])

    # Get health
    health = get_registry_health(mock_model_registry)

    # Verify OK status
    assert health.status == HealthStatus.OK
