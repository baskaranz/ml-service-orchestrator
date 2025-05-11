"""Tests for API routers."""

from unittest.mock import patch, MagicMock, AsyncMock
import json

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from app.core.models import ModelSummary


def test_health_endpoint(client: TestClient):
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@patch("app.services.proxy.ProxyService.proxy_to_model")
def test_orchestrator_endpoint(mock_proxy, client: TestClient):
    """Test the orchestrator endpoint."""
    # Configure mock to return a proper FastAPI Response
    mock_response = Response(
        content=json.dumps({"result": "success"}),
        status_code=200,
        media_type="application/json"
    )
    mock_proxy.return_value = mock_response
    
    # Make request to orchestrator
    response = client.get("/orchestrator/test_model_1")
    
    # Verify response
    assert response.status_code == 200
    # Access the response content as text and parse it
    assert response.json() == {"result": "success"}


@patch("app.services.model_registry.ModelRegistryService.list_models")
def test_admin_list_models(mock_list_models, client: TestClient):
    """Test listing models in admin API."""
    # Set up mock API key in request header
    headers = {"X-API-Key": "test-admin-key"}
    
    # Create proper ModelSummary instances
    model_1 = ModelSummary(id="model_1", name="Model 1", description="desc", version="1.0.0", active=True)
    model_2 = ModelSummary(id="model_2", name="Model 2", description="desc", version="1.0.0", active=False)
    
    # Configure mock to return the list of ModelSummary instances
    mock_list_models.return_value = [model_1, model_2]
    
    # Make request
    response = client.get("/admin/models", headers=headers)
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert data["count"] == 2
    assert data["models"][0]["id"] == "model_1"
    assert data["models"][1]["id"] == "model_2"


@patch("app.services.model_registry.ModelRegistryService.reload_configs")
def test_admin_reload_configs(mock_reload, client: TestClient):
    """Test reloading configurations in admin API."""
    # Set up mock API key in request header
    headers = {"X-API-Key": "test-admin-key"}
    
    # Configure mock
    mock_reload.return_value = {"model_1": MagicMock(), "model_2": MagicMock()}
    
    # Make request
    response = client.post("/admin/reload", headers=headers)
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "message" in data
    
    # Verify mock was called
    mock_reload.assert_called_once()