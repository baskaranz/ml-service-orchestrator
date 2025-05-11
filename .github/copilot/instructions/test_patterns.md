# ML Orchestrator - Test Patterns

This file provides detailed guidance for writing tests for the ML Orchestrator service.

## Overview

The ML Orchestrator uses pytest for testing, with these key testing patterns:
1. Test files mirror the application structure
2. Async tests use pytest-asyncio
3. Dependencies are mocked with unittest.mock
4. Fixtures are used for test setup
5. Both success and error paths are tested

## Test Directory Structure

The test directory structure mirrors the application structure:

```
tests/
├── conftest.py                    # Global test fixtures
├── test_api/                      # Tests for API routes
│   ├── test_admin.py              # Admin API tests
│   ├── test_dependencies.py       # API dependency tests
│   ├── test_health.py             # Health API tests
│   └── test_orchestrator.py       # Orchestrator API tests
├── test_config/                   # Tests for configuration
│   ├── test_models_config.py      # Model config tests
│   └── test_settings.py           # Settings tests
├── test_core/                     # Tests for core domain
│   ├── test_exceptions.py         # Exception tests
│   ├── test_models.py             # Model tests
│   └── test_orchestrator.py       # Orchestrator tests
├── test_services/                 # Tests for services
│   ├── test_model_registry.py     # Model registry tests
│   └── test_proxy.py              # Proxy service tests
└── test_utils/                    # Tests for utilities
    ├── test_http.py               # HTTP utility tests
    └── test_logging.py            # Logging utility tests
```

When adding tests, follow this structure and create new test files in the appropriate directories.

## Test Fixtures

Global test fixtures are defined in `tests/conftest.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.config.models_config import ModelConfigManager
from app.core.models import ModelConfig, CircuitBreakerSettings, AuthConfig
from app.core.orchestrator import Orchestrator
from app.services.model_registry import ModelRegistryService
from app.services.proxy import ProxyService
from app.main import create_app
from tests.mocks.settings import settings

@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return settings

@pytest.fixture
def app():
    """Create a test FastAPI app instance."""
    return create_app()

@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def model_config_instance():
    """Create a sample ModelConfig instance for testing."""
    return ModelConfig(
        id="test_model_1",
        name="Test Model",
        description="A test model for unit tests",
        endpoint_url="http://localhost:8888/test",
        version="1.0.0",
        timeout=10.0,
        max_retries=2,
        circuit_breaker=CircuitBreakerSettings(
            failure_threshold=3,
            reset_timeout=15.0
        ),
        auth=AuthConfig(
            type="api_key",
            key_name="X-API-Key",
            key_value="test_api_key",
            location="header"
        ),
        headers={"X-Source": "test"},
        active=True
    )

@pytest.fixture
def model_configs(model_config_instance):
    """Create a list of model configs for testing."""
    model_2 = ModelConfig(
        id="test_model_2",
        name="Test Model 2",
        description="Another test model for unit tests",
        endpoint_url="http://localhost:8889/test2",
        version="1.0.0",
        timeout=15.0,
        max_retries=3,
        circuit_breaker=CircuitBreakerSettings(
            failure_threshold=4,
            reset_timeout=20.0
        ),
        auth=AuthConfig(
            type="bearer_token",
            key_value="test_token"
        ),
        headers={"X-Source": "test2"},
        active=True
    )
    return [model_config_instance, model_2]

@pytest.fixture
def mock_config_manager():
    """Create a mock ModelConfigManager for testing."""
    manager = ModelConfigManager(
        config_dir="/tmp/test_config",
        registry_file="/tmp/test_config/models_registry.yaml"
    )
    return manager

@pytest.fixture
def mock_model_registry():
    """Create a mock ModelRegistryService for testing."""
    config_manager = ModelConfigManager(
        config_dir="/tmp/test_config",
        registry_file="/tmp/test_config/models_registry.yaml"
    )
    service = ModelRegistryService(config_manager)
    
    # Load models into the registry
    service._models = {
        "test_model_1": ModelConfig(
            id="test_model_1",
            name="Test Model",
            description="A test model for unit tests",
            endpoint_url="http://localhost:8888/test",
            version="1.0.0",
            timeout=10.0,
            max_retries=2,
            auth=AuthConfig(type="api_key", key_name="X-API-Key", key_value="test_api_key"),
            active=True
        ),
        "test_model_2": ModelConfig(
            id="test_model_2",
            name="Test Model 2",
            description="Another test model for unit tests",
            endpoint_url="http://localhost:8889/test2",
            version="1.0.0",
            auth=AuthConfig(type="bearer_token", key_value="test_token"),
            active=True
        )
    }
    return service

@pytest.fixture
def mock_orchestrator():
    """Create a mock Orchestrator for testing."""
    return Orchestrator()

@pytest.fixture
def mock_proxy_service(mock_model_registry, mock_orchestrator):
    """Create a mock ProxyService for testing."""
    return ProxyService(mock_model_registry, mock_orchestrator)

@pytest.fixture
async def async_client(app):
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

You can use these fixtures in your tests and add more specific fixtures in individual test files as needed.

## Async Testing

For testing async functions, use the `pytest.mark.asyncio` decorator:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test an async function."""
    # Setup
    expected = "expected_result"
    
    # Execute
    result = await async_function()
    
    # Assert
    assert result == expected
```

For mocking async functions, use `AsyncMock`:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_async_mock():
    """Test using an async mock."""
    # Setup mock
    mock_dependency = AsyncMock()
    mock_dependency.async_method.return_value = "mocked_result"
    
    # Execute with mock
    with patch("module.dependency", mock_dependency):
        result = await function_under_test()
    
    # Assert
    assert result == "mocked_result"
    mock_dependency.async_method.assert_called_once()
```

## API Testing

For testing FastAPI endpoints, use the `TestClient` fixture:

```python
def test_health_endpoint(client):
    """Test the health endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

For testing async API endpoints, use the `async_client` fixture:

```python
@pytest.mark.asyncio
async def test_async_endpoint(async_client):
    """Test an async endpoint."""
    response = await async_client.get("/health/details")
    
    assert response.status_code == 200
    assert response.json()["status"] in ["ok", "warning", "error"]
```

For testing authenticated endpoints, mock the authentication dependency:

```python
def test_admin_endpoint(client, app):
    """Test an admin endpoint with authentication."""
    # Override authentication dependency
    app.dependency_overrides[get_api_key] = lambda: "test_key"
    
    try:
        # Make request
        response = client.get("/admin/models", headers={"X-API-Key": "test_key"})
        
        # Assert
        assert response.status_code == 200
    finally:
        # Clean up dependency override
        app.dependency_overrides = {}
```

## Service Testing

For testing services, mock the dependencies:

```python
@pytest.fixture
def mock_model_registry():
    """Create a mock model registry service."""
    registry = MagicMock(spec=ModelRegistryService)
    
    # Configure mock
    registry.get_model_config.return_value = ModelConfig(
        id="test_model",
        name="Test Model",
        endpoint_url="http://example.com/test"
    )
    
    return registry

@pytest.fixture
def proxy_service(mock_model_registry, mock_orchestrator):
    """Create a proxy service with mocked dependencies."""
    return ProxyService(mock_model_registry, mock_orchestrator)

@pytest.mark.asyncio
async def test_proxy_to_model(proxy_service, mock_orchestrator):
    """Test proxying a request to a model."""
    # Create mock request
    mock_request = AsyncMock()
    mock_request.json = AsyncMock(return_value={"prompt": "test"})
    mock_request.headers = {"content-type": "application/json"}
    
    # Configure mock orchestrator
    mock_orchestrator.proxy_request = AsyncMock(return_value={"result": "success"})
    
    # Execute
    result = await proxy_service.proxy_to_model("test_model", mock_request)
    
    # Assert
    assert result == {"result": "success"}
    mock_orchestrator.proxy_request.assert_called_once()
```

## Testing Error Paths

Always test error paths in addition to success paths:

```python
@pytest.mark.asyncio
async def test_proxy_service_error_handling(proxy_service, mock_model_registry, mock_orchestrator):
    """Test error handling in proxy service."""
    # Create mock request
    mock_request = AsyncMock()
    mock_request.json = AsyncMock(return_value={"prompt": "test"})
    mock_request.headers = {"content-type": "application/json"}
    
    # Configure model registry to raise an exception
    mock_model_registry.get_model_config.side_effect = KeyError("test_model")
    
    # Execute and verify error
    with pytest.raises(ModelRequestError) as exc_info:
        await proxy_service.proxy_to_model("test_model", mock_request)
    
    # Assert error details
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.message
```

## Testing Configuration

For testing configuration-related code, use temporary directories:

```python
@pytest.fixture
def test_config_dir(tmp_path):
    """Create a temporary config directory."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    
    # Create registry file
    registry = {
        "version": "1.0.0",
        "models": [
            {"id": "test_model", "file": "models/test_model.yaml"}
        ]
    }
    
    registry_file = tmp_path / "registry.yaml"
    registry_file.write_text(yaml.dump(registry))
    
    # Create model config file
    model_config = {
        "name": "Test Model",
        "description": "Test model for unit tests",
        "endpoint_url": "http://example.com/test",
        "version": "1.0.0",
        "timeout": 10.0,
        "active": True
    }
    
    model_file = models_dir / "test_model.yaml"
    model_file.write_text(yaml.dump(model_config))
    
    return tmp_path

@pytest.mark.asyncio
async def test_load_configs(test_config_dir):
    """Test loading configurations."""
    manager = ModelConfigManager(
        config_dir=str(test_config_dir),
        registry_file=str(test_config_dir / "registry.yaml")
    )
    
    # Load configs
    configs = await manager.load_configs()
    
    # Verify
    assert "test_model" in configs
    assert configs["test_model"].name == "Test Model"
    assert configs["test_model"].endpoint_url == "http://example.com/test"
```

## Test Isolation

Ensure tests are isolated and don't depend on each other:

```python
@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks after each test."""
    # This fixture will automatically reset all mocks after each test
    yield
    reset_all_mocks()
```

## Test Coverage

For measuring test coverage, use pytest-cov:

```bash
python -m pytest --cov=app --cov-report=term-missing
```

To measure coverage for a specific module:

```bash
python -m pytest tests/test_services/test_model_registry.py --cov=app.services.model_registry --cov-report=term-missing
```

## Test Organization for Complex Modules

For complex modules, organize tests into multiple files:

1. **Basic tests**: Simple, direct function testing
   ```
   tests/test_services/test_model_registry.py
   ```

2. **Advanced tests**: Complex scenarios, edge cases
   ```
   tests/test_services/test_model_registry_advanced.py
   ```

3. **Dependency tests**: Dependency injection testing
   ```
   tests/test_services/test_model_registry_dependency.py
   ```

## Common Testing Patterns

### Testing Asynchronous Functions

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test an async function."""
    # Setup
    input_data = {"key": "value"}
    expected = {"result": "success"}
    
    # Execute
    result = await async_function(input_data)
    
    # Assert
    assert result == expected
```

### Testing FastAPI Dependencies

```python
def test_dependency_function():
    """Test a dependency function directly."""
    # Execute
    result = dependency_function()
    
    # Assert
    assert result == expected

def test_dependency_in_endpoint(client, app):
    """Test a dependency function in an endpoint."""
    # Create a mock result
    mock_result = {"key": "value"}
    
    # Override the dependency
    app.dependency_overrides[dependency_function] = lambda: mock_result
    
    try:
        # Make request
        response = client.get("/endpoint")
        
        # Assert
        assert response.status_code == 200
        assert response.json() == expected_response
    finally:
        # Clean up
        app.dependency_overrides = {}
```

### Testing Exception Handlers

```python
def test_exception_handler(client):
    """Test an exception handler."""
    # Create a test endpoint that raises the exception
    @app.get("/test_exception")
    def test_endpoint():
        raise CustomException("Test error")
    
    # Make request
    response = client.get("/test_exception")
    
    # Assert
    assert response.status_code == expected_status_code
    assert response.json() == {
        "error": "custom_error",
        "detail": "Test error"
    }
```

### Testing Circuit Breaker

```python
@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker for testing."""
    return CircuitBreaker(failure_threshold=3, reset_timeout=5.0)

def test_circuit_breaker_initially_closed(circuit_breaker):
    """Test that circuit breaker is initially closed."""
    assert not circuit_breaker.is_open()

def test_circuit_breaker_opens_after_threshold(circuit_breaker):
    """Test that circuit breaker opens after threshold failures."""
    # Record failures up to threshold
    for _ in range(3):
        circuit_breaker.record_failure()
    
    # Verify circuit is open
    assert circuit_breaker.is_open()

def test_circuit_breaker_resets_after_timeout(circuit_breaker):
    """Test that circuit breaker resets after timeout."""
    # Open the circuit
    for _ in range(3):
        circuit_breaker.record_failure()
    
    # Verify circuit is open
    assert circuit_breaker.is_open()
    
    # Mock time passage
    circuit_breaker.last_failure_time = time.time() - 10.0  # 10 seconds ago, longer than reset_timeout
    
    # Verify circuit attempts to close
    assert not circuit_breaker.is_open()
```