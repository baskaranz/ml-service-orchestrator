"""Tests for model registry dependency injection."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.model_registry import (
    ModelRegistryService,
    get_model_registry_service,
    setup_model_registry
)


def test_get_model_registry_service():
    """Test the get_model_registry_service dependency."""
    # Call the dependency
    service = get_model_registry_service()
    
    # Verify a ModelRegistryService was returned
    assert isinstance(service, ModelRegistryService)
    
    # Verify it's a singleton
    service2 = get_model_registry_service()
    assert service is service2


def test_setup_model_registry():
    """Test setting up the model registry service with FastAPI."""
    # Create a FastAPI app
    app = FastAPI()
    
    # Set up the model registry
    setup_model_registry(app)
    
    # Verify startup and shutdown events were registered
    startup_events = [event for event in app.router.on_startup]
    shutdown_events = [event for event in app.router.on_shutdown]
    
    assert len(startup_events) == 1
    assert len(shutdown_events) == 1