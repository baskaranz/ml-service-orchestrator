# Lasso - ML Model Orchestration Platform

## Overview

Lasso is a platform for orchestrating and managing machine learning models. It provides a unified interface for model deployment, monitoring, and inference.

## Project Structure

```
.
├── app/                    # Main application code
│   ├── api/               # API routes and endpoints
│   ├── core/              # Core business logic
│   ├── services/          # Service layer implementations
│   └── utils/             # Utility functions and helpers
├── config/                # Configuration files
│   ├── models/           # Model configuration files (auto-generated)
│   └── env/              # Environment configuration files
├── docs/                  # Documentation
│   ├── api/              # API documentation
│   └── README.md         # This file
├── mocks/                 # Mock model services
│   ├── model_mock.py     # Mock model implementation
│   └── Dockerfile        # Dockerfile for mock models
├── scripts/              # Utility scripts
├── tests/                # Test files
├── logs/                 # Application logs (git-ignored)
└── .venv/                # Virtual environment (git-ignored)
```

## Version Control

### Git Configuration

The project uses `.gitignore` to exclude unnecessary files from version control:

1. **Python-specific**:
   - Byte-compiled files (`__pycache__/`, `*.pyc`)
   - Test coverage files (`.coverage`, `htmlcov/`)
   - Distribution files (`build/`, `dist/`)
   - Virtual environments (`.venv/`, `env/`)

2. **IDE and Editor**:
   - VS Code settings (except shared settings)
   - Cursor IDE files
   - Vim swap files
   - macOS system files

3. **Project-specific**:
   - Generated model configs (`config/models/*.yaml`)
   - Environment files (`config/env/*.env`)
   - Log files (`logs/`)
   - Docker override files

4. **Development**:
   - Local settings
   - Database files
   - Temporary files
   - Build artifacts

### Directory Structure Maintenance

Empty directories are maintained using `.gitkeep` files:
- `config/models/.gitkeep`
- `config/env/.gitkeep`

## Architecture

The platform consists of two main components:

1. **Orchestrator**: The central service that manages model routing and request handling
2. **Model Services**: Individual model services that handle specific model inference

### Mock Model Service

The platform includes a mock model service for testing and development purposes. The mock model:

- Simulates model predictions with random values
- Supports standard model input/output formats
- Includes health check endpoints
- Generates its own configuration for orchestrator registration

#### Mock Model Features

- **Prediction Endpoint**: `/predict`

  - Accepts POST requests with input data
  - Returns predictions and confidence scores
  - Supports multiple input items
  - Includes model metadata in responses

- **Health Check**: `/health`

  - Returns service status
  - Used for container health monitoring

- **Configuration**: Auto-generates model configuration in YAML format
  - Includes model ID, name, version, and endpoint URL
  - Stored in `config/models/` directory
  - Files are git-ignored but directory structure is maintained

## Setup and Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- Required Python packages (see requirements.txt)

### Running the Services

1. Start the services using Docker Compose:

   ```bash
   docker compose up -d
   ```

2. The services will be available at:
   - Orchestrator: http://localhost:8000
   - Mock Model: http://localhost:8001

## Testing the Services

### Basic Prediction

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"inputs": {"data": ["test input"]}}' \
  http://localhost:8000/orchestrator/models/mock-model-1
```

Expected response:

```json
{
  "outputs": {
    "predictions": [0.123456789],
    "confidence": 0.95
  },
  "metadata": {
    "name": "mock-model-1",
    "version": "1.0.0"
  }
}
```

### Multiple Inputs

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"inputs": {"data": ["input 1", "input 2"]}}' \
  http://localhost:8000/orchestrator/models/mock-model-1
```

### With Parameters

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"inputs": {"data": ["test input"]}, "parameters": {"temperature": 0.7}}' \
  http://localhost:8000/orchestrator/models/mock-model-1
```

### Error Cases

1. Invalid JSON:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"inputs": {"data": ["test input"]' \
  http://localhost:8000/orchestrator/models/mock-model-1
```

2. Non-existent Model:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"inputs": {"data": ["test input"]}}' \
  http://localhost:8000/orchestrator/models/non-existent-model
```

## Health Checks

### Orchestrator Health

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "OK",
  "version": "1.0.0",
  "models": [
    {
      "id": "mock-model-1",
      "name": "mock-model-1",
      "active": true
    }
  ],
  "components": {}
}
```

### Mock Model Health

```bash
curl http://localhost:8001/health
```

Expected response:

```json
{
  "status": "healthy"
}
```

## Configuration

### Mock Model Configuration

The mock model automatically generates its configuration file in `config/models/mock-model-1.yaml`:

```yaml
id: mock-model-1
name: mock-model-1
description: Mock model for testing
version: 1.0.0
endpoint_url: http://mock-model-1:8000
```

Note: These configuration files are git-ignored but the directory structure is maintained using `.gitkeep`.

## Development

### Adding New Mock Models

1. Create a new service in `mocks/docker-compose.yml`:
   ```yaml
   mock-model-2:
     <<: *mock-model-template
     ports:
       - "${MOCK_MODEL_2_PORT:-8002}:8000"
     environment:
       - PORT=8000
       - MODEL_NAME=mock-model-2
       - MODEL_VERSION=1.0.0
       - LOG_LEVEL=DEBUG
   ```

2. Start the new service:
   ```bash
   # Start the orchestrator first
   docker compose up -d

   # Then start the mock model
   docker compose -f mocks/docker-compose.yml up -d mock-model-2
   ```

### Model Configuration

Model configurations are stored in the `config/models` directory. Each model should have its own YAML configuration file with the following structure:

```yaml
id: model-name
name: Model Name
description: Model description
version: 1.0.0
endpoint_url: http://model-name:8000
active: true
```

The orchestrator will automatically discover and use any models configured in this directory. The configuration files are git-ignored but the directory structure is maintained using `.gitkeep`.

### Logging

- Orchestrator logs: `docker compose logs orchestrator`
- Mock model logs: `docker compose logs mock-model-1`
- Log files are stored in the `logs/` directory (git-ignored)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
