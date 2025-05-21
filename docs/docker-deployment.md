# Docker Deployment Guide

This guide explains how to build, distribute, and deploy the ML Service Orchestrator using Docker. It covers both manual Docker operations and Docker Compose for easier orchestration.

## Building the Docker Image

The ML Service Orchestrator provides a convenient script for building the Docker image:

```bash
./scripts/build_image.sh
```

This script will:

1. Build a production-ready Docker image named `ml-service-orchestrator:1.0.0`
2. Optimize the image using multi-stage builds for smaller size
3. Prompt you to export the image as a compressed file for distribution
4. Save the exported image to `lib/dist/ml-service-orchestrator-1.0.0.tar.gz`

### Build Options

When running the build script, you'll be prompted with:

```
Do you want to export the image as a tar file for sharing? (y/n):
```

- Answer **y** to create a distributable archive in the `lib/dist` directory
- Answer **n** if you only need the image locally

## Distributing the Docker Image

After building, the Docker image can be shared in several ways:

### Option 1: Share the Compressed Image File

The compressed image file (`lib/dist/ml-service-orchestrator-1.0.0.tar.gz`) can be shared directly. Recipients can load it with:

```bash
docker load -i ml-service-orchestrator-1.0.0.tar.gz
```

### Option 2: Push to a Docker Registry

For team environments, push the image to a Docker registry:

```bash
# Tag the image for your registry
docker tag ml-service-orchestrator:1.0.0 your-registry.com/ml-service-orchestrator:1.0.0

# Push to registry
docker push your-registry.com/ml-service-orchestrator:1.0.0
```

## Deploying the Orchestrator

To deploy the ML Service Orchestrator, use the provided script:

```bash
./scripts/run_orchestrator.sh
```

This script will:

1. Check if the Docker image exists locally, and load it if not found
2. Create the necessary Docker network
3. Prompt for environment selection (local or production)
4. Optionally start mock models for testing
5. Start the orchestrator container with appropriate configurations
6. Verify the service is healthy

### Deployment Options

The script will prompt you for several options:

1. **Environment Selection**:
   ```
   Available environments:
   1) local (development)
   2) production
   Select environment [1]:
   ```
   This determines which configuration directory is used.

2. **Mock Models**:
   ```
   Do you want to run mock models for testing? (y/n) [y]:
   ```
   If yes, the script will start two mock model containers for testing.

## Manual Deployment

If you prefer to run the containers manually, use these commands:

```bash
# Create network
docker network create --driver bridge ml-network

# Run the orchestrator
docker run -d \
  --name ml-orchestrator \
  --network ml-network \
  -p 8000:8000 \
  -v $(pwd)/config/local:/app/config/local \
  -v $(pwd)/logs:/app/logs \
  -e APP_ENV=local \
  -e CONFIG_DIR=/app/config/local \
  -e MODELS_DIR=/app/config/local/models \
  ml-service-orchestrator:1.0.0
```

## Container-to-Container vs. Host-to-Container Communication

The ML Service Orchestrator supports two deployment scenarios:

### Container-to-Container

When both the orchestrator and models run in Docker containers:

```bash
# Configure models for container-to-container communication
make configure-models-docker
```

This updates model configurations to use `http://{container-name}:{PORT}` endpoints (e.g., `http://mock-model-1:8000`).

### Host-to-Container

When the orchestrator runs on the host and models run in Docker containers:

```bash
# Configure models for host-to-container communication
make configure-models-host
```

This updates model configurations to use `http://localhost:{PORT}` endpoints (e.g., `http://localhost:8001` for mock-model-1).

## Using Docker Compose

For easier deployment, you can use Docker Compose to manage all services together.

### Prerequisites

- Docker and Docker Compose installed on your system
- Ports 8000-8002 available on your machine

### Quick Start

1. **Start the services**
   ```bash
   docker-compose up -d
   ```

2. **Register the mock models** (if not using YAML configuration)
   ```bash
   docker-compose exec orchestrator python /app/scripts/register_models.py
   ```

3. **Test the services**
   - Orchestrator API: http://localhost:8000/docs
   - Mock Model 1: http://localhost:8001/
   - Mock Model 2: http://localhost:8002/

### Stopping the Services

```bash
docker-compose down
```

### Adding More Models

1. Add a new service to `docker-compose.override.yml`
2. Update the `scripts/register_models.py` file with the new model configuration
3. Restart the services: `docker-compose up -d`

## Available Endpoints

### Orchestrator
- `GET /health` - Health check
- `GET /api/v1/models` - List all registered models
- `POST /api/v1/models` - Register a new model
- `GET /api/v1/models/{model_id}` - Get model details
- `POST /api/v1/models/{model_id}` - Make a prediction with a model

### Mock Models
- `GET /` - Health check
- `POST /predict` - Mock prediction endpoint
- `GET /metrics` - Prometheus metrics

## Troubleshooting

### Image Not Found

If you see `Error: Docker image not found and no image file available`, run the build script first:

```bash
./scripts/build_image.sh
```

### Container Already Running

If you see `Container ml-orchestrator is already running`, you can stop and remove it:

```bash
docker stop ml-orchestrator
docker rm ml-orchestrator
```

### Network Issues

If models can't communicate with the orchestrator, ensure they're on the same network:

```bash
# Verify network
docker network inspect ml-network

# Check container network
docker inspect -f '{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}' ml-orchestrator
```

### Docker Compose Troubleshooting

- Check logs: `docker-compose logs -f`
- Check container status: `docker-compose ps`
- Access container shell: `docker-compose exec orchestrator bash`
