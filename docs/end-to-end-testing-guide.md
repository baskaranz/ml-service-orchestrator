# 🧪 End-to-End Testing Guide

This guide provides comprehensive instructions for testing the ML Service Orchestrator with mock models in both Docker and local development environments.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- `curl` command line tool
- `jq` for JSON pretty-printing (optional but recommended)
  ```bash
  # On macOS
  brew install jq

  # On Ubuntu/Debian
  sudo apt-get install jq
  ```

> **Note:** Before proceeding with end-to-end testing, make sure you have set up your mock models.
> Refer to the [Mock Model Setup Guide](../mock-model-setup-guide.md) for detailed instructions on
> creating and configuring mock models for testing.

## 🐳 Docker Testing Environment

### 1. Start Mock Models

We'll use Docker Compose to start mock model services:

```bash
# Start mock models in detached mode
docker-compose -f mocks/docker-compose.yml up -d
```

This starts three mock models:
- `mock-model-1` on port 8001
- `mock-model-2` on port 8002
- `mock-model-3` on port 8003

### 2. Verify Mock Models

Check that all mock models are running:

```bash
# Check health of mock models
curl -s http://localhost:8001/health | jq
curl -s http://localhost:8002/health | jq
curl -s http://localhost:8003/health | jq
```

### 3. Start the Orchestrator

```bash
# Start the orchestrator service
docker-compose up -d orchestrator

# Or run locally (from project root)
python -m app.main
```

## 🧪 Running Tests

### 1. Test API Endpoints

```bash
# Check orchestrator health (basic)
curl -s http://localhost:8000/api/v1/health | jq

# Get detailed health information
curl -s http://localhost:8000/api/v1/health/details | jq

# List registered models
curl -s http://localhost:8000/api/v1/models | jq

# Make a prediction
curl -X 'POST' \
  'http://localhost:8000/api/v1/models/mock-model-1' \
  -H 'Content-Type: application/json' \
  -d '{"input": "This is a test"}' | jq

# Check model health
curl -s http://localhost:8000/api/v1/health/models/mock-model-1 | jq
```

### 2. Test Error Scenarios

```bash
# Non-existent model
curl -X 'POST' \
  'http://localhost:8000/api/v1/models/non-existent-model' \
  -H 'Content-Type: application/json' \
  -d '{"input": "test"}' | jq

# Invalid request format
curl -X 'POST' \
  'http://localhost:8000/api/v1/models/mock-model-1' \
  -H 'Content-Type: application/json' \
  -d '{"wrong_key": "test"}' | jq
```

## 🛠️ Local Development Testing

### 1. Set Up Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```ini
# Application
APP_ENV=development
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000

# API Keys (for protected endpoints)
API_KEYS=test-key-1,test-key-2
```

### 3. Run Tests

```bash
# Run unit tests
pytest tests/

# Run with coverage report
pytest --cov=app --cov-report=term-missing tests/
```

## 🧹 Clean Up

When you're done testing:

```bash
# Stop and remove all containers
docker-compose down

# Remove unused resources
docker system prune -f

# Deactivate virtual environment (if using)
deactivate
```

## 🔄 Testing with HTTP/2 (Optional)

The orchestrator supports HTTP/2 for model requests. To enable:

1. Install the HTTP/2 dependencies:
   ```bash
   pip install 'httpx[http2]'
   ```

2. Update the model configuration:
   ```yaml
   platform:
     name: rest
     config:
       http2: true
   ```

Note: The orchestrator will automatically fall back to HTTP/1.1 if HTTP/2 is not supported.

## 📊 Health Check Endpoints

The orchestrator provides several endpoints to monitor its health and performance:

```bash
# Basic health check
curl -s http://localhost:8000/api/v1/health | jq

# Detailed health information
curl -s http://localhost:8000/api/v1/health/details | jq

# Check health of a specific model
curl -s http://localhost:8000/api/v1/health/models/mock-model-1 | jq
```

## 🔍 Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure all services are running and accessible on the expected ports.
2. **Model Not Found**: Verify the model ID is correct and the model is registered in the orchestrator.
3. **Health Check Failures**: Check the logs for detailed error messages and ensure all dependencies are running.
4. **CORS Issues**: If you encounter CORS errors, verify the CORS configuration in the orchestrator settings.

### Viewing Logs

```bash
# View orchestrator logs
docker-compose logs -f orchestrator

# View mock model logs
docker-compose -f mocks/docker-compose.yml logs -f
```

### Debugging with cURL

For more detailed debugging, use the `-v` flag with cURL to see request/response headers and status codes:

```bash
curl -v http://localhost:8000/api/v1/health
```
