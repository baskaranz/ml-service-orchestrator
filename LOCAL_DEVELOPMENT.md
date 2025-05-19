# Local Development Setup

This document explains how to set up and use the local development environment for the ML Orchestrator.

## Prerequisites

- Docker and Docker Compose installed
- Make sure ports 8000-8002 are available

## Local Development Environment

The local development environment includes:

1. **Orchestrator Service** - Main API service (port 8000)
2. **Mock Model 1** - Active mock model (port 8001)
3. **Mock Model 2** - Inactive mock model (port 8002)

## Getting Started

### 1. Start Services

```bash
# Start all services
./scripts/local-dev.sh start

# Start with custom port
./scripts/local-dev.sh --port 9000 start
```

### 2. Check Status

```bash
# Check service status
./scripts/local-dev.sh status
```

### 3. View Logs

```bash
# View logs in real-time
./scripts/local-dev.sh logs
```

### 4. Stop Services

```bash
# Stop all services
./scripts/local-dev.sh stop
```

## Available Endpoints

- **Orchestrator**: http://localhost:8000
  - Health check: `GET /health`
  - API docs: `GET /docs`

- **Mock Model 1**: http://localhost:8001
  - Health check: `GET /health`
  - Prediction: `POST /predict`

- **Mock Model 2**: http://localhost:8002
  - Health check: `GET /health`
  - Prediction: `POST /predict`

## Configuration

### Environment Variables

- `ORCHESTRATOR_PORT`: Port for the orchestrator (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

### Model Configuration

Model configurations are loaded from `config/local/models/`. Each YAML file in this directory defines a model that the orchestrator can use.

## Development Workflow

1. Start the local environment: `./scripts/local-dev.sh start`
2. Make code changes
3. Rebuild services: `docker-compose build`
4. Restart services: `./scripts/local-dev.sh restart`
5. Test your changes
6. Stop services when done: `./scripts/local-dev.sh stop`

## Troubleshooting

- If services fail to start, check logs: `./scripts/local-dev.sh logs`
- Make sure Docker has enough resources allocated
- Check for port conflicts (8000-8002)
