# ML Service Orchestrator

A high-performance, production-ready FastAPI service for orchestrating and managing multiple ML model predictions with built-in fault tolerance, circuit breakers, health monitoring, and dynamic model registration.

> **Latest Update (May 2024)**: Enhanced circuit breaker implementation with improved error handling and test coverage. Added support for dynamic model registration and health checks.

## 🌟 Features

- **Model Agnostic**: Support for any ML model with a REST API
- **Dynamic Model Registration**: Register and unregister models at runtime
- **Health Monitoring**: Built-in health checks with detailed system and model status
- **Metrics Collection**: System and model-level metrics via API endpoints
- **Circuit Breakers**: Intelligent circuit breaking with configurable thresholds and timeouts
- **Error Handling**: Comprehensive error handling with retry mechanisms and fallback strategies
- **Logging**: Structured JSON logging with configurable levels and sensitive data masking
- **Testing**: Comprehensive test suite with 90%+ code coverage
- **API Documentation**: Full OpenAPI/Swagger documentation
- **Containerized**: Ready for Docker and Kubernetes deployment
- **Secure**: API key authentication and request validation

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- Virtual environment (recommended)
- For HTTP/2 support: `pip install 'httpx[http2]'`

### Environment Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/ml-service-orchestrator.git
   cd ml-service-orchestrator
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   .venv/bin/python -m app.main
   ```

## 🏃 Running the Application

### 1. Start the Orchestrator

The orchestrator service runs in Docker and automatically discovers models configured in the environment-specific directory (e.g., `config/local/models/` for local development).

```bash
# Clone the repository (if not already cloned)
git clone https://github.com/baskaranz/ml-service-orchestrator.git
cd ml-service-orchestrator

# Start the orchestrator service with Docker Compose
docker-compose up -d orchestrator

# Or for development with hot-reload
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Development Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. Run tests:
   ```bash
   # Run all tests
   pytest

   # Run tests with coverage
   pytest --cov=app --cov-report=term-missing

   # Run a specific test file
   pytest tests/test_core/test_orchestrator.py -v
   ```

### 2. Run Mock Models (for Testing)

For testing, you can run mock model servers that simulate ML model behavior using the Makefile commands:

```bash
# Start all mock models
make mock-up

# Stop mock models
make mock-down
```

Or use the scripts directly:

```bash
# Start mock model 1 on port 8001
./scripts/start_mock_model.sh mock-model-1 8001

# Start mock model 2 on port 8002
./scripts/start_mock_model.sh mock-model-2 8002
```

### 3. Configure Docker Networking

When running the orchestrator and mock models, you need to configure the model endpoints based on your deployment scenario:

#### Host-to-Container Communication

When running the orchestrator on the host and mock models in Docker containers:

```bash
# Configure models for host-to-container communication
make configure-models-host
```

This updates model configurations to use `http://localhost:{PORT}` endpoints (e.g., `http://localhost:8001` for mock-model-1).

#### Container-to-Container Communication

When running both the orchestrator and models in Docker containers:

```bash
# Configure models for container-to-container communication
make configure-models-docker
```

This updates model configurations to use `http://{container-name}:{PORT}` endpoints (e.g., `http://mock-model-1:8000`).


### 4. Verify Services

Check if all services are running correctly:

```bash
# Check orchestrator health
curl http://localhost:8000/health

# Check mock model 1 health
curl http://localhost:8001/health

# View API documentation (after starting the orchestrator)
open http://localhost:8000/docs
```

### 5. Test Predictions

Test the prediction endpoints using the orchestrator:

```bash
# Get list of registered models
curl -X 'GET' \
  'http://localhost:8000/api/v1/models' \
  -H 'accept: application/json'

# Make a prediction with mock-model-1
curl -X 'POST' \
  'http://localhost:8000/api/v1/models/mock-model-1' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"input": "Sample input text"}'

# Check model health status
curl -X 'GET' \
  'http://localhost:8000/api/v1/models/mock-model-1/health' \
  -H 'accept: application/json'
```

**Note**: The mock models expect a JSON payload with a key `input` (e.g., `{"input": "some_string"}`). Using a different format like `{"data": ...}` will cause a validation error.

## 📊 Monitoring and Metrics

The ML Service Orchestrator provides comprehensive monitoring capabilities:

### System Metrics

- **Model Statistics**: Number of loaded models, active models
- **Resource Usage**: HTTP client connections, error handlers
- **Performance Metrics**: Request latencies, success/failure rates

### Health Checks

- **Endpoint**: `GET /health`
- **Response**:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2024-05-26T02:30:00Z",
    "components": {
      "database": {"status": "healthy"},
      "model_registry": {"status": "healthy"}
    }
  }
  ```

### Model Metrics

- **Endpoint**: `GET /metrics`
- **Response**:
  ```json
  {
    "system": {
      "models_loaded": 3,
      "active_models": ["model-1", "model-2"],
      "http_clients": 2,
      "error_handlers": 2
    },
    "models": {
      "model-1": {
        "active": true,
        "endpoint": "http://model-1:8000",
        "timeout": 30.0,
        "max_retries": 3,
        "has_error_handler": true,
        "has_http_client": true
      }
    }
  }
  ```

### Logging

- **Structured JSON** logging by default
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Automatic masking of sensitive fields (API keys, tokens, etc.)
- Request/response metadata included in logs

## ⚙️ Configuration

### Model Registration

Models can be registered in multiple ways:

1. **YAML Configuration Files** (Recommended for production)
   - Place model configs in the environment-specific directory (e.g., `config/local/models/` for local development)
   - Automatically loaded at startup
   - Supports hot-reloading with `POST /refresh` endpoint
   - Example YAML structure:
     ```yaml
     id: sentiment-analyzer
     name: Sentiment Analysis Model
     endpoint_url: http://mock-model-1:8000
     active: true
     timeout: 30.0

     # Circuit breaker configuration
     circuit_breaker:
       failure_threshold: 5
       reset_timeout: 60
       half_open_timeout: 30
       success_threshold: 2

     # Health check configuration
     health_check:
       endpoint: /health
       interval: 30
       timeout: 5
       failure_threshold: 3
     ```

2. **Environment Variables**
   - Set `MODEL_CONFIG_DIR` to specify custom model config directory
   - Example: `export MODEL_CONFIG_DIR=config/local/models`

3. **Docker Environment**
   - Mount model configs as volumes in Docker
   - Example in docker-compose.yml:
     ```yaml
     volumes:
       - ./config/local/models:/app/config/local/models
     ```

2. **API Registration** (For dynamic environments)
   - Register models at runtime via API
   - Lost on service restart unless persisted

### Model Configuration

Each model requires a YAML configuration file in the environment-specific directory (e.g., `config/local/models/`):

```yaml
# Required fields
id: sentiment-analyzer
name: Sentiment Analysis Model
endpoint_url: http://mock-model-1:8000
active: true

# Platform configuration
platform:
  name: rest
  config:
    timeout: 30  # seconds
    max_retries: 3

    # Health check configuration
    health_check:
      enabled: true
      endpoint: /health
      interval: 30
      timeout: 5
      failure_threshold: 3

    # Circuit breaker settings
    circuit_breaker:
      enabled: true
      failure_threshold: 5
      reset_timeout: 30
      half_open_timeout: 30
      success_threshold: 2
```

### Environment Variables

Configure the orchestrator using these environment variables:

```ini
# Application
APP_NAME=ml-orchestrator
APP_ENV=development  # development, staging, production
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Model defaults
DEFAULT_TIMEOUT=30.0
DEFAULT_MAX_RETRIES=3

# Security
API_KEYS=your-api-key-1,your-api-key-2

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Configuration Precedence

1. Environment variables (highest priority)
2. `.env` file in project root
3. Default values in code (lowest priority)

## 📚 API Documentation

### Interactive Documentation

Access the interactive API documentation when the service is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `GET /api/v1/models` | GET | List all registered models | None |
| `POST /api/v1/models/{model_id}` | POST | Submit prediction request | API Key |
| `GET /api/v1/models/{model_id}/health` | GET | Get model health status | None |
| `GET /health` | GET | Basic health check | None |
| `GET /health/details` | GET | Detailed health information | None |
| `POST /refresh` | POST | Reload model configurations | API Key |

### Authentication

Secure your API endpoints using API key authentication. Include the API key in the `X-API-Key` header:

```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/models' \
  -H 'X-API-Key: your-api-key' \
  -H 'accept: application/json'
```

## 🚀 Deployment

### Docker Deployment

1. Build the container:
   ```bash
   docker build -t ml-orchestrator:latest .
   ```

2. Run the container:
   ```bash
   docker run -d \
     --name ml-orchestrator \
     -p 8000:8000 \
     -v $(pwd)/config:/app/config \
     --env-file .env \
     ml-orchestrator:latest
   ```

### Kubernetes Deployment

1. Create a namespace:
   ```bash
   kubectl create namespace ml-orchestrator
   ```

2. Create a secret for API keys:
   ```bash
   kubectl -n ml-orchestrator create secret generic ml-orchestrator-secrets \
     --from-literal=API_KEYS='your-api-key-1,your-api-key-2'
   ```

3. Deploy the application:
   ```bash
   kubectl -n ml-orchestrator apply -f k8s/
   ```

4. Access the service:
   ```bash
   kubectl -n ml-orchestrator port-forward svc/ml-orchestrator 8000:8000
   ```

## 📚 Additional Documentation

- [API Specification](docs/api/orchestrator-api.yaml) - Complete OpenAPI 3.1 specification
- [Platform Configuration](docs/platform-configuration.md) - Detailed configuration options
- [Model Registration](docs/model-registration.md) - Guide to registering models
- [YAML Model Registration](docs/yaml-model-registration.md) - Detailed guide for YAML-based model configuration
- [Run Instructions](docs/run-instructions.md) - Detailed guide for running the orchestrator
- [Docker Deployment](docs/docker-deployment.md) - Comprehensive guide for Docker deployment, including image building and Docker Compose
- [End-to-End Testing](docs/end-to-end-testing-guide.md) - Testing guide

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

## 🌐 HTTP/2 Configuration

The orchestrator supports both HTTP/1.1 (default) and HTTP/2 for model communication.

### Default Behavior
- Uses HTTP/1.1 by default for maximum compatibility
- No additional dependencies required

### Enabling HTTP/2
To use HTTP/2 with models that support it:

1. Install the required dependency:
   ```bash
   pip install 'httpx[http2]'
   ```

2. Enable HTTP/2 in your model configuration:
   ```yaml
   http2: true  # Only if your model server supports HTTP/2
   ```

### When to Use HTTP/2
- **Use HTTP/2** when connecting to modern model servers that support it
- **Stick with HTTP/1.1** for:
  - Testing environments
  - Servers without HTTP/2 support
  - When you want to minimize dependencies

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

### Monitoring Development

To add custom metrics or monitoring:

1. **Add Custom Metrics**:
   ```python
   # In your service class
   from prometheus_client import Counter, Gauge
   
   REQUESTS_TOTAL = Counter('myapp_requests_total', 'Total requests')
   ACTIVE_USERS = Gauge('myapp_active_users', 'Number of active users')
   
   # In your endpoint
   @app.get("/my-endpoint")
   def my_endpoint():
       REQUESTS_TOTAL.inc()
       ACTIVE_USERS.set(42)
       return {"status": "ok"}
   ```

2. **Enable Prometheus Metrics** (if using Prometheus):
   ```python
   from prometheus_fastapi_instrumentator import Instrumentator
   
   app = FastAPI()
   Instrumentator().instrument(app).expose(app)
   ```

### Code Style and Quality

1. Create a new model configuration file in the environment-specific directory (e.g., `config/local/models/`)
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

   - Verify model configurations in the environment-specific directory (e.g., `config/local/models/`)
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
# config/local/models/example-model.yaml

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
