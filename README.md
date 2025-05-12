# ML Model Orchestrator

A FastAPI-based service for orchestrating multiple ML model predictions.

## Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- Virtual environment (recommended)

## Running the Application

### 1. Start the Orchestrator

The orchestrator service runs in Docker and is model-agnostic. It will automatically discover and use any models configured in the `config/models` directory.

```bash
# Start the orchestrator service
docker compose up -d
```

### 2. Running Mock Models (for Testing)

For testing purposes, you can run mock model servers locally. The mock servers simulate ML model behavior and are useful for development and testing.

```bash
# Start mock model 1 (in a new terminal)
cd app/mocks
python model_mock.py --port 8001 --model-name model-1-mock

# Start mock model 2 (in another terminal)
cd app/mocks
python model_mock.py --port 8002 --model-name model-2-mock
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

Model configurations are stored in the `config/models` directory. Each model should have its own YAML configuration file with the following structure:

```yaml
name: model-name
version: 1.0.0
description: Model description
endpoint: http://localhost:8001 # Model server endpoint
health_check: /health
prediction_endpoint: /predict
timeout: 30
retry_count: 3
retry_delay: 1
```

### Environment Variables

The orchestrator service uses the following environment variables (configured in docker-compose.yml):

- `APP_NAME`: Application name (default: orchestrator)
- `APP_VERSION`: Application version (default: 1.0.0)
- `DEBUG`: Debug mode (default: true)
- `HOST`: Host to bind to (default: 0.0.0.0)
- `PORT`: Port to listen on (default: 8000)

## 🚦 Advanced Error Handling, Retries, and Circuit Breaker

### Overview

This project implements robust, async-compatible error handling and circuit breaker logic for all model API requests. The system is designed to maximize reliability, observability, and resilience against transient and persistent failures.

---

### Features

- **Configurable Retries:**  
  Each model can specify its own `max_retries` and timeout settings. Retries use exponential backoff and optional jitter to avoid thundering herd problems.

- **Async Circuit Breaker:**  
  Each model is protected by a circuit breaker that tracks failures and automatically opens to prevent repeated failed requests from overwhelming the system.

  - Circuit breaker settings (failure threshold, reset timeout, excluded exceptions) are configurable per model.

- **Centralized Error Handling:**  
  All errors are logged, categorized, and tracked. The system distinguishes between transient errors (which can be retried) and permanent errors (which are not retried).

- **Model Statistics Endpoint:**  
  Query real-time statistics for any model, including request counts, error rates, and last success/failure times.

---

### Configuration

Each model in your configuration can specify:

```yaml
max_retries: 3
timeout: 10.0
circuit_breaker:
  failure_threshold: 5
  reset_timeout: 60.0
  exclude_exceptions:
    - ValueError
```

---

### API Endpoints

#### **Forward Request to Model**

- `POST /orchestrator/{model_id}`
  - Forwards a request to the specified model endpoint with full error handling and circuit breaker protection.

#### **Get Model Statistics**

- `GET /orchestrator/{model_id}/stats`

  - Returns statistics and error handling information for the specified model.

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
      "counts": {
        "TimeoutError": 3,
        "HTTPStatusError": 4
      },
      "last_errors": {
        "TimeoutError": "2024-06-01T12:39:00.000Z",
        "HTTPStatusError": "2024-06-01T12:40:00.123Z"
      }
    }
  }
  ```

---

### Testing

A comprehensive test script is provided at `app/scripts/test_error_handling.py`:

- Simulates both transient and persistent failures.
- Verifies retry logic, error handling, and statistics tracking.
- Can be used as a template for future tests.

Run the test with:

```bash
python -m app.scripts.test_error_handling
```

---

### Best Practices

- Use async functions for all I/O-bound operations.
- Configure circuit breaker and retry settings per model for optimal resilience.
- Monitor the statistics endpoint to track model health and error rates.

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
2. Ensure the model server implements the required endpoints:
   - `GET /health`: Health check endpoint
   - `POST /predict`: Prediction endpoint

### Mock Server Development

The mock server (`app/mocks/model_mock.py`) can be customized to simulate different model behaviors:

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
