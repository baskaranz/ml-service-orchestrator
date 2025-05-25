# Model Registration Guide

This document explains how to register and manage models in the ML Service Orchestrator.

## 📋 Registration Methods

### 1. YAML Configuration (Recommended for Production)

Persist model configurations using YAML files in the environment-specific models directory. The orchestrator automatically loads models from the appropriate directory based on the `APP_ENV` environment variable.

**Directory Structure:**
```
config/
├── local/  # For local development (default)
│   └── models/
│       ├── model1.yaml
│       └── model2.yaml
├── test/   # For testing environment
│   └── models/
├── dev/    # For development environment
│   └── models/
└── prod/   # For production environment
    └── models/
```

**Example:** `config/local/models/sentiment-analyzer.yaml`
```yaml
# Required fields
id: sentiment-analyzer
name: "Sentiment Analysis"
description: "Analyzes text sentiment"
endpoint_url: "http://sentiment-service:8000/predict"
active: true

# Platform configuration
platform:
  name: "rest"
  config:
    # Request settings
    timeout: 30  # seconds
    max_retries: 3
    
    # Health check configuration
    health_check:
      enabled: true
      endpoint: "/health"
      interval: 30  # seconds
      timeout: 5    # seconds
      failure_threshold: 3
      success_threshold: 1
    
    # Circuit breaker settings
    circuit_breaker:
      enabled: true
      failure_threshold: 5
      reset_timeout: 30  # seconds
      half_open_timeout: 30  # seconds
      success_threshold: 2
```

### 2. API Registration (For Development/Testing)

Register models at runtime using the REST API (in-memory only, not persisted).

**Endpoint:** `POST /api/v1/models`

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/models' \
  -H 'X-API-Key: your-api-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "sentiment-analyzer",
    "name": "Sentiment Analysis",
    "endpoint_url": "http://sentiment-service:8000/predict",
    "active": true,
    "platform": {
      "name": "rest",
      "config": {
        "timeout": 30,
        "max_retries": 3
      }
    }
  }'
```

## 🔄 Method Comparison

| Feature                     | API Registration | YAML Registration |
|-----------------------------|-----------------|-------------------|
| **Persistence**            | ❌ In-memory only | ✅ Persistent     |
| **Requires Restart**       | ❌ No            | ✅ Yes            |
| **Version Control**        | ❌ No            | ✅ Yes            |
| **Dynamic Updates**        | ✅ Instant       | ❌ File change + restart |
| **Ideal For**              | Testing, Dynamic environments | Production, Stable configs |

## 🛠️ Managing Registered Models

### List All Models
```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/models' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your-api-key'
```

### Get Model Details
```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/models/sentiment-analyzer' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your-api-key'
```

### Update a Model (API Registration Only)
```bash
curl -X 'PUT' \
  'http://localhost:8000/api/v1/models/sentiment-analyzer' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your-api-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "endpoint_url": "http://new-sentiment-service:8000/predict",
    "active": true
  }'
```

### Delete a Model (API Registration Only)
```bash
curl -X 'DELETE' \
  'http://localhost:8000/api/v1/models/sentiment-analyzer' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your-api-key'
```

## 📝 Best Practices

1. **Use Environment-Specific Configurations**: Store model configurations in the appropriate environment directory (`config/{env}/models/`).

2. **Docker Networking Awareness**: When running the orchestrator on the host and models in Docker containers:
   - Use `http://localhost:{PORT}` in model configurations for host-to-container communication
   - Use `http://{container-name}:{PORT}` for container-to-container communication
   - Use the `configure-models-host` and `configure-models-docker` Makefile targets to switch between these modes

3. **Version Control**: Keep model configurations in version control to track changes.

4. **Validation**: Always validate model configurations before deploying to production.

5. **Circuit Breaker Configuration**: Configure appropriate circuit breaker settings to prevent cascading failures.

6. **Health Checks**: Enable health checks for all models to ensure they are operational.

## 📋 Registration Methods

### 1. YAML Configuration (Recommended for Production)

Persist model configurations using YAML files in the `config/models/` directory.

**Example:** `config/models/sentiment-analyzer.yaml`
```yaml
# Required fields
id: sentiment-analyzer
name: "Sentiment Analysis"
description: "Analyzes text sentiment"
endpoint_url: "http://sentiment-service:8000/predict"
active: true

# Platform configuration
platform:
  name: "rest"
  config:
    # Request settings
    timeout: 30  # seconds
    max_retries: 3
    
    # Health check configuration
    health_check:
      enabled: true
      endpoint: "/health"
      interval: 30  # seconds
      timeout: 5    # seconds
      failure_threshold: 3
      success_threshold: 1
    
    # Circuit breaker settings
    circuit_breaker:
      enabled: true
      failure_threshold: 5
      reset_timeout: 30  # seconds
      half_open_timeout: 30  # seconds
      success_threshold: 2
```

### 2. API Registration (For Development/Testing)

Register models at runtime using the REST API (in-memory only, not persisted).

**Endpoint:** `POST /api/v1/models`

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/models' \
  -H 'X-API-Key: your-api-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "sentiment-analyzer",
    "name": "Sentiment Analysis",
    "endpoint_url": "http://sentiment-service:8000/predict",
    "active": true,
    "platform": {
      "name": "rest",
      "config": {
        "timeout": 30,
        "max_retries": 3
      }
    }
  }'
```

## 🔄 Method Comparison

| Feature                     | API Registration | YAML Registration |
|-----------------------------|-----------------|-------------------|
| **Persistence**            | ❌ In-memory only | ✅ Persistent     |
| **Requires Restart**       | ❌ No            | ✅ Yes            |
| **Version Control**        | ❌ No            | ✅ Yes            |
| **Dynamic Updates**        | ✅ Instant       | ❌ File change + restart |
| **Ideal For**              | Testing, Dynamic environments | Production, Stable configs |

## 🛠️ Managing Registered Models

### List All Models
```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/models' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your-api-key'
```

### Get Model Details
```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/models/sentiment-analyzer' \
  -H 'accept: application/json' \
  -H 'X-API-Key: your-api-key'
```

### Update a Model (API Registration Only)
```bash
curl -X 'PATCH' \
  'http://localhost:8000/api/v1/models/sentiment-analyzer' \
  -H 'X-API-Key: your-api-key' \
  -H 'Content-Type: application/json' \
  -d '{"endpoint_url": "http://new-endpoint:8000/predict"}'
```

### Delete a Model (API Registration Only)
```bash
curl -X 'DELETE' \
  'http://localhost:8000/api/v1/models/sentiment-analyzer' \
  -H 'X-API-Key: your-api-key'
```

## 🔄 Reloading Models

To reload models from the configuration files without restarting the service:

```bash
curl -X 'POST' \
  'http://localhost:8000/refresh' \
  -H 'X-API-Key: your-api-key'
```

## 🏗️ Best Practices

1. **Use Environment Variables** in YAML files for sensitive data:
   ```yaml
   endpoint_url: ${SENTIMENT_SERVICE_URL}
   ```

2. **Enable Health Checks** for critical models to monitor their availability

3. **Use Circuit Breakers** to prevent cascading failures

4. **Version Control** your YAML configurations for better change management

5. **Document** each model's expected input/output format in the description field

6. **Test** model configurations in a staging environment before deploying to production

7. **Monitor** model health and performance metrics

8. **Rotate** API keys and credentials regularly
   ```yaml
   auth:
     type: "api_key"
     config:
       header_name: "X-API-Key"
       api_key: "${MODEL_API_KEY}"  # Use environment variables
   ```

2. **Health Checks**:
   ```yaml
   platform:
     config:
       health_check:
         endpoint: "/health"
         interval: 30
         timeout: 5
   ```

3. **Circuit Breaking**:
   ```yaml
   circuit_breaker:
     failure_threshold: 5
     reset_timeout: 60
   ```

4. **Monitoring**:
   - Track request latency
   - Monitor error rates
   - Set up alerts for failures

## Example: Complete Model Configuration

```yaml
id: image-classifier
name: "Image Classification"
description: "Classifies images into categories"
version: "2.1.0"
endpoint_url: "${IMAGE_API_ENDPOINT}"
active: true
platform:
  name: "rest"
  config:
    timeout: 60
    max_retries: 2
    health_check:
      endpoint: "/health"
      interval: 30
      timeout: 5
      failure_threshold: 3

circuit_breaker:
  failure_threshold: 5
  reset_timeout: 300
  half_open_timeout: 30
  success_threshold: 2

auth:
  type: "api_key"
  config:
    header_name: "X-API-Key"
    api_key: "${IMAGE_API_KEY}"

metadata:
  owner: "ml-team"
  environment: "production"
  contact: "ml-team@example.com"
```

## Security Considerations

1. Always use HTTPS for API endpoints
2. Rotate API keys regularly
3. Implement proper authentication/authorization
4. Use environment variables for sensitive data
5. Set appropriate CORS policies

## Troubleshooting

- **Model not found**: Verify the model ID and registration status
- **Connection errors**: Check endpoint URL and network connectivity
- **Authentication failures**: Verify API keys and authentication headers
- **Timeouts**: Adjust timeout values in the platform configuration
