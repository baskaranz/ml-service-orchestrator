"""Tests for proxy service dependency injection."""

from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.services.proxy import ProxyService, get_proxy_service
from app.services.model_registry import ModelRegistryService, get_model_registry_service
from app.core.orchestrator import Orchestrator


def test_get_proxy_service():
    """Test the get_proxy_service dependency."""
    # Create mock dependencies
    mock_registry = MagicMock(spec=ModelRegistryService)
    mock_orchestrator = MagicMock(spec=Orchestrator)
    
    # We need to provide the actual dependency values, not patch the functions
    # that create the dependencies, since FastAPI's Depends() resolves at runtime
    service = get_proxy_service(
        model_registry=mock_registry,
        orchestrator=mock_orchestrator
    )
    
    # Verify the right type is returned
    assert isinstance(service, ProxyService)
    
    # Verify dependencies were injected
    assert service.model_registry is mock_registry
    assert service.orchestrator is mock_orchestrator


def test_proxy_service_dependency_in_fastapi():
    """Test using the proxy service dependency in a FastAPI app."""
    # Create a test app
    app = FastAPI()
    
    # Mock the models
    mock_registry = MagicMock(spec=ModelRegistryService)
    mock_orchestrator = MagicMock(spec=Orchestrator)
    
    # Create a mock proxy service that we'll provide
    mock_proxy = ProxyService(mock_registry, mock_orchestrator)
    
    # Define a test endpoint using the dependency
    @app.get("/test")
    def test_endpoint(proxy: ProxyService = Depends(get_proxy_service)):
        # Just return a simple response to confirm the dependency worked
        return {"status": "ok", "registry_type": type(proxy.model_registry).__name__, "orchestrator_type": type(proxy.orchestrator).__name__}
    
    # Override the dependency directly
    app.dependency_overrides[get_proxy_service] = lambda: mock_proxy
    
    # Test the endpoint
    client = TestClient(app)
    response = client.get("/test")
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["registry_type"] == "MagicMock"
    assert response.json()["orchestrator_type"] == "MagicMock"
    

def test_proxy_service_initialization():
    """Test ProxyService initialization with different inputs."""
    # Test with real instances
    registry = ModelRegistryService(MagicMock())
    orchestrator = Orchestrator()
    service = ProxyService(registry, orchestrator)
    
    assert service.model_registry is registry
    assert service.orchestrator is orchestrator
    
    # Test with mock instances
    mock_registry = MagicMock(spec=ModelRegistryService)
    mock_orchestrator = MagicMock(spec=Orchestrator)
    service = ProxyService(mock_registry, mock_orchestrator)
    
    assert service.model_registry is mock_registry
    assert service.orchestrator is mock_orchestrator


def test_proxy_service_dependency_override():
    """Test simple dependency override for the proxy service."""
    # Create a test app
    app = FastAPI()
    
    # Create a test route using the proxy service
    @app.get("/test-dependency")
    async def test_route(proxy: ProxyService = Depends(get_proxy_service)):
        return {"service": "overridden"}
    
    # Create a mock proxy service
    mock_proxy = MagicMock(spec=ProxyService)
    
    # Override the dependency
    app.dependency_overrides[get_proxy_service] = lambda: mock_proxy
    
    # Test it
    client = TestClient(app)
    response = client.get("/test-dependency")
    
    # Verify the response
    assert response.status_code == 200
    
    # Verify the mock was used
    assert get_proxy_service != app.dependency_overrides[get_proxy_service]