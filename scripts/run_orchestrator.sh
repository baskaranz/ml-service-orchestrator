#!/bin/bash

# Script to run the ML Service Orchestrator Docker image
# This script helps users quickly set up and run the orchestrator

set -e

# Configuration
IMAGE_NAME="ml-service-orchestrator"
IMAGE_VERSION="1.0.0"
CONTAINER_NAME="ml-orchestrator"
PORT="8000"
CONFIG_ENV="production"
DIST_DIR="lib/dist"

# Print banner
echo "=================================================="
echo "       ML Service Orchestrator Deployment        "
echo "=================================================="
echo "This script deploys the ML Service Orchestrator for"
echo "production or development use."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if image exists
if ! docker image inspect ${IMAGE_NAME}:${IMAGE_VERSION} &> /dev/null; then
    echo "Image ${IMAGE_NAME}:${IMAGE_VERSION} not found locally."
    
    # Check if tar file exists in lib/dist directory
    if [ -f "${DIST_DIR}/${IMAGE_NAME}-${IMAGE_VERSION}.tar.gz" ]; then
        echo "Found compressed image file in ${DIST_DIR}. Loading..."
        gunzip -c ${DIST_DIR}/${IMAGE_NAME}-${IMAGE_VERSION}.tar.gz | docker load
    elif [ -f "${DIST_DIR}/${IMAGE_NAME}-${IMAGE_VERSION}.tar" ]; then
        echo "Found image file in ${DIST_DIR}. Loading..."
        docker load -i ${DIST_DIR}/${IMAGE_NAME}-${IMAGE_VERSION}.tar
    # Check in root directory as fallback
    elif [ -f "${IMAGE_NAME}-${IMAGE_VERSION}.tar.gz" ]; then
        echo "Found compressed image file in project root. Loading..."
        gunzip -c ${IMAGE_NAME}-${IMAGE_VERSION}.tar.gz | docker load
    elif [ -f "${IMAGE_NAME}-${IMAGE_VERSION}.tar" ]; then
        echo "Found image file in project root. Loading..."
        docker load -i ${IMAGE_NAME}-${IMAGE_VERSION}.tar
    else
        echo "Error: Docker image not found and no image file available."
        echo "Please build the image first using scripts/build_image.sh"
        exit 1
    fi
fi

# Create network if it doesn't exist
if ! docker network inspect ml-network &> /dev/null; then
    echo "Creating Docker network 'ml-network'..."
    docker network create --driver bridge ml-network
fi

# Check if container is already running
if docker ps | grep -q ${CONTAINER_NAME}; then
    echo "Container ${CONTAINER_NAME} is already running."
    echo "To stop it: docker stop ${CONTAINER_NAME}"
    echo "To remove it: docker rm ${CONTAINER_NAME}"
    exit 0
fi

# Check if container exists but is stopped
if docker ps -a | grep -q ${CONTAINER_NAME}; then
    echo "Container ${CONTAINER_NAME} exists but is not running."
    echo "Removing existing container..."
    docker rm ${CONTAINER_NAME}
fi

# Select deployment environment
echo ""
echo "Available environments:"
echo "1) production (recommended for deployment)"
echo "2) local (for development and testing)"
read -p "Select environment [1]: " ENV_CHOICE

case "${ENV_CHOICE}" in
    "2")
        CONFIG_ENV="local"
        echo "Using local environment for development"
        ;;
    *)
        CONFIG_ENV="production"
        echo "Using production environment"
        ;;
esac

# Ensure config directory exists
if [ ! -d "./config/${CONFIG_ENV}/models" ]; then
    echo "Creating config directory structure..."
    mkdir -p "./config/${CONFIG_ENV}/models"
fi

# Optional: Run mock models for testing
read -p "\nDo you want to run mock models for testing? (n/y) [n]: " RUN_MOCKS
RUN_MOCKS=${RUN_MOCKS:-n}

if [[ "$RUN_MOCKS" =~ ^[Yy]$ ]]; then
    # Run mock models
    echo "\nStarting mock models for testing purposes..."
    
    # Check if mock models are already running
    if docker ps | grep -q "mock-model-1"; then
        echo "Mock models are already running."
    else
        # Run mock-model-1
        docker run -d --name mock-model-1 \
            --network ml-network \
            -p 8001:8000 \
            -e MODEL_NAME=mock-model-1 \
            -e MODEL_VERSION=1.0.0 \
            -e PORT=8000 \
            ${IMAGE_NAME}:${IMAGE_VERSION} \
            sh -c "python -m app.mocks.model_mock"
            
        # Run mock-model-2
        docker run -d --name mock-model-2 \
            --network ml-network \
            -p 8002:8000 \
            -e MODEL_NAME=mock-model-2 \
            -e MODEL_VERSION=1.0.0 \
            -e PORT=8000 \
            ${IMAGE_NAME}:${IMAGE_VERSION} \
            sh -c "python -m app.mocks.model_mock"
            
        echo "Mock models started on ports 8001 and 8002."
        
        # Configure for container-to-container communication
        if [ -f "./scripts/configure_models_docker.sh" ]; then
            echo "Configuring models for container-to-container communication..."
            ./scripts/configure_models_docker.sh
        fi
    fi
fi

# Run the ML Service Orchestrator
echo "\nDeploying ML Service Orchestrator..."

# Set appropriate worker count based on environment
if [ "${CONFIG_ENV}" = "production" ]; then
    # Use more workers for production
    WORKERS=4
    RESTART_POLICY="--restart=always"
    echo "Using production configuration with ${WORKERS} workers and automatic restart"
else
    # Use fewer workers for development
    WORKERS=1
    RESTART_POLICY="--restart=unless-stopped"
    echo "Using development configuration with ${WORKERS} workers"
fi

# Deploy the orchestrator container
docker run -d \
    --name ${CONTAINER_NAME} \
    ${RESTART_POLICY} \
    --network ml-network \
    -p ${PORT}:8000 \
    -v $(pwd)/config/${CONFIG_ENV}:/app/config/${CONFIG_ENV} \
    -v $(pwd)/logs:/app/logs \
    -e APP_ENV=${CONFIG_ENV} \
    -e CONFIG_DIR=/app/config/${CONFIG_ENV} \
    -e MODELS_DIR=/app/config/${CONFIG_ENV}/models \
    -e WORKERS=${WORKERS} \
    ${IMAGE_NAME}:${IMAGE_VERSION}

echo "\nML Service Orchestrator is running!"
echo "API documentation: http://localhost:${PORT}/docs"
echo "Health check: http://localhost:${PORT}/health"

echo "\nTo check logs: docker logs ${CONTAINER_NAME}"
echo "To stop: docker stop ${CONTAINER_NAME}"

# Wait for service to be ready
echo "\nWaiting for service to be ready..."
sleep 5

# Check if service is healthy
for i in {1..12}; do
    if curl -s http://localhost:${PORT}/health | grep -q "status"; then
        echo "\nService is ready! You can now use the ML Service Orchestrator."
        echo "Try it out: curl -X GET http://localhost:${PORT}/api/v1/models"
        exit 0
    fi
    echo -n "."
    sleep 5
done

echo "\nWarning: Service might not be fully ready yet. Please check logs:"
echo "docker logs ${CONTAINER_NAME}"
