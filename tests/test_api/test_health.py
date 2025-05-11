"""Tests for health check API endpoints."""

import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.models import HealthStatus
from app.api.routers.health import get_system_health, get_registry_health, update_overall_status


def test_basic_health_check(client: TestClient):
    """Test the basic health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_detailed_health_check(client: TestClient, mock_settings):
    """Test the detailed health check endpoint."""
    response = client.get("/health/details")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "warning", "error"]
    assert data["version"] == mock_settings.APP_VERSION
    assert "components" in data
    assert "system" in data["components"]
    assert "model_registry" in data["components"]


def test_get_system_health():
    """Test getting system health information."""
    health = get_system_health()
    
    assert health.status == HealthStatus.OK
    assert "python_version" in health.details
    assert "platform" in health.details


def test_get_system_health_error():
    """Test getting system health information with an error."""
    with patch("platform.python_version", side_effect=Exception("Test error")):
        health = get_system_health()
        
        assert health.status == HealthStatus.ERROR
        assert "error" in health.details


def test_get_registry_health_no_models():
    """Test getting registry health with no models."""
    # Create mock registry with no models
    mock_registry = MagicMock()
    mock_registry.list_models.return_value = []
    
    health = get_registry_health(mock_registry)
    
    assert health.status == HealthStatus.WARNING
    assert health.details["model_count"] == 0
    assert "No models loaded" in health.details["warning"]


def test_get_registry_health_no_active_models():
    """Test getting registry health with no active models."""
    # Create mock registry with inactive models
    mock_registry = MagicMock()
    mock_model = MagicMock()
    mock_model.active = False
    mock_registry.list_models.return_value = [mock_model]
    
    health = get_registry_health(mock_registry)
    
    assert health.status == HealthStatus.WARNING
    assert health.details["model_count"] == 1
    assert health.details["active_models"] == 0
    assert "No active models" in health.details["warning"]


def test_get_registry_health_with_active_models():
    """Test getting registry health with active models."""
    # Create mock registry with active models
    mock_registry = MagicMock()
    mock_model = MagicMock()
    mock_model.active = True
    mock_model.id = "test_model"
    mock_registry.list_models.return_value = [mock_model]
    
    health = get_registry_health(mock_registry)
    
    assert health.status == HealthStatus.OK
    assert health.details["model_count"] == 1
    assert health.details["active_models"] == 1
    assert health.details["models"] == ["test_model"]


def test_get_registry_health_error():
    """Test getting registry health with an error."""
    # Create mock registry that raises an exception
    mock_registry = MagicMock()
    mock_registry.list_models.side_effect = Exception("Test error")
    
    health = get_registry_health(mock_registry)
    
    assert health.status == HealthStatus.ERROR
    assert "error" in health.details


def test_update_overall_status():
    """Test updating the overall health status."""
    # Test that error takes precedence
    assert update_overall_status(HealthStatus.OK, HealthStatus.ERROR) == HealthStatus.ERROR
    assert update_overall_status(HealthStatus.WARNING, HealthStatus.ERROR) == HealthStatus.ERROR
    assert update_overall_status(HealthStatus.ERROR, HealthStatus.OK) == HealthStatus.ERROR
    
    # Test that warning takes precedence over OK
    assert update_overall_status(HealthStatus.OK, HealthStatus.WARNING) == HealthStatus.WARNING
    assert update_overall_status(HealthStatus.WARNING, HealthStatus.OK) == HealthStatus.WARNING
    
    # Test that OK with OK remains OK
    assert update_overall_status(HealthStatus.OK, HealthStatus.OK) == HealthStatus.OK