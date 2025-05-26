# YAML Model Registration Guide

This guide explains how to register and manage models using YAML configuration files with the ML Service Orchestrator.

## Table of Contents
- [File Structure](#file-structure)
- [Configuration Format](#configuration-format)
- [Required Fields](#required-fields)
- [Example Configurations](#example-configurations)
- [Loading Mechanism](#loading-mechanism)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## File Structure

Model configurations should be placed in environment-specific directories with `.yaml` or `.yml` extensions. The orchestrator uses the `APP_ENV` environment variable to determine which directory to load configurations from.

```
config/
├── local/  # For local development (default)
│   └── models/
│       ├── sentiment-analyzer.yaml
│       └── image-classifier.yaml
├── test/   # For testing environment
│   └── models/
├── dev/    # For development environment
│   └── models/
└── prod/   # For production environment
    └── models/
```

## Configuration Format

### Basic Structure

```yaml
# Required fields
id: unique-model-id
name: "Human-readable Model Name"
endpoint_url: "https://api.example.com/predict"
active: true
config:
  timeout: 30  # seconds
  max_retries: 3

# Optional fields
version: "1.0.0"
description: "Detailed description of the model"
metadata:
  owner: "team@example.com"
  environment: "production"
  created: "2025-01-01"
```

### HTTP/2 Configuration

By default, the orchestrator uses HTTP/1.1 for all model requests. To use HTTP/2 (only if your model server supports it), you need to explicitly enable it and ensure you have the required dependencies installed.

```yaml
# Enable HTTP/2 (only if your server supports it)
http2: false  # Default is false, set to true only if needed

# Required when using HTTP/2
# Make sure to install the required dependency:
# pip install 'httpx[http2]'
```

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | Unique identifier for the model | `sentiment-analyzer-v1` |
| `name` | string | Human-readable name | "Sentiment Analysis" |
| `endpoint_url` | URL | Base URL for model inference | `https://api.example.com/v1/predict` |
| `active` | boolean | Whether the model is active | `true` |
| `config.timeout` | integer | Request timeout in seconds | `30` |
| `config.max_retries` | integer | Maximum number of retry attempts | `3` |

### Configuration Options

#### REST Endpoint Configuration

```yaml
config:
  # Required
  timeout: 30  # seconds
  max_retries: 3

  # Optional
  health_check:
    endpoint: "/health"  # defaults to "/health"
    interval: 30  # seconds
    timeout: 5  # seconds
    failure_threshold: 3

  # Custom headers
  headers:
    Content-Type: "application/json"
    X-Custom-Header: "value"

  # Connection pooling
  max_connections: 100
  max_keepalive_connections: 50
  keepalive_timeout: 60  # seconds

### Authentication

#### API Key

```yaml
auth:
  type: "api_key"
  config:
    header_name: "X-API-Key"
    api_key: "${API_KEY}"  # Use environment variables for secrets
```

#### OAuth2

```yaml
auth:
  type: "oauth2"
  config:
    token_url: "https://auth.example.com/oauth/token"
    client_id: "${CLIENT_ID}"
    client_secret: "${CLIENT_SECRET}"
    scopes: ["predict"]
```

## Example Configurations

### Basic Model

```yaml
id: sentiment-analyzer
name: "Sentiment Analysis"
description: "Analyzes text sentiment (positive/negative/neutral)"
version: "1.2.0"
endpoint_url: "https://api.example.com/v1/predict"
active: true
config:
  timeout: 30
  max_retries: 3
  health_check:
    endpoint: "/health"
    interval: 30
    timeout: 5
    failure_threshold: 3

auth:
  type: "api_key"
  config:
    header_name: "X-API-Key"
    api_key: "${SENTIMENT_API_KEY}"

metadata:
  owner: "ml-team@example.com"
  environment: "production"
  created: "2025-01-01"
  updated: "2025-05-17"
```

### Advanced Configuration

```yaml
id: image-classifier
name: "Image Classification"
description: "Classifies images into 1000 categories"
version: "2.1.0"
endpoint_url: "https://image-service.example.com/v2/predict"
active: true
config:
  timeout: 60
  max_retries: 2
  health_check:
    endpoint: "/health"
    interval: 30
    timeout: 5
  # Additional REST-specific configurations can be added here

auth:
  type: "oauth2"
  config:
    token_url: "https://auth.example.com/oauth/token"
    client_id: "${CLIENT_ID}"
    client_secret: "${CLIENT_SECRET}"
    scopes: ["predict"]

metadata:
  owner: "cv-team@example.com"
  environment: "staging"
  created: "2025-03-15"
  updated: "2025-05-10"
  performance:
    p99_latency_ms: 120
    accuracy: 0.92
  resources:
    gpu: true
    min_memory_gb: 8
```

## Loading Mechanism

1. **Startup**:
   - Orchestrator scans the environment-specific models directory on startup
   - Loads all `.yaml` and `.yml` files
   - Uses the `APP_ENV` environment variable to determine which directory to use (defaults to 'local')

## Docker Networking Configuration

When using the ML Service Orchestrator with Docker containers, you need to be aware of networking differences between deployment modes.

### Host-to-Container Communication

When running the orchestrator on the host machine and models in Docker containers:

```yaml
# Example: config/local/models/mock-model-1.yaml
id: mock-model-1
name: "Mock Model 1"
endpoint_url: "http://localhost:8001"  # Host port mapped to container port 8000
active: true
```

In this scenario:
- The Docker container exposes port 8000 internally
- This port is mapped to host port 8001 (as defined in docker-compose.yml)
- The orchestrator running on the host must connect to `localhost:8001`

### Container-to-Container Communication

When running both the orchestrator and models in Docker containers on the same network:

```yaml
# Example: config/local/models/mock-model-1.yaml
id: mock-model-1
name: "Mock Model 1"
endpoint_url: "http://mock-model-1:8000"  # Container name and internal port
active: true
```

In this scenario:
- Containers can communicate using container names as hostnames
- Use the internal container port (usually 8000)
- Docker's internal DNS resolves container names to their IP addresses

### Automated Configuration with Makefile

The project includes Makefile targets to automatically switch between these configurations:

```bash
# Configure models for host-to-container communication
make configure-models-host

# Configure models for container-to-container communication
make configure-models-docker
```

These commands update the endpoint URLs in all model configuration files to use the appropriate format based on your deployment mode.
   - Validates each configuration
   - Registers valid models
   - Validates connectivity to each endpoint

2. **Hot Reloading (optional)**:
   - Monitor directory for changes
   - Automatically reload configurations when files change
   - Maintain existing connections
   - Log changes for audit

3. **Validation**:
   - Check required fields
   - Validate endpoint URLs are properly formatted
   - Verify authentication credentials if provided
   - Check for duplicate model IDs
   - Test connectivity to the endpoint

## Best Practices

1. **File Naming**:
   - Use kebab-case for filenames
   - Include model name and version
   - Example: `sentiment-analyzer-v1.2.0.yaml`

2. **Versioning**:
   - Use semantic versioning (MAJOR.MINOR.PATCH)
   - Update version for breaking changes
   - Document changes in commit messages

3. **Security**:
   - Never commit secrets to version control
   - Use environment variables for sensitive data
   - Set appropriate file permissions (600 for sensitive files)

4. **Documentation**:
   - Include a `description` field
   - Document input/output formats
   - Add usage examples

5. **Organization**:
   - One model per file
   - Group related models in subdirectories
   - Use consistent indentation (2 spaces)

6. **Docker Networking**:
   - Be aware of networking differences between host and container environments.
   - Use Makefile targets for consistent configuration.

## Troubleshooting

### Common Issues

1. **Configuration Not Loading**
   - Check file permissions
   - Verify YAML syntax (no tabs, correct indentation)
   - Check for duplicate model IDs

2. **Connection Failures**
   - Verify endpoint URL is correct
   - Check network connectivity
   - Verify authentication credentials

3. **Validation Errors**
   - Check required fields
   - Verify data types
   - Check for YAML syntax errors

### Logging

Check orchestrator logs for detailed error messages:

```bash
docker-compose logs orchestrator
```

### Validation Script

Use the included validation script to check configurations:

```bash
python scripts/validate_model.py
```

## Example: Complete Workflow

1. Create a new model configuration:
   ```bash
   mkdir -p config/models
   touch config/models/sentiment-analyzer-v1.0.0.yaml
   ```

2. Edit the configuration:
   ```yaml
   id: sentiment-analyzer
   name: "Sentiment Analysis"
   version: "1.0.0"
   endpoint_url: "${SENTIMENT_API_ENDPOINT}"
   active: true
   platform:
     name: "rest"
     config:
       timeout: 30
       max_retries: 3
   ```

3. Validate the configuration:
   ```bash
   python scripts/validate_model.py
   ```

4. Restart the orchestrator to load the new configuration:
   ```bash
   docker-compose restart orchestrator
   ```

5. Verify the model is registered:
   ```bash
   curl -H "X-API-Key: $ADMIN_API_KEY" http://localhost:8000/admin/models
   ```
