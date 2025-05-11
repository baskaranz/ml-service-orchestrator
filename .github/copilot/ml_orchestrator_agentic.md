# ML Orchestrator - AI-Agentic Coding Guide

This guide provides tailored agentic coding approaches specifically for the ML Orchestrator Service codebase.

## Codebase Architecture Overview

The ML Orchestrator has these specific architectural components to be aware of:

1. **Config Layer**
   - `app/config/models_config.py`: YAML model configuration loading
   - `app/config/settings.py`: Environment-based application settings

2. **API Layer**
   - `app/api/routes/orchestrator.py`: Main model request routing
   - `app/api/routes/admin.py`: Admin operations for model management
   - `app/api/routes/health.py`: Health checking and monitoring
   - `app/api/dependencies.py`: FastAPI dependency injection

3. **Core Layer**
   - `app/core/models.py`: Pydantic data models for configuration
   - `app/core/orchestrator.py`: Main orchestration logic and circuit breakers
   - `app/core/exceptions.py`: Custom exception types and handlers

4. **Service Layer**
   - `app/services/model_registry.py`: Model registration and lookups
   - `app/services/proxy.py`: Request proxying to model endpoints

5. **Utilities Layer**
   - `app/utils/http.py`: HTTP client and request handling
   - `app/utils/logging.py`: Structured logging utilities

## Codebase-Specific Patterns

When implementing features, be aware of these specific patterns:

1. **YAML Configuration-Driven Architecture**
   - Models are defined in YAML with environment variable substitution
   - Configuration files are hot-reloaded without service restart
   - `ModelConfigManager` handles loading and parsing

2. **FastAPI Dependency Injection**
   - Services are provided via dependency injection
   - API key validation via `get_api_key` dependency
   - Pattern: `service: ServiceClass = Depends(get_service)`

3. **Async/Await Throughout**
   - All IO operations use async/await
   - HTTP requests use the `HttpClient` in `app/utils/http.py`
   - Endpoints are async functions with proper error handling

4. **Circuit Breaker Pattern**
   - Implementation in `app/core/orchestrator.py`
   - Models have individual circuit breaker configurations
   - Failure counting and automatic reset after timeout

5. **Structured Error Handling**
   - Custom exception types in `app/core/exceptions.py`
   - Exception handlers registered in FastAPI
   - Consistent error response format with status codes

6. **Comprehensive Testing Approach**
   - Tests mirror application structure in `tests/` directory
   - Async tests use `pytest.mark.asyncio`
   - Mock usage for external dependencies
   - Pattern-specific tests (e.g., circuit breaker tests)

## ML Orchestrator Agentic Task Templates

### 1. Adding a New Model Configuration Feature

```
I need you to extend the model configuration system to support [FEATURE_NAME].

Based on the existing ModelConfig in app/core/models.py and configuration loading in 
app/config/models_config.py, implement a new configuration feature that will:

1. Add new field(s) to the ModelConfig Pydantic model
2. Update the YAML parsing in ModelConfigManager
3. Add appropriate validation
4. Update the Orchestrator to use the new configuration
5. Add tests for the new functionality

Example implementation approach:
1. Examine how similar features like circuit_breaker or auth are implemented
2. Follow the pattern of nested Pydantic models for structured config
3. Add proper defaults and validation
4. Update test fixtures to include the new configuration

Use full autonomy to implement this feature following the existing patterns in the codebase.
```

### 2. Enhancing Circuit Breaker Functionality

```
I need you to enhance the circuit breaker implementation in app/core/orchestrator.py.

The current implementation has these characteristics:
- CircuitBreaker class tracks failure counts and state
- Simple open/closed states with reset_timeout
- No half-open state or test requests
- Individual breakers per model

Implement these enhancements:
1. Add a half-open state that allows a single test request
2. Implement exponential backoff for retry attempts
3. Add proper metrics for circuit state changes
4. Improve the failure detection logic

The implementation should:
- Maintain backward compatibility with existing configuration
- Follow the async patterns in the codebase
- Include comprehensive tests for each state transition
- Update documentation comments

Use full autonomy to implement these enhancements while maintaining the existing architecture.
```

### 3. Implementing Model Response Caching

```
I need you to implement a response caching system for the ML Orchestrator.

Based on our architecture:
1. Create a new CacheService in app/services/cache.py
2. Add cache configuration to ModelConfig in app/core/models.py
3. Integrate caching in the ProxyService in app/services/proxy.py
4. Add cache metrics to health reporting

The cache should:
- Use model ID and request content hash as cache keys
- Support TTL-based expiration configurable per model
- Include hit/miss metrics
- Support cache bypass via request header
- Follow our existing async patterns

Implementation approach:
1. Study how the ModelRegistry and ProxyService are implemented
2. Follow the dependency injection pattern for the CacheService
3. Add proper configuration validation
4. Integrate with existing error handling
5. Add comprehensive tests

Use full autonomy to implement this feature following our established patterns.
```

### 4. Fixing Model Registry Performance

```
I need you to optimize the ModelRegistry service in app/services/model_registry.py.

The current implementation has these performance issues:
- Linear search for model lookups (O(n) complexity)
- Inefficient model updates requiring full reload
- No concurrency control for simultaneous operations

Implement these optimizations:
1. Change the internal data structure for O(1) lookups
2. Implement efficient partial updates
3. Add proper async locking for thread safety
4. Improve error handling for missing models
5. Add registry metrics for monitoring

Requirements:
- Maintain the existing public API
- Follow our async/await patterns
- Ensure backward compatibility
- Keep the hot-reload capability
- Maintain 100% test coverage

Use full autonomy to refactor this service while following our established patterns.
```

### 5. Implementing Comprehensive Tests

```
I need you to implement comprehensive tests for app/core/orchestrator.py to improve 
coverage from 65% to at least 90%.

Focus on these specific areas:
1. Circuit breaker state transitions and recovery
2. Request routing with different model configurations
3. Error handling for various failure scenarios
4. Timeout and retry mechanism
5. Authentication header processing

Based on our testing patterns:
1. Create tests in tests/test_core/test_orchestrator.py
2. Use pytest.mark.asyncio for async tests
3. Use AsyncMock for mocking async functions
4. Create appropriate fixtures for testing
5. Ensure proper assertion messages

Implementation approach:
1. Study existing tests in tests/test_core/
2. Follow the patterns from other comprehensive test files
3. Use the pytest fixtures in tests/conftest.py
4. Test both success and failure paths

Use full autonomy to implement these tests following our established patterns.
```

## Decision Boundaries for ML Orchestrator

### Configuration Layer Decisions

**You have autonomy to:**
- Add new configuration options to existing models
- Implement environment variable substitution
- Add validation for configuration values
- Improve error messages for configuration issues

**Please ask for guidance on:**
- Changing the YAML schema format
- Adding new top-level configuration sections
- Modifying the environment variable substitution syntax

### API Layer Decisions

**You have autonomy to:**
- Add new endpoints following existing patterns
- Implement new response models
- Add request validation
- Enhance existing endpoint functionality

**Please ask for guidance on:**
- Changing existing endpoint signatures
- Modifying authentication mechanisms
- Adding new API versioning
- Changing error response formats

### Core Layer Decisions

**You have autonomy to:**
- Enhance circuit breaker implementation
- Add new functionality to orchestrator
- Add new Pydantic models
- Improve exception handling

**Please ask for guidance on:**
- Changing the core orchestration flow
- Modifying public interfaces of core components
- Changing the circuit breaker state model
- Modifying the exception hierarchy

### Service Layer Decisions

**You have autonomy to:**
- Optimize internal implementations
- Add new service methods
- Improve error handling
- Add metrics and logging

**Please ask for guidance on:**
- Adding new service dependencies
- Changing service initialization patterns
- Modifying public service interfaces
- Changing the dependency injection model

### Testing Decisions

**You have autonomy to:**
- Add new test cases and scenarios
- Create test fixtures and helpers
- Improve assertion messages
- Add performance tests

**Please ask for guidance on:**
- Changing the testing framework
- Modifying global test fixtures
- Changing the test directory structure

## ML Orchestrator Workflow Patterns

### Configuration-Driven Feature Implementation

```
For implementing [FEATURE_NAME], which requires configuration changes:

1. First, examine app/core/models.py to understand the ModelConfig structure
2. Then, check app/config/models_config.py to see configuration loading
3. Study existing config examples in config/models/ directory
4. Add new Pydantic model(s) to app/core/models.py
5. Update YAML parsing in ModelConfigManager
6. Ensure proper validation and defaults
7. Add usage of the new config in relevant services
8. Create tests for the new configuration
9. Update example YAML files

Each step should follow existing patterns in the codebase.
```

### Service Integration Pattern

```
For implementing [SERVICE_NAME] which needs integration with existing services:

1. First, study app/services/model_registry.py and app/services/proxy.py
2. Create a new service file in app/services/
3. Define the service class with clear responsibility
4. Implement dependency injection with a get_service function
5. Add the service to app/main.py's setup
6. Integrate with existing services through dependencies
7. Add comprehensive tests in tests/test_services/
8. Update relevant health checks

Follow our established patterns for service implementation and dependency injection.
```

### Circuit Breaker Enhancement Pattern

```
For enhancing the circuit breaker functionality:

1. First, study app/core/orchestrator.py to understand current implementation
2. Extend the CircuitBreaker class with new states/functionality
3. Update the Orchestrator.proxy_request method to use new features
4. Ensure backward compatibility with existing configuration
5. Add detailed logging for state transitions
6. Add metrics for circuit breaker operations
7. Create tests for all state transitions and edge cases
8. Update documentation

This follows our pattern of improving core functionality while maintaining compatibility.
```

## Codebase-Specific Quality Verification

When implementing features, verify your solution against these ML Orchestrator-specific criteria:

### Configuration Handling
- Does the implementation follow our YAML configuration pattern?
- Is environment variable substitution properly supported?
- Are configuration changes hot-reloadable?
- Are there proper validation error messages?

### Async Implementation
- Does the code use async/await consistently?
- Are async functions properly tested with pytest.mark.asyncio?
- Is proper error handling implemented for async operations?
- Are timeouts properly managed?

### Circuit Breaker Integration
- Does the implementation properly integrate with circuit breakers?
- Are failure conditions properly detected and handled?
- Are circuit breaker states properly tracked and reset?
- Are metrics collected for circuit breaker events?

### FastAPI Integration
- Does the implementation follow our dependency injection pattern?
- Are routes properly defined with appropriate response models?
- Is authentication properly handled?
- Are exceptions caught and converted to appropriate HTTP responses?

### Testing Quality
- Do tests follow our pytest patterns?
- Is AsyncMock used for mocking async functions?
- Are both success and failure paths tested?
- Does test coverage meet our target (80%+)?

## Self-Review Process for ML Orchestrator

After implementing a feature, perform this ML Orchestrator-specific self-review:

1. **Configuration Review**
   - Does the implementation load and validate configuration correctly?
   - Are changes compatible with existing YAML files?
   - Is hot-reloading supported for configuration changes?

2. **Async Implementation**
   - Are all IO operations properly async?
   - Is proper error handling implemented for async functions?
   - Are timeouts properly configured and respected?

3. **Circuit Breaker Integration**
   - Does the implementation respect circuit breaker states?
   - Are failures properly detected and counted?
   - Is circuit breaker configuration properly used?

4. **Service Integration**
   - Does the implementation follow our dependency injection pattern?
   - Are services properly initialized and integrated?
   - Is error propagation consistent with our patterns?

5. **API Integration**
   - Do new/modified endpoints follow our FastAPI patterns?
   - Are request/response models properly defined?
   - Is authentication properly handled?

6. **Testing Quality**
   - Do tests cover both success and failure paths?
   - Are async tests properly implemented with pytest.mark.asyncio?
   - Is mocking done correctly with AsyncMock for async functions?
   - Does coverage meet our 80%+ target?

7. **Documentation**
   - Are docstrings added/updated with proper format?
   - Are complex code sections adequately commented?
   - Are public interfaces clearly documented?

8. **Performance**
   - Have you considered the performance impact of changes?
   - Are there any potential bottlenecks introduced?
   - Is caching used appropriately where beneficial?