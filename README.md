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
