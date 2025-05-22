# Docker Distribution Guide

This guide explains how to distribute and run the ML Service Orchestrator using Docker.

## Building and Distributing Docker Images

The ML Service Orchestrator provides several methods for building and distributing Docker images.

### Building the Docker Image

```bash
# Build the Docker image and start containers
make docker
```

This command will:
1. Build the Docker image (`ml-orchestrator:latest`)
2. Create the required Docker network if it doesn't exist
3. Start the containers using Docker Compose

### Pushing to a Docker Registry

#### Remote Registry (e.g., Docker Hub)

```bash
# First, authenticate with Docker Hub
docker login

# Push to a remote registry
make docker-push DOCKER_REGISTRY=your-username/
```

Example:
```bash
make docker-push DOCKER_REGISTRY=baskaran/
```

This will push the image to Docker Hub as `baskaran/ml-orchestrator:latest`.

#### Local Registry

```bash
# Start a local registry if you don't have one
docker run -d -p 5001:5000 --name local-registry registry:2

# Push to the local registry
make docker-push-local
```

This will push the image to your local registry as `localhost:5001/ml-orchestrator:latest`.

### Saving as a Tar File

```bash
# Save the Docker image as a tar file
make docker-save
```

This will save the Docker image to `dist/ml-orchestrator-latest.tar`.

## Running from a Tar File

If you've received the Docker image as a tar file, follow these steps to run it:

### Step 1: Load the Docker Image

```bash
# Load the Docker image from the tar file
docker load -i dist/ml-orchestrator-latest.tar
```

This will make the image available in your local Docker environment as `ml-orchestrator:latest`.

### Step 2: Run the Orchestrator

You have several options for running the container:

#### Option 1: Run Just the Orchestrator (Simplest)

```bash
# Run the orchestrator container with the required environment variable
docker run -p 8000:8000 -e APP_ENV=local ml-orchestrator:latest
```

This maps port 8000 from the container to port 8000 on your host, allowing you to access the orchestrator API at http://localhost:8000.

**Important**: You must set the `APP_ENV` environment variable to one of: `dev`, `stg`, `prod`, `test`, or `local`. Without this, the application will fail to start with an environment error.

#### Option 2: Run with Docker Compose (Recommended)

This approach runs the orchestrator along with the mock models, which is the complete setup:

```bash
# Ensure the network exists
docker network create ml-network

# Run the orchestrator and mock models
docker-compose up
```

Or you can use our enhanced Makefile target:

```bash
# Run the complete setup with one command
make docker-compose-safe
```

#### Option 3: Run with Custom Configuration

```bash
# Run with custom environment variables
docker run -p 8000:8000 \
  -e APP_ENV=local \
  -e LOG_LEVEL=DEBUG \
  -e CONFIG_DIR=/app/config/local \
  -e MODELS_DIR=/app/config/local/models \
  ml-orchestrator:latest
```

### Step 3: Verify the Orchestrator is Running

Check that the orchestrator is running properly:

```bash
# Check the health endpoint
curl http://localhost:8000/health

# List available models
curl http://localhost:8000/api/v1/models
```

### Step 4: Make Requests to the Orchestrator

Once the orchestrator is running, you can send requests to it:

```bash
# Example request to a model
curl -X POST http://localhost:8000/api/v1/models/mock-model-1 \
  -H "Content-Type: application/json" \
  -d '{"input": "test input"}'
```

**Note**: The mock models expect a JSON payload with a key `input`, not `data`.

## Additional Options

### Mounting Custom Configuration

```bash
# Mount custom configuration
docker run -p 8000:8000 \
  -e APP_ENV=local \
  -v /path/to/your/config:/app/config/local \
  ml-orchestrator:latest
```

### Persisting Logs

```bash
# Mount a volume for logs
docker run -p 8000:8000 \
  -e APP_ENV=local \
  -v /path/to/logs:/app/logs \
  ml-orchestrator:latest
```

### Running in Detached Mode

```bash
# Run in the background
docker run -d -p 8000:8000 -e APP_ENV=local ml-orchestrator:latest
```

## Troubleshooting

### Environment Configuration Issues

If you see an error like this:

```
ValueError: Invalid environment: production. Must be one of: dev, stg, prod, test, local
```

Make sure to set the `APP_ENV` environment variable to one of the allowed values:

```bash
docker run -p 8000:8000 -e APP_ENV=local ml-orchestrator:latest
```

### Network Issues

If you encounter network-related issues, ensure the Docker network exists:

```bash
docker network create ml-network
```

### Container Communication

When running the orchestrator on the host and mock models in Docker:

1. The mock model endpoints in the YAML configuration (e.g., `config/local/models/mock-model-1.yaml`) must be set to `http://localhost:8001` (or the appropriate host port)

2. When running everything in Docker, the endpoints should be container names like `http://mock-model-1:8000`

Use the provided Makefile targets to configure these automatically:

```bash
# For host-to-container communication
make configure-models-host

# For container-to-container communication
make configure-models-docker
```
