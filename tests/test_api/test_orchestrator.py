"""Tests for orchestrator API routers."""

import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from app.core.exceptions import ModelRequestError, CircuitBreakerError
from app.services.proxy import ProxyService


@patch("app.services.model_registry.ModelRegistryService.get_model_config")
def test_orchestrator_route_not_found(mock_get_model, client: TestClient):
    """Test that requesting a non-existent model returns 404."""
    # Mock registry to return None for non-existent model
    mock_get_model.side_effect = Exception("Model not found")
    
    response = client.get("/orchestrator/non_existent_model")
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@patch("app.services.proxy.ProxyService.proxy_to_model")
@patch("app.services.model_registry.ModelRegistryService.get_model_config")
def test_orchestrator_route_success(mock_get_model, mock_proxy, client: TestClient, model_config_instance):
    """Test successful routing to a model endpoint."""
    # Setup mocks
    mock_get_model.return_value = model_config_instance
    mock_response = Response(content=json.dumps({"result": "success"}), media_type="application/json")
    mock_proxy.return_value = mock_response
    
    response = client.get("/orchestrator/test_model_1")
    
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "success"


@patch("app.services.proxy.ProxyService.proxy_to_model")
@patch("app.services.model_registry.ModelRegistryService.get_model_config")
def test_orchestrator_route_with_path(mock_get_model, mock_proxy, client: TestClient, model_config_instance):
    """Test routing with additional path parameters."""
    # Setup mocks
    mock_get_model.return_value = model_config_instance
    mock_response = Response(content=json.dumps({"result": "success"}), media_type="application/json")
    mock_proxy.return_value = mock_response
    
    response = client.get("/orchestrator/test_model_1/predict?param=value")
    
    # Verify the proxy was called with the correct path_suffix
    mock_proxy.assert_called_once()
    call_args = mock_proxy.call_args[0]
    assert call_args[0] == "test_model_1"  # model_id
    assert "predict" in call_args[2]  # path_suffix
    
    assert response.status_code == 200


@patch("app.services.proxy.ProxyService.proxy_to_model")
@patch("app.services.model_registry.ModelRegistryService.get_model_config")
def test_orchestrator_route_post_json(mock_get_model, mock_proxy, client: TestClient, model_config_instance):
    """Test POST request with JSON body."""
    # Setup mocks
    mock_get_model.return_value = model_config_instance
    mock_response = Response(content=json.dumps({"result": "processed"}), media_type="application/json")
    mock_proxy.return_value = mock_response
    
    # Send POST request with JSON body
    response = client.post(
        "/orchestrator/test_model_1/predict",
        json={"text": "test text"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "processed"


@patch("app.services.proxy.ProxyService.proxy_to_model")
@patch("app.services.model_registry.ModelRegistryService.get_model_config")
def test_orchestrator_model_request_error(mock_get_model, mock_proxy, client: TestClient, model_config_instance):
    """Test handling model request errors."""
    # Setup mocks
    mock_get_model.return_value = model_config_instance
    mock_proxy.side_effect = ModelRequestError(
        message="Error calling model API",
        status_code=500,
        model_id="test_model_1"
    )
    
    response = client.get("/orchestrator/test_model_1")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert "Error calling model API" in data["error"]


@patch("app.services.proxy.ProxyService.proxy_to_model")
@patch("app.services.model_registry.ModelRegistryService.get_model_config")
def test_orchestrator_circuit_breaker_error(mock_get_model, mock_proxy, client: TestClient, model_config_instance):
    """Test handling circuit breaker errors."""
    # Setup mocks
    mock_get_model.return_value = model_config_instance
    mock_proxy.side_effect = CircuitBreakerError(
        model_id="test_model_1"
    )
    
    response = client.get("/orchestrator/test_model_1")
    
    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert "circuit breaker" in data["error"].lower()


@pytest.mark.asyncio
@patch("app.services.model_registry.ModelRegistryService.get_model_config")
@patch("app.services.proxy.ProxyService.proxy_to_model")
async def test_orchestrator_async_request(mock_proxy, mock_get_model, async_client, model_config_instance):
    """Test the orchestrator routing asynchronously."""
    # Setup mocks
    mock_get_model.return_value = model_config_instance
    mock_response = Response(content=json.dumps({"result": "async_success"}), media_type="application/json")
    mock_proxy.return_value = mock_response
    
    # Send an async request
    response = await async_client.get("/orchestrator/test_model_1/predict")
    
    # Verify the mock was called
    mock_proxy.assert_called_once()
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "async_success"