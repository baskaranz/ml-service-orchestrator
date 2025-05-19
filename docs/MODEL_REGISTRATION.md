# Model Registration Guide

This document explains the different methods available for registering models with the ML Service Orchestrator.

## Registration Methods

### 1. Dynamic API Registration

Register models at runtime using the REST API without any configuration files.

**Endpoint:**
```
POST /admin/register-model
```

**Example Request:**
```bash
curl -X POST http://your-orchestrator:8000/admin/register-model \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "id": "sentiment-analyzer",
      "name": "Sentiment Analysis",
      "endpoint_url": "https://api.example.com/predict",
      "active": true,
      "platform": {
        "name": "rest",
        "config": {
          "timeout": 30,
          "max_retries": 3
        }
      }
    }
  }'
```

### 2. YAML File Registration

Persist model configurations using YAML files in the `config/models/` directory. The main application configuration is in `config/app.cfg`.

**Example Model Config:** `config/models/sentiment-analyzer.yaml`
**Main Config:** `config/app.cfg`
```yaml
id: sentiment-analyzer
name: "Sentiment Analysis"
description: "Analyzes text sentiment"
version: "1.0.0"
endpoint_url: "https://api.example.com/predict"
active: true
platform:
  name: "rest"
  config:
    timeout: 30
    max_retries: 3
    health_check:
      endpoint: "/health"
      interval: 30
      timeout: 5
      failure_threshold: 3
```

## Method Comparison

| Feature                     | API Registration | YAML Registration |
|-----------------------------|-----------------|-------------------|
| **Persistence**            | ❌ In-memory only | ✅ Persistent      |
| **Requires Restart**       | ❌ No            | ✅ Yes             |
| **Version Control**        | ❌ No            | ✅ Yes             |
| **Dynamic Updates**        | ✅ Instant       | ❌ File change + restart |
| **Ideal For**              | Testing, Dynamic environments | Production, Stable configs |

## Managing Registered Models

### List All Models
```bash
curl -H "X-API-Key: your-admin-key" http://your-orchestrator:8000/admin/models
```

### Get Model Details
```bash
curl -H "X-API-Key: your-admin-key" http://your-orchestrator:8000/admin/models/{model_id}
```

### Update a Model
```bash
curl -X PUT http://your-orchestrator:8000/admin/models/{model_id} \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"model": {"endpoint_url": "https://new-endpoint.example.com"}}'
```

### Delete a Model
```bash
curl -X DELETE http://your-orchestrator:8000/admin/models/{model_id} \
  -H "X-API-Key: your-admin-key"
```

## Best Practices

1. **Environment Variables**:
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
