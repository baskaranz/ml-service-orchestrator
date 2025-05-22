"""
Tests for health check endpoints using async client.
"""

import platform
from unittest.mock import MagicMock, patch

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
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert "version" in data
    assert "models" in data
    assert "components" in data


@pytest.mark.asyncio
@patch("app.services.model_registry.ModelRegistryService.list_models", new_callable=MagicMock)
async def test_detailed_health_check_async(mock_list_models, app, mock_settings):
    """Test the detailed health check endpoint asynchronously."""
    # Return a list of mock models
    mock_model = MagicMock()
    mock_model.id = "test_model_1"
    mock_model.name = "Test Model 1"
    mock_model.active = True
    mock_list_models.return_value = [mock_model]
    client = TestClient(app)
    response = client.get("/health/details")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["OK", "WARNING", "ERROR"]
    assert data["version"] == mock_settings.APP_VERSION
    assert "models" in data
    assert "components" in data


@pytest.mark.asyncio
async def test_detailed_health_check_with_system_error(app, mock_settings):
    """Test detailed health check when system health has an error."""

    def mock_raise(*args, **kwargs):
        raise Exception("Test system error")

    with patch("platform.python_version", side_effect=mock_raise):
        client = TestClient(app)
        response = client.get("/health/details")
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
        response = client.get("/health/details")

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


@pytest.mark.asyncio
async def test_detailed_health_check_with_mock_registry_error(app):
    """Test detailed health check when registry fails to get models."""
    # Create a custom route handler that raises an exception in get_registry_health
    error_health = ComponentHealth(
        status=HealthStatus.ERROR, details={"error": "Test registry error"}
    )

    with patch("app.api.routers.health.get_registry_health", return_value=error_health):
        # Create a TestClient from the app
        client = TestClient(app)

        # Make the request
        response = client.get("/health/details")

        # Check response - should reflect the error
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert data["status"] == "ERROR"  # Overall status should be error

        # Check registry component has error
        components = data.get("components", {})
        assert isinstance(components, dict)
        registry = components.get("model_registry", {})
        assert isinstance(registry, dict)
        assert registry["status"] == "ERROR"
        details = registry.get("details", {})
        assert isinstance(details, dict)
        assert "error" in details


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
    assert health.details["model_count"] == 2
    assert health.details["active_models"] == 2
    assert "test_model_1" in health.details["models"]
    assert "test_model_2" in health.details["models"]


def test_get_registry_health_no_models():
    """Test get_registry_health with no models."""
    # Create empty registry
    registry = MagicMock(spec=ModelRegistryService)
    registry.list_models.return_value = []

    # Get health
    health = get_registry_health(registry)

    # Verify warning status
    assert health.status == HealthStatus.WARNING
    assert health.details["model_count"] == 0
    assert health.details["active_models"] == 0
    assert "warning" in health.details
    assert health.details["warning"] == "No models loaded"


def test_get_registry_health_inactive_models():
    """Test get_registry_health with inactive models only."""
    # Create registry mock with only inactive models
    registry = MagicMock(spec=ModelRegistryService)

    inactive_model1 = MagicMock()
    inactive_model1.id = "inactive_model1"
    inactive_model1.active = False

    inactive_model2 = MagicMock()
    inactive_model2.id = "inactive_model2"
    inactive_model2.active = False

    registry.list_models.return_value = [inactive_model1, inactive_model2]

    # Get health
    health = get_registry_health(registry)

    # Verify warning status
    assert health.status == HealthStatus.WARNING
    assert health.details["model_count"] == 2
    assert health.details["active_models"] == 0
    assert "warning" in health.details
    assert "No active models" in health.details["warning"]


def test_get_registry_health_error():
    """Test get_registry_health with an error."""
    # Create registry mock that raises an exception
    registry = MagicMock(spec=ModelRegistryService)
    registry.list_models.side_effect = Exception("Test registry error")

    # Get health
    health = get_registry_health(registry)

    # Verify error status
    assert health.status == HealthStatus.ERROR
    assert "error" in health.details
    assert "Test registry error" in health.details["error"]


def test_update_overall_status_combinations():
    """Test all combinations of update_overall_status."""
    # Error takes precedence over all other statuses
    assert update_overall_status(HealthStatus.OK, HealthStatus.ERROR) == HealthStatus.ERROR
    assert update_overall_status(HealthStatus.WARNING, HealthStatus.ERROR) == HealthStatus.ERROR
    assert update_overall_status(HealthStatus.ERROR, HealthStatus.OK) == HealthStatus.ERROR
    assert update_overall_status(HealthStatus.ERROR, HealthStatus.WARNING) == HealthStatus.ERROR
    assert update_overall_status(HealthStatus.ERROR, HealthStatus.ERROR) == HealthStatus.ERROR

    # Warning takes precedence over OK
    assert update_overall_status(HealthStatus.OK, HealthStatus.WARNING) == HealthStatus.WARNING
    assert update_overall_status(HealthStatus.WARNING, HealthStatus.OK) == HealthStatus.WARNING
    assert update_overall_status(HealthStatus.WARNING, HealthStatus.WARNING) == HealthStatus.WARNING

    # OK only when both are OK
    assert update_overall_status(HealthStatus.OK, HealthStatus.OK) == HealthStatus.OK
