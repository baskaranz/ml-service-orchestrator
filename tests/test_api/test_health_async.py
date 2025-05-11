"""Async tests for health check API endpoints."""

import asyncio
import platform
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.models import HealthStatus, ComponentHealth, HealthResponse
from app.api.routers.health import get_system_health, get_registry_health, update_overall_status
from app.services.model_registry import ModelRegistryService


@pytest.mark.asyncio
async def test_basic_health_check_async(app):
    """Test the basic health check endpoint asynchronously."""
    # Create a TestClient from the app
    client = TestClient(app)
    
    # Make the request
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_detailed_health_check_async(app, mock_settings):
    """Test the detailed health check endpoint asynchronously."""
    # Create a TestClient from the app
    client = TestClient(app)
    
    # Make the request
    response = client.get("/health/details")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "warning", "error"]
    assert data["version"] == mock_settings.APP_VERSION
    assert "components" in data
    assert "system" in data["components"]
    assert "model_registry" in data["components"]
    
    # Check system health details
    system = data["components"]["system"]
    assert system["status"] in ["ok", "warning", "error"]
    assert "details" in system
    assert "python_version" in system["details"]
    assert "platform" in system["details"]
    
    # Check model registry health details
    registry = data["components"]["model_registry"]
    assert registry["status"] in ["ok", "warning", "error"]
    assert "details" in registry
    assert "model_count" in registry["details"]
    assert "active_models" in registry["details"]


@pytest.mark.asyncio
async def test_detailed_health_check_with_system_error(app, mock_settings):
    """Test detailed health check when system health has an error."""
    # Patch platform.python_version to raise an exception
    original_version = platform.python_version
    
    def mock_raise(*args, **kwargs):
        raise Exception("Test system error")
    
    with patch("platform.python_version", side_effect=mock_raise):
        # Create a TestClient from the app
        client = TestClient(app)
        
        # Make the request
        response = client.get("/health/details")
        
        # Check response - should reflect the error
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"  # Overall status should be error
        
        # Check system component has error
        system = data["components"]["system"]
        assert system["status"] == "error"
        assert "error" in system["details"]
    
    # Restore original function
    platform.python_version = original_version


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
        assert data["status"] == "warning"  # Overall status should be warning
        
        # Check registry component has warning
        registry = data["components"]["model_registry"]
        assert registry["status"] == "warning"
        assert "warning" in registry["details"]
        assert registry["details"]["warning"] in ["No active models", "No models loaded"]
    finally:
        # Reset models to active for other tests
        for model_id, model in mock_model_registry._models.items():
            model.active = True


@pytest.mark.asyncio
async def test_detailed_health_check_with_mock_registry_error(app):
    """Test detailed health check when registry fails to get models."""
    # Create a custom route handler that raises an exception in get_registry_health
    error_health = ComponentHealth(
        status=HealthStatus.ERROR,
        details={"error": "Test registry error"}
    )
    
    with patch("app.api.routers.health.get_registry_health", return_value=error_health):
        # Create a TestClient from the app
        client = TestClient(app)
        
        # Make the request
        response = client.get("/health/details")
        
        # Check response - should reflect the error
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"  # Overall status should be error
        
        # Check registry component has error
        registry = data["components"]["model_registry"]
        assert registry["status"] == "error"
        assert "error" in registry["details"]


def test_get_system_health_with_platform_details():
    """Test get_system_health returns the right platform details."""
    # Patch platform functions to return known values
    with patch.multiple(
        platform,
        python_version=lambda: "3.9.0",
        platform=lambda: "Test Platform",
        machine=lambda: "x86_64"
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