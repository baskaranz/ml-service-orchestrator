# ML Orchestrator Service

A YAML config-driven FastAPI orchestrator service for ML model endpoints.

![Test Coverage](https://img.shields.io/badge/coverage-79%25-yellow)
![Python Version](https://img.shields.io/badge/python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.0-green)

## Project Overview

This service acts as a centralized API gateway for multiple machine learning model endpoints. It dynamically routes requests to the appropriate model APIs based on YAML configuration, supporting zero-downtime updates through configuration hot-reloading.

## Key Features

- **Dynamic Routing**: Route requests to different model endpoints based on URL path
- **Zero-Downtime Updates**: Add or modify model endpoints without service restart
- **Configuration-Driven**: YAML-based configuration for model endpoints
- **Request Proxying**: Forward requests to model endpoints with proper error handling
- **Circuit Breaking**: Fault tolerance with circuit breaker pattern
- **Admin API**: Management endpoints for model configurations
- **Health Monitoring**: Comprehensive health checks and metrics

## Quick Start

### Using Docker

```bash
# Build and run with Docker
docker build -t ml-orchestrator .
docker run -p 8000:8000 ml-orchestrator
```

### Using Development Environment

```bash
# Setup development environment
./scripts/setup_dev.sh

# Activate virtual environment
source venv/bin/activate

# Run the service
make run
```

### Using our Development CLI

```bash
# Run the service
./scripts/dev_cli.py run

# Run tests with coverage
./scripts/dev_cli.py coverage

# Generate a new model configuration
./scripts/dev_cli.py gen-model my_new_model --endpoint="http://my-model-api.com"

# Generate a test file skeleton
./scripts/dev_cli.py gen-test core.orchestrator --async-test
```

## Project Structure

```
ml-orchestrator/
├── README.md
├── Makefile                    # Common development commands
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── app/
│   ├── __init__.py
│   ├── main.py                 # Main FastAPI application entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── models_config.py    # Config loader/parser for model endpoints
│   │   └── settings.py         # Global app settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py       # Health check endpoints
│   │   │   ├── orchestrator.py # Main orchestrator routing logic
│   │   │   └── admin.py        # Admin endpoints for managing models
│   │   └── dependencies.py     # FastAPI dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Core orchestration logic
│   │   ├── models.py           # Pydantic models for requests/responses
│   │   └── exceptions.py       # Custom exception handlers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── model_registry.py   # Service for model registry operations
│   │   └── proxy.py            # Service for proxying requests to models
│   └── utils/
│       ├── __init__.py
│       ├── logging.py          # Logging utilities
│       └── http.py             # HTTP client utilities
├── tests/
│   ├── README.md               # Testing guide
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_coverage_summary.md # Coverage summary
│   ├── test_api/
│   │   ├── test_dependencies.py
│   │   ├── test_health.py
│   │   ├── test_health_async.py
│   │   ├── test_orchestrator.py
│   │   └── test_admin.py
│   ├── test_config/
│   │   ├── test_models_config.py
│   │   └── test_models_config_advanced.py
│   ├── test_core/
│   │   ├── test_exceptions.py
│   │   ├── test_models.py
│   │   └── test_orchestrator.py
│   ├── test_services/
│   │   ├── test_model_registry.py
│   │   ├── test_model_registry_advanced.py
│   │   ├── test_proxy.py
│   │   └── test_proxy_advanced.py
│   └── test_utils/
│       ├── test_http.py
│       └── test_logging.py
├── config/                      # Configuration files
│   ├── models/                  # YAML config files for models
│   │   ├── model_1.yaml
│   │   └── model_2.yaml
│   └── models_registry.yaml     # Main registry of all models
├── .github/                     # GitHub workflows and templates
│   ├── workflows/               # CI/CD workflows
│   └── ISSUE_TEMPLATE/          # Issue templates
└── scripts/
    ├── dev_cli.py              # Development CLI tool
    ├── coverage_report.py      # Test coverage reporting tool
    ├── setup_dev.sh            # Development environment setup script
    ├── reload_config.sh        # Script to reload config without restart
    ├── health_check.sh         # Health check script
    ├── create_dummy_models.py  # Tool to create dummy model APIs for testing
    ├── start_dummy_models.sh   # Auto-generated script to start dummy models
    └── DUMMY_MODELS_README.md  # Documentation for dummy model APIs
```

## Architecture Design

### System Components

#### Configuration System
- **ModelConfigManager**: Loads and monitors YAML configuration files
- **Settings**: Application settings from environment variables

#### API Layer
- **OrchestratorRouter**: Dynamically routes requests to model endpoints
- **AdminRouter**: Manages model configurations
- **HealthRouter**: Provides health check endpoints

#### Core Services
- **ModelRegistry**: In-memory registry of model configurations
- **OrchestratorService**: Routes requests to appropriate model endpoints
- **ProxyService**: Forwards requests to model endpoints with error handling

#### Request Flow
```
User Request → FastAPI → OrchestratorRouter → OrchestratorService → ModelRegistry → ProxyService → Model Endpoint
```

### Key Design Patterns

1. **Configuration-as-Code**: YAML files define all model endpoints and their behavior
2. **Dynamic Routing**: URL paths map directly to model endpoints
3. **Hot Reloading**: Configuration changes are detected and applied without restart
4. **Circuit Breaker**: Prevents cascading failures from unavailable model endpoints
5. **Dependency Injection**: FastAPI dependencies for clean service integration

## API Usage

### Model Endpoints
Access model endpoints through the orchestrator:
- `https://base-url/orchestrator/model_1` → routes to Model 1's endpoint
- `https://base-url/orchestrator/model_2` → routes to Model 2's endpoint

### Admin API
Manage model configurations:
- `POST /admin/models` - Add a new model
- `PUT /admin/models/{model_id}` - Update a model
- `DELETE /admin/models/{model_id}` - Remove a model
- `GET /admin/models` - List all models
- `GET /admin/models/{model_id}` - Get a specific model
- `POST /admin/reload` - Reload all configurations

### Health Checks
- `GET /health` - Basic health check
- `GET /health/details` - Detailed health status with component checks

## Configuration Examples

### Main Registry

```yaml
# config/models_registry.yaml
version: "1.0.0"
name: "ML Model Orchestrator Registry"
description: "Registry of all ML model endpoints"

# Global settings
settings:
  default_timeout: 30.0
  default_max_retries: 3
  circuit_breaker:
    failure_threshold: 5
    reset_timeout: 30.0

# List of all models
models:
  - id: "model_1"
    config_file: "models/model_1.yaml"
  - id: "model_2"
    config_file: "models/model_2.yaml"
```

### Model Configuration

```yaml
# config/models/model_1.yaml
id: "model_1"
name: "Sentiment Analysis Model"
description: "Model for sentiment analysis of text"
endpoint_url: "${MODEL_1_URL:https://model1-api.example.com/predict}"
version: "1.0.0"
timeout: 10.0
max_retries: 3

# Circuit breaker settings
circuit_breaker:
  failure_threshold: 5
  reset_timeout: 30.0

# Authentication settings
auth:
  type: "api_key"
  key_name: "X-API-Key"
  key_value: "${MODEL_1_API_KEY}"
  location: "header"
```

## Development

### Setting Up Development Environment

We provide a setup script for quick environment configuration:

```bash
./scripts/setup_dev.sh
```

Or set up manually:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### Development Workflow with Make

We provide a Makefile with common development commands:

```bash
# Run the application
make run

# Run linters
make lint

# Run tests with coverage
make test-cov

# Format code
make format

# Clean up build artifacts
make clean
```

### Development CLI

For more advanced development tasks, use our CLI tool:

```bash
# Run the application with custom settings
./scripts/dev_cli.py run --port 8080 --debug

# Run specific tests
./scripts/dev_cli.py test --module core.models

# Run tests with coverage
./scripts/dev_cli.py coverage --report html

# Generate a new model configuration
./scripts/dev_cli.py gen-model my_model --endpoint="http://example.com/my_model"

# Generate a test file skeleton
./scripts/dev_cli.py gen-test services.proxy --async-test --class-test ProxyService
```

### Adding a New Model

1. Create a new YAML configuration file in `config/models/`
2. Add the model to the registry in `config/models_registry.yaml`
3. The service will automatically detect and load the new configuration

Alternatively, use our CLI tool:

```bash
./scripts/dev_cli.py gen-model new_model \
  --endpoint="https://api.example.com/new_model" \
  --timeout=15.0 \
  --auth-type=bearer_token \
  --auth-key="my_secure_token"
```

### Creating Dummy Model APIs for Testing

We provide a script to create and run dummy model APIs for testing and development:

```bash
# Create default dummy models (apple_model and orange_model)
python scripts/create_dummy_models.py

# Create custom models with specific names
python scripts/create_dummy_models.py --model-name model1 model2 model3

# Start all dummy models as background processes
bash scripts/start_dummy_models.sh
```

For more information, see [DUMMY_MODELS_README.md](scripts/DUMMY_MODELS_README.md).

### Testing

We have comprehensive test coverage (79%) for the codebase. Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# View coverage report
./scripts/coverage_report.py --html
```

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed information about contributing to this project.

## License

MIT

## Contributors

Your Team Name