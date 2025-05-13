# ML Model Orchestrator

A FastAPI-based service for orchestrating multiple ML model predictions.

## Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- Virtual environment (recommended)
- Hugging Face API key (for production) or Ollama (for development)

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
# Basic configuration (required)
id: model-name
name: Model Name
endpoint_url: http://localhost:8001
type: classification

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

3. If LLM error handling is not working:
   - Check LLM provider configuration
   - Verify API keys are set correctly
   - Check logs for LLM-related errors
