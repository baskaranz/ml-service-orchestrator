# Platform Configuration Guide

This document provides a detailed explanation of all platform configurations available in the ML Orchestrator.

## Table of Contents

1. [Application Settings](#application-settings)
2. [Server Settings](#server-settings)
3. [Config File Paths](#config-file-paths)
4. [Default Service Settings](#default-service-settings)
5. [Circuit Breaker Settings](#circuit-breaker-settings)
6. [Error Handling Settings](#error-handling-settings)
7. [Health Check Settings](#health-check-settings)
8. [Logging Settings](#logging-settings)
9. [Admin API Settings](#admin-api-settings)
10. [LLM Provider Settings](#llm-provider-settings)
11. [Model Platform Settings](#model-platform-settings)

## Application Settings

```ini
APP_NAME=ML Orchestrator
APP_VERSION=1.0.0
DEBUG=true
```

- `APP_NAME`: Name of the application (default: "ML Orchestrator")
- `APP_VERSION`: Version of the application (default: "1.0.0")
- `DEBUG`: Enable/disable debug mode (default: false)

## Server Settings

```ini
HOST=0.0.0.0
PORT=8000
WORKERS=1
```

- `HOST`: Host address to bind the server (default: "0.0.0.0")
- `PORT`: Port number to listen on (default: 8000)
- `WORKERS`: Number of worker processes (default: 1)

## Config File Paths

```ini
CONFIG_DIR=config
MODELS_DIR=config/{env}/models
```

- `CONFIG_DIR`: Base directory for configuration files
- `MODELS_DIR`: Directory containing model configurations (environment-specific)
- `{env}`: Environment name (e.g., 'dev', 'stg', 'prod') determined by the `APP_ENV` environment variable (defaults to 'dev')

## Default Service Settings

```ini
DEFAULT_TIMEOUT=30.0
DEFAULT_MAX_RETRIES=3
```

- `DEFAULT_TIMEOUT`: Default timeout for service requests in seconds
- `DEFAULT_MAX_RETRIES`: Default maximum number of retry attempts

## Circuit Breaker Settings

```ini
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RESET_TIMEOUT=30.0
CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT=30.0
CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2
```

- `CIRCUIT_BREAKER_FAILURE_THRESHOLD`: Number of failures before opening the circuit
- `CIRCUIT_BREAKER_RESET_TIMEOUT`: Time in seconds before attempting to close the circuit
- `CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT`: Time in seconds to stay in half-open state
- `CIRCUIT_BREAKER_SUCCESS_THRESHOLD`: Number of successful calls to close the circuit

## Error Handling Settings

```ini
ERROR_HANDLING_BACKOFF_FACTOR=2.0
ERROR_HANDLING_MAX_RETRY_DELAY=30.0
ERROR_HANDLING_RETRY_DELAY=1.0
```

- `ERROR_HANDLING_BACKOFF_FACTOR`: Multiplier for exponential backoff
- `ERROR_HANDLING_MAX_RETRY_DELAY`: Maximum delay between retries in seconds
- `ERROR_HANDLING_RETRY_DELAY`: Initial delay between retries in seconds

## Health Check Settings

```ini
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=5
HEALTH_CHECK_FAILURE_THRESHOLD=3
HEALTH_CHECK_SUCCESS_THRESHOLD=2
```

- `HEALTH_CHECK_ENABLED`: Enable/disable health checks
- `HEALTH_CHECK_INTERVAL`: Time between health checks in seconds
- `HEALTH_CHECK_TIMEOUT`: Timeout for health check requests in seconds
- `HEALTH_CHECK_FAILURE_THRESHOLD`: Number of failures before marking unhealthy
- `HEALTH_CHECK_SUCCESS_THRESHOLD`: Number of successes to mark as healthy

## Logging Settings

```ini
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_INCLUDE_METADATA=true
LOG_SENSITIVE_FIELDS=api_key,password,token
```

- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT`: Log format (json or text)
- `LOG_INCLUDE_METADATA`: Include additional metadata in logs
- `LOG_SENSITIVE_FIELDS`: Comma-separated list of fields to mask in logs

## Admin API Settings

```ini
ADMIN_API_ENABLED=true
ADMIN_API_KEY=your-admin-key
```

- `ADMIN_API_ENABLED`: Enable/disable admin API
- `ADMIN_API_KEY`: API key for admin access

## LLM Provider Settings

```ini
LLM_ENABLED=true
LLM_PROVIDER_TYPE=huggingface
LLM_PROVIDER_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.2
LLM_PROVIDER_TIMEOUT=30
LLM_PROVIDER_MAX_RETRIES=3
```

- `LLM_ENABLED`: Enable/disable LLM features
- `LLM_PROVIDER_TYPE`: LLM provider type (huggingface or ollama)
- `LLM_PROVIDER_MODEL_NAME`: Name of the model to use
- `LLM_PROVIDER_TIMEOUT`: Timeout for LLM requests in seconds
- `LLM_PROVIDER_MAX_RETRIES`: Maximum number of retries for LLM requests

## Model Platform Settings

```ini
MODEL_PLATFORM_ENABLED=true
MODEL_PLATFORM_TIMEOUT=30.0
MODEL_PLATFORM_MAX_RETRIES=3
MODEL_PLATFORM_HEALTH_CHECK_INTERVAL=30
MODEL_PLATFORM_HEALTH_CHECK_TIMEOUT=5
MODEL_PLATFORM_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
MODEL_PLATFORM_CIRCUIT_BREAKER_RESET_TIMEOUT=30.0
MODEL_PLATFORM_CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT=30.0
MODEL_PLATFORM_CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2
```

- `MODEL_PLATFORM_ENABLED`: Enable/disable platform configuration for models
- `MODEL_PLATFORM_TIMEOUT`: Default timeout for model platform requests in seconds
- `MODEL_PLATFORM_MAX_RETRIES`: Default maximum number of retry attempts for model platform requests
- `MODEL_PLATFORM_HEALTH_CHECK_INTERVAL`: Time between health checks for model platforms in seconds
- `MODEL_PLATFORM_HEALTH_CHECK_TIMEOUT`: Timeout for model platform health check requests in seconds
- `MODEL_PLATFORM_CIRCUIT_BREAKER_FAILURE_THRESHOLD`: Default number of failures before opening the circuit
- `MODEL_PLATFORM_CIRCUIT_BREAKER_RESET_TIMEOUT`: Default time in seconds before attempting to close the circuit
- `MODEL_PLATFORM_CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT`: Default time in seconds to stay in half-open state
- `MODEL_PLATFORM_CIRCUIT_BREAKER_SUCCESS_THRESHOLD`: Default number of successful calls to close the circuit

### Model Platform Configuration

Each model can have its own platform configuration that overrides the default settings. The platform configuration is defined in the model's YAML file:

```yaml
id: "model_id"
name: "Model Name"
endpoint_url: "http://model-endpoint/predict"
platform:
  timeout: 45.0
  max_retries: 5
  health_check:
    enabled: true
    interval: 60
    timeout: 10
    failure_threshold: 3
    success_threshold: 2
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    reset_timeout: 30.0
    half_open_timeout: 30.0
    success_threshold: 2
  error_handling:
    enabled: true
    max_retries: 3
    retry_delay: 1.0
    max_retry_delay: 30.0
    backoff_factor: 2.0
```

The platform configuration supports the following settings:

- `timeout`: Request timeout in seconds
- `max_retries`: Maximum number of retry attempts
- `health_check`: Health check configuration
  - `enabled`: Enable/disable health checks
  - `interval`: Time between health checks in seconds
  - `timeout`: Health check request timeout in seconds
  - `failure_threshold`: Number of failures before marking unhealthy
  - `success_threshold`: Number of successes to mark as healthy
- `circuit_breaker`: Circuit breaker configuration
  - `enabled`: Enable/disable circuit breaker
  - `failure_threshold`: Number of failures before opening the circuit
  - `reset_timeout`: Time in seconds before attempting to close the circuit
  - `half_open_timeout`: Time in seconds to stay in half-open state
  - `success_threshold`: Number of successful calls to close the circuit
- `error_handling`: Error handling configuration
  - `enabled`: Enable/disable error handling
  - `max_retries`: Maximum number of retry attempts
  - `retry_delay`: Initial delay between retries in seconds
  - `max_retry_delay`: Maximum delay between retries in seconds
  - `backoff_factor`: Multiplier for exponential backoff

If a model does not specify platform settings, the default values from the environment configuration will be used. The platform configuration is automatically applied to all registered model endpoints through the orchestrator.

## Environment-Specific Configurations

The platform supports different configurations for different environments:

### Development Environment

- Debug mode enabled
- Single worker
- Local file paths
- Ollama as LLM provider
- Shorter timeouts and retries

### Production Environment

- Debug mode disabled
- Multiple workers
- System-wide file paths
- Hugging Face as LLM provider
- Longer timeouts and more retries

### Test Environment

- Debug mode enabled
- Single worker
- Temporary file paths
- LLM features disabled
- Minimal timeouts and retries

## Best Practices

1. **Environment Selection**

   - Use development settings for local development
   - Use production settings for deployment
   - Use test settings for automated testing

2. **Security**

   - Never commit sensitive values to version control
   - Use environment variables for secrets
   - Regularly rotate API keys

3. **Performance**

   - Adjust worker count based on available CPU cores
   - Configure appropriate timeouts for your use case
   - Monitor and adjust circuit breaker thresholds

4. **Monitoring**
   - Use appropriate log levels for each environment
   - Enable metadata logging in production
   - Configure sensitive field masking

## Configuration Validation

The platform validates all configuration values:

- Port numbers must be between 1 and 65535
- Log levels must be valid (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Timeouts must be positive numbers
- Retry counts must be non-negative
- File paths must be valid and accessible
