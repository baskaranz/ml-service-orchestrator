# ML Model Orchestrator

A FastAPI-based service for orchestrating multiple ML model predictions.

## Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- Virtual environment (recommended)
- Hugging Face API key (for production) or Ollama (for development)

## Running the Application

### 1. Start the Orchestrator

The orchestrator service runs in Docker and is model-agnostic. It will automatically discover and use any models configured in the `config/models/` directory.

```bash
# Start the orchestrator service using the provided script
./scripts/start_orchestrator.sh
```

### 2. Running Mock Models (for Testing)

For testing purposes, you can run mock model servers in Docker. The mock servers simulate ML model behavior and are useful for development and testing.

```bash
# Start mock model 1
./scripts/mocks/start_mock_model.sh mock-model-1 8001

# Start mock model 2
./scripts/mocks/start_mock_model.sh mock-model-2 8002
```

### 3. Verify Services

Check if all services are running correctly:

```bash
# Check orchestrator health
curl http://localhost:8000/health

# Check mock model 1 health
curl http://localhost:8001/health

# Check mock model 2 health
curl http://localhost:8002/health
```

### 4. Test Predictions

Test the prediction endpoints:

```bash
# Test mock model 1 prediction
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"data": [1, 2, 3, 4, 5]}, "parameters": {"threshold": 0.5}}'

# Test mock model 2 prediction
curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"data": [1, 2, 3, 4, 5]}, "parameters": {"threshold": 0.5}}'
```

## Configuration

### Model Configuration

Model configurations are stored in the `config/models` directory. The main application configuration is in `config/app.cfg`. Each model should have its own YAML configuration file with the following structure:

```yaml
# Basic configuration (required)
id: model-name
name: Model Name
endpoint_url: http://localhost:8001

# Optional LLM provider configuration
llm_provider:
  type: huggingface # or ollama
  model_name: mistralai/Mistral-7B-Instruct-v0.2
```

The LLM provider configuration is optional and can be omitted if you don't need advanced error handling or LLM-based features.

### Environment Variables

The orchestrator service uses the following environment variables (configured in docker-compose.yml):

- `APP_NAME`: Application name (default: orchestrator)
- `APP_VERSION`: Application version (default: 1.0.0)
- `DEBUG`: Debug mode (default: true)
- `HOST`: Host to bind to (default: 0.0.0.0)
- `PORT`: Port to listen on (default: 8000)
- `HUGGINGFACE_API_KEY`: API key for Hugging Face models (required only if using Hugging Face LLM provider)
- `APP_ENV`: Environment (development, production, test)

## 🚦 Error Handling

The platform provides two levels of error handling:

### 1. Basic Error Handling (Default)

When LLM provider is not configured, the system uses standard error handling:

```yaml
# Basic model configuration without LLM
id: simple-model
name: Simple Model
endpoint_url: http://localhost:8001
```

Features:

- HTTP status code-based error classification
- Automatic retries for 5xx errors
- Circuit breaker pattern for fault tolerance
- Exponential backoff with jitter
- Configurable retry limits and timeouts

### 2. Advanced LLM-Based Error Handling (Optional)

For more sophisticated error handling, you can add LLM provider configuration:

```yaml
# Model configuration with LLM-based error handling
id: advanced-model
name: Advanced Model
endpoint_url: http://localhost:8001
llm_provider:
  type: huggingface # or ollama
  model_name: mistralai/Mistral-7B-Instruct-v0.2
```

Features:

- Intelligent error classification using LLM
- Context-aware retry decisions
- Adaptive circuit breaker thresholds
- Detailed error analysis and reasoning
- Pattern-based error handling

### Error Handling Behavior

#### Without LLM Provider:

- Retries on 5xx server errors
- No retries on 4xx client errors
- Standard circuit breaker thresholds
- Basic error logging

#### With LLM Provider:

- Smart classification of errors (transient, permanent, rate limit, etc.)
- Adaptive retry strategies based on error context
- Dynamic circuit breaker adjustments
- Rich error context and analysis
- Pattern-based error handling

### Configuration

The error handling behavior is determined by the presence of the `llm_provider` field in your model configuration. You can mix and match models with and without LLM-based error handling in the same deployment.

### Environment Variables

The orchestrator service uses the following environment variables (configured in docker-compose.yml):

- `APP_NAME`: Application name (default: orchestrator)
- `APP_VERSION`: Application version (default: 1.0.0)
- `DEBUG`: Debug mode (default: true)
- `HOST`: Host to bind to (default: 0.0.0.0)
- `PORT`: Port to listen on (default: 8000)
- `HUGGINGFACE_API_KEY`: API key for Hugging Face models (required only if using Hugging Face LLM provider)
- `APP_ENV`: Environment (development, production, test)

## 🚦 Advanced LLM-Based Error Handling

### Overview

This project implements intelligent, LLM-based error handling and circuit breaker logic for all model API requests. The system uses language models to analyze errors, classify them, and make smart decisions about retries and circuit breaker behavior.

---

### Features

- **LLM-Based Error Classification:**

  - Uses LangChain and LiteLLM for intelligent error analysis
  - Classifies errors as transient, permanent, rate limit, or authentication issues
  - Adapts retry and circuit breaker behavior based on error context

- **Smart Retries:**

  - Retries are guided by LLM classification
  - Exponential backoff with jitter for rate limits
  - No retries for permanent errors
  - Configurable per model

- **Adaptive Circuit Breaker:**

  - Circuit breaker thresholds adjust based on LLM analysis
  - Tracks error patterns and context
  - Prevents cascading failures
  - Configurable per model

- **Enhanced Observability:**
  - Rich error context and classification
  - Detailed statistics and error patterns
  - Model-aware error handling

---

### Configuration

Each model in your configuration can specify:

```yaml
llm_provider:
  type: huggingface # or ollama
  model_name: mistralai/Mistral-7B-Instruct-v0.2
  timeout: 30
  max_retries: 3
  api_key: ${HUGGINGFACE_API_KEY}

circuit_breaker:
  failure_threshold: 5
  reset_timeout: 60.0
```

---

### API Endpoints

#### **Forward Request to Model**

- `POST /orchestrator/{model_id}`
  - Forwards a request to the specified model endpoint with LLM-based error handling

#### **Get Model Statistics**

- `GET /orchestrator/{model_id}/stats`

  - Returns detailed statistics including error classifications and patterns

  **Example Response:**

  ```json
  {
    "model_id": "my-model",
    "request_stats": {
      "total_requests": 42,
      "successful_requests": 35,
      "failed_requests": 7,
      "last_success": "2024-06-01T12:34:56.789Z",
      "last_failure": "2024-06-01T12:40:00.123Z"
    },
    "error_stats": {
      "classifications": {
        "transient": 3,
        "permanent": 2,
        "rate_limit": 2
      },
      "last_errors": {
        "transient": "2024-06-01T12:39:00.000Z",
        "permanent": "2024-06-01T12:40:00.123Z"
      }
    }
  }
  ```

---

### Testing

Comprehensive test suites are provided:

- `tests/test_utils/test_llm_error_handling.py`: Tests for LLM-based error handling
- `tests/test_services/test_proxy.py`: Tests for proxy service with error handling
- `tests/test_config/test_models_config.py`: Tests for model configuration

Run the tests with:

```bash
pytest -v
```

---

### Best Practices

- Use Hugging Face in production and Ollama in development
- Configure appropriate timeouts and retries per model
- Monitor error classifications and patterns
- Use environment variables for API keys
- Keep error handling configuration in sync with model capabilities

## Stopping the Application

```bash
# Stop the orchestrator
docker compose down

# Stop mock servers
# Press Ctrl+C in each terminal running a mock server
```

## Development

### Adding New Models

1. Create a new model configuration file in `config/models/`
2. Configure the LLM provider and error handling settings
3. Ensure the model server implements the required endpoints:
   - `GET /health`: Health check endpoint
   - `POST /predict`: Prediction endpoint

### Mock Server Development

The mock server (`mocks/model_mock.py`) can be customized to simulate different model behaviors:

- Modify the prediction response in the `predict` function
- Add new endpoints as needed
- Customize the model metadata

## Troubleshooting

1. If ports are already in use:

   - Check for running services: `lsof -i :<port>`
   - Stop conflicting services or use different ports

2. If the orchestrator can't connect to models:

   - Verify model configurations in `config/models/`
   - Check if model servers are running
   - Verify network connectivity between services

3. If LLM error handling is not working:
   - Check LLM provider configuration
   - Verify API keys are set correctly
   - Check logs for LLM-related errors

### Circuit Breaker Behavior

The system implements a circuit breaker pattern to prevent cascading failures and provide fault tolerance. The behavior differs between basic and LLM-based modes:

#### Basic Mode Circuit Breaker

```yaml
# Default circuit breaker settings (when not explicitly configured)
circuit_breaker:
  failure_threshold: 5 # Number of failures before opening
  reset_timeout: 60.0 # Seconds before attempting to close
  half_open_timeout: 30.0 # Seconds in half-open state
  success_threshold: 2 # Successful requests to close circuit
```

Behavior:

- Opens circuit after 5 consecutive failures
- Stays open for 60 seconds
- Moves to half-open state for 30 seconds
- Requires 2 successful requests to close
- Resets failure count on successful requests
- Applies to all 5xx errors equally

#### LLM-Based Mode Circuit Breaker

```yaml
# LLM-based circuit breaker with adaptive settings
circuit_breaker:
  failure_threshold: 5 # Base threshold, adjusted by LLM
  reset_timeout: 60.0 # Base timeout, adjusted by LLM
  half_open_timeout: 30.0 # Base half-open timeout
  success_threshold: 2 # Successful requests to close
  adaptive:
    enabled: true
    max_threshold: 10 # Maximum failure threshold
    min_threshold: 3 # Minimum failure threshold
    max_timeout: 300.0 # Maximum reset timeout
    min_timeout: 30.0 # Minimum reset timeout
```

Behavior:

- Adapts thresholds based on error classification:
  - Rate limits: Shorter timeouts, higher thresholds
  - Transient errors: Moderate timeouts, standard thresholds
  - Permanent errors: Longer timeouts, lower thresholds
- Tracks error patterns and context
- Adjusts circuit breaker parameters dynamically
- Provides detailed metrics and analysis
- Maintains separate counters for different error types

#### Circuit States

Both modes implement the standard circuit breaker states:

1. **Closed (Normal Operation)**

   - Requests flow normally
   - Failures are counted
   - Successes reset failure count

2. **Open (Failure Mode)**

   - Requests fail fast
   - No external calls made
   - Timer running for reset

3. **Half-Open (Recovery Mode)**
   - Limited requests allowed
   - Success moves to closed
   - Failure moves to open

#### Monitoring and Metrics

The system provides metrics for both modes:

```json
{
  "circuit_breaker": {
    "state": "closed",
    "failure_count": 0,
    "last_failure": "2024-03-14T12:00:00Z",
    "total_failures": 10,
    "total_successes": 100,
    "current_threshold": 5,
    "current_timeout": 60.0
  }
}
```

LLM-based mode includes additional metrics:

```json
{
  "circuit_breaker": {
    // ... basic metrics ...
    "error_classifications": {
      "rate_limit": 3,
      "transient": 5,
      "permanent": 2
    },
    "adaptive_settings": {
      "current_threshold": 7,
      "current_timeout": 90.0,
      "last_adjustment": "2024-03-14T12:00:00Z",
      "adjustment_reason": "Rate limit errors detected"
    }
  }
}
```

#### Circuit Breaker Scenarios

Here are examples of how the circuit breaker behaves in different error scenarios:

##### 1. Rate Limit Errors

```yaml
# Initial configuration
circuit_breaker:
  failure_threshold: 5
  reset_timeout: 60.0
  adaptive:
    enabled: true
    max_threshold: 10
    min_threshold: 3
```

Scenario:

```json
{
  "errors": [
    {
      "type": "rate_limit",
      "message": "Too many requests",
      "retry_after": 30
    }
  ],
  "circuit_breaker": {
    "before": {
      "threshold": 5,
      "timeout": 60.0
    },
    "after": {
      "threshold": 8, // Increased to handle rate limits
      "timeout": 30.0, // Reduced to match retry_after
      "reason": "Rate limit detected, increasing threshold and reducing timeout"
    }
  }
}
```

##### 2. Transient Network Errors

```yaml
# Initial configuration
circuit_breaker:
  failure_threshold: 5
  reset_timeout: 60.0
  adaptive:
    enabled: true
    max_threshold: 10
    min_threshold: 3
```

Scenario:

```json
{
  "errors": [
    {
      "type": "transient",
      "message": "Connection timeout",
      "retry_count": 2
    }
  ],
  "circuit_breaker": {
    "before": {
      "threshold": 5,
      "timeout": 60.0
    },
    "after": {
      "threshold": 6, // Slightly increased
      "timeout": 45.0, // Slightly reduced
      "reason": "Transient errors detected, moderate adjustment"
    }
  }
}
```

##### 3. Permanent Errors

```yaml
# Initial configuration
circuit_breaker:
  failure_threshold: 5
  reset_timeout: 60.0
  adaptive:
    enabled: true
    max_threshold: 10
    min_threshold: 3
```

Scenario:

```json
{
  "errors": [
    {
      "type": "permanent",
      "message": "Invalid API key",
      "code": 401
    }
  ],
  "circuit_breaker": {
    "before": {
      "threshold": 5,
      "timeout": 60.0
    },
    "after": {
      "threshold": 3, // Reduced to minimum
      "timeout": 120.0, // Increased significantly
      "reason": "Permanent error detected, reducing threshold and increasing timeout"
    }
  }
}
```

##### 4. Mixed Error Types

```yaml
# Initial configuration
circuit_breaker:
  failure_threshold: 5
  reset_timeout: 60.0
  adaptive:
    enabled: true
    max_threshold: 10
    min_threshold: 3
```

Scenario:

```json
{
  "errors": [
    {
      "type": "rate_limit",
      "message": "Too many requests",
      "retry_after": 30
    },
    {
      "type": "transient",
      "message": "Connection timeout",
      "retry_count": 1
    }
  ],
  "circuit_breaker": {
    "before": {
      "threshold": 5,
      "timeout": 60.0
    },
    "after": {
      "threshold": 7, // Balanced increase
      "timeout": 40.0, // Balanced timeout
      "reason": "Mixed errors detected, balanced adjustment based on error types"
    }
  }
}
```

##### 5. Recovery Scenarios

```json
{
  "circuit_breaker": {
    "state": "half-open",
    "test_requests": [
      {
        "status": "success",
        "latency": 150
      },
      {
        "status": "success",
        "latency": 145
      }
    ],
    "result": {
      "new_state": "closed",
      "reason": "Two successful requests in half-open state",
      "adjusted_settings": {
        "threshold": 5, // Reset to default
        "timeout": 60.0 // Reset to default
      }
    }
  }
}
```

##### 6. Basic Mode vs LLM Mode Comparison

Basic Mode:

```json
{
  "errors": [
    {
      "status": 503,
      "message": "Service unavailable"
    }
  ],
  "circuit_breaker": {
    "state": "open",
    "failure_count": 5,
    "timeout": 60.0,
    "reason": "Fixed threshold reached"
  }
}
```

LLM Mode:

```json
{
  "errors": [
    {
      "status": 503,
      "message": "Service unavailable",
      "llm_analysis": {
        "type": "transient",
        "confidence": 0.85,
        "suggested_action": "retry_with_backoff"
      }
    }
  ],
  "circuit_breaker": {
    "state": "open",
    "failure_count": 5,
    "timeout": 45.0,
    "reason": "Transient error pattern detected, reducing timeout for faster recovery",
    "llm_insights": {
      "error_pattern": "Intermittent service unavailability",
      "recommended_strategy": "Shorter timeout with higher threshold"
    }
  }
}
```

### Complete Configuration Example

Here's a complete example of a model configuration with all available options:

```yaml
# config/models/example-model.yaml

# Basic model configuration (required)
id: example-model
name: Example Model
endpoint_url: http://localhost:8001

# Error handling configuration
error_handling:
  # Basic error handling (always enabled)
  basic:
    enabled: true
    max_retries: 3
    retry_delay: 1.0
    max_retry_delay: 30.0
    backoff_factor: 2.0

  # LLM-based error handling (optional)
  llm:
    enabled: false # Set to true to enable LLM-based handling
    provider:
      type: huggingface # or ollama
      model_name: mistralai/Mistral-7B-Instruct-v0.2
      timeout: 30
      max_retries: 3
      api_key: ${HUGGINGFACE_API_KEY} # Uses environment variable

# Circuit breaker configuration
circuit_breaker:
  # Basic settings (always enabled)
  basic:
    enabled: true
    failure_threshold: 5 # Number of failures before opening
    reset_timeout: 60.0 # Seconds before attempting to close
    half_open_timeout: 30.0 # Seconds in half-open state
    success_threshold: 2 # Successful requests to close circuit

  # LLM-based circuit breaker (optional)
  llm:
    enabled: false # Set to true to enable LLM-based circuit breaker
    max_threshold: 10 # Maximum failure threshold
    min_threshold: 3 # Minimum failure threshold
    max_timeout: 300.0 # Maximum reset timeout
    min_timeout: 30.0 # Minimum reset timeout

    # Error type specific settings
    error_types:
      rate_limit:
        threshold_multiplier: 1.5
        timeout_multiplier: 0.5
      transient:
        threshold_multiplier: 1.2
        timeout_multiplier: 0.8
      permanent:
        threshold_multiplier: 0.6
        timeout_multiplier: 2.0

# Monitoring configuration
monitoring:
  enabled: true
  metrics_interval: 60 # Seconds between metrics collection
  log_level: INFO # DEBUG, INFO, WARNING, ERROR
  alert_threshold: 0.8 # Alert when error rate exceeds 80%

# Request configuration
request:
  timeout: 30 # Request timeout in seconds
  max_retries: 3 # Maximum number of retries
  retry_delay: 1.0 # Initial retry delay in seconds
  max_retry_delay: 30.0 # Maximum retry delay in seconds
  backoff_factor: 2.0 # Exponential backoff factor

# Health check configuration
health_check:
  enabled: true
  interval: 30 # Seconds between health checks
  timeout: 5 # Health check timeout in seconds
  failure_threshold: 3 # Number of failures before marking unhealthy
  success_threshold: 2 # Number of successes before marking healthy

# Logging configuration
logging:
  level: INFO # DEBUG, INFO, WARNING, ERROR
  format: json # json or text
  include_metadata: true # Include request/response metadata
  sensitive_fields: # Fields to mask in logs
    - api_key
    - password
    - token
```

This configuration provides:

1. **Error Handling**

   - Basic error handling (always enabled)
   - Optional LLM-based error handling
   - Consistent configuration structure

2. **Circuit Breaker**

   - Basic circuit breaker (always enabled)
   - Optional LLM-based circuit breaker
   - Error-type specific adjustments

3. **Monitoring**

   - Metrics collection
   - Alerting thresholds
   - Logging configuration

4. **Request Handling**

   - Timeout and retry settings
   - Backoff strategy configuration

5. **Health Monitoring**
   - Health check intervals
   - Failure and success thresholds

The error handling and circuit breaker will:

- Always use basic error handling and circuit breaker
- Optionally use LLM-based features when enabled
- Provide consistent behavior across both modes
- Allow for easy switching between basic and LLM-based handling
