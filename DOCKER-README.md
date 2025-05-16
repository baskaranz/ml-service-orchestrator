# ML Service Orchestrator with Docker

This guide explains how to run the ML Service Orchestrator with mock model APIs using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Ports 8000-8002 available on your machine

## Quick Start

1. **Start the services**
   ```bash
   docker-compose up -d
   ```

2. **Register the mock models**
   ```bash
   docker-compose exec orchestrator python /app/scripts/register_models.py
   ```

3. **Test the services**
   - Orchestrator API: http://localhost:8000/docs
   - Mock Model 1: http://localhost:8001/
   - Mock Model 2: http://localhost:8002/

## Available Endpoints

### Orchestrator
- `GET /health` - Health check
- `GET /api/v1/models` - List all registered models
- `POST /api/v1/models` - Register a new model
- `GET /api/v1/models/{model_id}` - Get model details
- `POST /api/v1/models/{model_id}/predict` - Make a prediction with a model

### Mock Models
- `GET /` - Health check
- `POST /predict` - Mock prediction endpoint
- `GET /metrics` - Prometheus metrics

## Stopping the Services

```bash
docker-compose down
```

## Troubleshooting

- Check logs: `docker-compose logs -f`
- Check container status: `docker-compose ps`
- Access container shell: `docker-compose exec orchestrator bash`

## Adding More Models

1. Add a new service to `docker-compose.override.yml`
2. Update the `scripts/register_models.py` file with the new model configuration
3. Restart the services: `docker-compose up -d`
