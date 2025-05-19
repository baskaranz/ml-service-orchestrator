"""Tests for admin API routers."""

import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from httpx import AsyncClient

from app.config.settings import settings
from app.models.config_models import ModelConfig
from app.schemas.api_models import ModelSummary


@pytest.fixture
def setup_api_key(mock_settings):
    """Set up a test API key for admin endpoints."""
    original_api_key = mock_settings.ADMIN_API_KEY
    mock_settings.ADMIN_API_KEY = "test-admin-key"
    yield
    mock_settings.ADMIN_API_KEY = original_api_key


def test_admin_unauthorized(client: TestClient):
    """Test that accessing admin endpoints without API key fails."""
    response = client.get("/admin/models")
    assert response.status_code == 403
    data = response.json()
    assert "error" in data
    assert "invalid" in data["error"].lower() or "unauthorized" in data["error"].lower()


@patch("app.services.model_registry.ModelRegistryService")
def test_admin_list_models(MockModelRegistry, client: TestClient, setup_api_key):
    """Test listing models with valid API key."""
    # Setup mock to return list of models
    mock_registry = MockModelRegistry.return_value
    mock_models = [
        ModelConfig(
            id="test_model_1", 
            name="Test Model 1", 
            endpoint_url="http://test1.com",
            active=True
        ),
        ModelConfig(
            id="test_model_2", 
            name="Test Model 2",
            endpoint_url="http://test2.com",
            active=True
        )
    ]
    mock_registry.list_models.return_value = mock_models
    
    response = client.get(
        "/admin/models", 
        headers={"X-API-Key": "test-admin-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert data["count"] == 2
    assert len(data["models"]) == 2
    # Check that the response contains the expected model IDs
    model_ids = [model["id"] for model in data["models"]]
    assert "test_model_1" in model_ids
    assert "test_model_2" in model_ids


@patch("app.services.model_registry.ModelRegistryService.get_model_config")
def test_admin_get_model(mock_get_model, client: TestClient, setup_api_key, model_config_instance, llm_provider_config):
    """Test getting a specific model."""
    # Setup mock to return a model
    mock_get_model.return_value = model_config_instance
    
    response = client.get(
        "/admin/models/test_model_1",
        headers={"X-API-Key": "test-admin-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test_model_1"
    assert data["name"] == "Test Model"
    assert data["endpoint_url"] == "http://localhost:8888/predict"


@patch("app.services.model_registry.ModelRegistryService.get_model_config")
def test_admin_get_model_not_found(mock_get_model, client: TestClient, setup_api_key):
    """Test getting a model that doesn't exist."""
    # Setup mock to raise a KeyError for non-existent model
    mock_get_model.side_effect = KeyError("Model not found")
    
    response = client.get(
        "/admin/models/nonexistent_model",
        headers={"X-API-Key": "test-admin-key"}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "not found" in data["error"].lower()


@patch("app.services.model_registry.ModelRegistryService.add_model", new_callable=AsyncMock)
def test_admin_add_model(mock_add_model, client: TestClient, setup_api_key, model_config_instance, llm_provider_config):
    """Test adding a new model."""
    new_model = model_config_instance.model_copy(update={"id": "new_test_model"})
    mock_add_model.return_value = new_model
    new_model_data = model_config_instance.model_dump()
    new_model_data["id"] = "new_test_model"
    response = client.post(
        "/admin/models",
        json={"model": new_model_data},
        headers={"X-API-Key": "test-admin-key"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "new_test_model"


@patch("app.services.model_registry.ModelRegistryService.add_model", new_callable=AsyncMock)
def test_admin_add_model_conflict(mock_add_model, client: TestClient, setup_api_key, model_config_instance, llm_provider_config):
    """Test adding a model that already exists."""
    mock_add_model.side_effect = ValueError("Model already exists")
    model_data = model_config_instance.model_dump()
    response = client.post(
        "/admin/models",
        json={"model": model_data},
        headers={"X-API-Key": "test-admin-key"}
    )
    assert response.status_code == 409


@patch("app.services.model_registry.ModelRegistryService.update_model", new_callable=AsyncMock)
def test_admin_update_model(mock_update_model, client: TestClient, setup_api_key, model_config_instance, llm_provider_config):
    """Test updating an existing model."""
    updated_model = model_config_instance.model_copy(update={
        "name": "Updated Model",
        "description": "This model was updated"
    })
    mock_update_model.return_value = updated_model
    updated_model_data = updated_model.model_dump()
    response = client.put(
        f"/admin/models/{model_config_instance.id}",
        json={"model": updated_model_data},
        headers={"X-API-Key": "test-admin-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Model"


@patch("app.services.model_registry.ModelRegistryService.update_model", new_callable=AsyncMock)
def test_admin_update_model_id_mismatch(mock_update_model, client: TestClient, setup_api_key, model_config_instance, llm_provider_config):
    """Test updating a model with mismatched IDs."""
    # Create a model with a different ID
    different_id_model = model_config_instance.model_copy(update={"id": "different_id"})
    different_id_data = different_id_model.model_dump()
    
    response = client.put(
        "/admin/models/test_model_1",
        json={"model": different_id_data},
        headers={"X-API-Key": "test-admin-key"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "mismatch" in data["error"].lower()


@patch("app.services.model_registry.ModelRegistryService.update_model", new_callable=AsyncMock)
def test_admin_update_model_not_found(mock_update_model, client: TestClient, setup_api_key, model_config_instance, llm_provider_config):
    """Test updating a model that doesn't exist."""
    mock_update_model.side_effect = KeyError("Model not found")
    nonexistent_model = model_config_instance.model_copy(update={"id": "nonexistent_model"})
    nonexistent_data = nonexistent_model.model_dump()
    response = client.put(
        "/admin/models/nonexistent_model",
        json={"model": nonexistent_data},
        headers={"X-API-Key": "test-admin-key"}
    )
    assert response.status_code == 404


@patch("app.services.model_registry.ModelRegistryService.delete_model", new_callable=AsyncMock)
def test_admin_delete_model(mock_delete_model, client: TestClient, setup_api_key):
    """Test deleting a model."""
    # Setup mock to return success
    mock_delete_model.return_value = None
    
    response = client.delete(
        "/admin/models/test_model_1",
        headers={"X-API-Key": "test-admin-key"}
    )
    
    assert response.status_code == 204


@patch("app.services.model_registry.ModelRegistryService.delete_model", new_callable=AsyncMock)
def test_admin_delete_model_not_found(mock_delete_model, client: TestClient, setup_api_key):
    """Test deleting a model that doesn't exist."""
    mock_delete_model.side_effect = KeyError("Model not found")
    response = client.delete(
        "/admin/models/nonexistent_model",
        headers={"X-API-Key": "test-admin-key"}
    )
    assert response.status_code == 404


@patch("app.services.model_registry.ModelRegistryService.reload_configs")
def test_admin_reload_configs(mock_reload, client: TestClient, setup_api_key):
    """Test reloading configurations."""
    # Setup mock to return updated models
    mock_reload.return_value = {
        "test_model_1": MagicMock(),
        "test_model_2": MagicMock()
    }
    
    response = client.post(
        "/admin/reload",
        headers={"X-API-Key": "test-admin-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "message" in data