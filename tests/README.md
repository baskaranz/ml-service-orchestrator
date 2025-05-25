# Testing Guide for ML Orchestrator Service

This document provides guidance on writing tests for the ML Orchestrator Service to maintain high test coverage and quality.

## Test Structure

Tests are organized mirroring the application structure:

```
tests/
├── conftest.py                 # Global test fixtures
├── test_api/                   # Tests for API routes and dependencies
│   ├── test_admin.py           # Admin route tests
│   ├── test_dependencies.py    # API dependency tests
│   ├── test_health.py          # Health route tests
│   └── test_orchestrator.py    # Orchestrator route tests
├── test_config/                # Tests for configuration modules
├── test_core/                  # Tests for core functionality
├── test_services/              # Tests for services
└── test_utils/                 # Tests for utility functions
```

## Best Practices for Testing

### 1. Test Coverage Requirements

- **Overall Target**: 80% or higher code coverage
- **Module Targets**:
  - Critical modules: 90%+ (orchestrator, proxy service, etc.)
  - General modules: 80%+
  - Infrastructure/config: 60%+

### 2. Async Testing

For testing async functions:

```python
import pytest

@pytest.mark.asyncio
async def test_my_async_function():
    # Test async function
    result = await my_async_function()
    assert result == expected_value
```

### 3. Mocking

Use `unittest.mock` for mocking dependencies:

```python
from unittest.mock import patch, MagicMock, AsyncMock

# For synchronous functions
with patch("module.function", return_value="mocked_value") as mock_func:
    result = function_under_test()
    mock_func.assert_called_once()

# For asynchronous functions
with patch("module.async_function", new_callable=AsyncMock) as mock_async_func:
    mock_async_func.return_value = "mocked_value"
    result = await function_under_test()
    mock_async_func.assert_called_once()
```

### 4. Testing FastAPI Dependencies

For testing FastAPI dependencies:

```python
# Direct testing
result = await dependency_function(param1, param2)
assert result == expected_value

# Testing in endpoint context
@app.get("/test")
def test_endpoint(dep_result = Depends(dependency_function)):
    return {"result": dep_result}

# Override dependency for testing
app.dependency_overrides[dependency_function] = lambda: "test_value"
response = client.get("/test")
assert response.status_code == 200
assert response.json() == {"result": "test_value"}
```

### 5. Circuit Breaker Testing

For testing circuit breaker patterns:

```python
# Test circuit open state
mock_cb = MagicMock()
mock_cb.is_open.return_value = True
with pytest.raises(CircuitBreakerError):
    await function_with_circuit_breaker(mock_cb)

# Test circuit closed state
mock_cb.is_open.return_value = False
result = await function_with_circuit_breaker(mock_cb)
assert result == expected_value
```

### 6. Organization Patterns

For complex modules, separate tests into:

1. **Basic tests**: Simple, direct function testing (`test_module.py`)
2. **Advanced tests**: Complex scenarios, edge cases (`test_module_advanced.py`)
3. **Dependency tests**: Dependency injection testing (`test_module_dependency.py`)

### 7. Running Tests with Coverage

```bash
# Run all tests with coverage
python -m pytest --cov=app --cov-report=term-missing

# Run tests for a specific module
python -m pytest tests/test_api/test_dependencies.py -v --cov=app.api.dependencies --cov-report=term-missing

# Run tests that match a pattern
python -m pytest -k "test_api_key" -v
```

### 8. Creating Test Fixtures

For reusable test components:

```python
import pytest

@pytest.fixture
def mock_service():
    """Create a mock service for testing."""
    service = MagicMock(spec=ServiceClass)
    service.method.return_value = "test_value"
    return service

@pytest.fixture
async def async_client(app):
    """Create an async client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

## Common Test Types

1. **Unit Tests**: Test individual functions or methods
2. **Integration Tests**: Test interactions between components
3. **API Tests**: Test HTTP endpoints using FastAPI TestClient
4. **Async Tests**: Test asynchronous functions with pytest-asyncio
5. **Error Handling Tests**: Test error conditions and exception handling
6. **Configuration Tests**: Test loading and validation of configuration
7. **Dependency Tests**: Test dependency injection and overrides

## Troubleshooting Common Issues

1. **Async Test Failures**:
   - Ensure proper use of `pytest.mark.asyncio`
   - Use `AsyncMock` for mocking async functions
   - Properly await async functions

2. **Mock Not Being Called**:
   - Verify the import path in the patch decorator
   - Ensure the mock is applied at the right scope

3. **HTTP Client Test Failures**:
   - Check Content-Type headers
   - Verify JSON serialization/deserialization
   - Check status codes and response bodies

4. **Test Isolation Problems**:
   - Reset mocks between tests
   - Use function-scoped fixtures
   - Avoid shared state between tests

## Recommended Testing Tools

- **pytest**: Base testing framework
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async testing
- **pytest-mock**: Simplified mocking
- **httpx**: Async HTTP client for testing
- **fastapi.testclient**: Testing FastAPI endpoints
