#!/bin/bash

# Script to build and package the ML Service Orchestrator Docker image
# This creates a portable image that can be shared with others

set -e

# Configuration
IMAGE_NAME="ml-service-orchestrator"
IMAGE_VERSION="1.0.0"
DIST_DIR="lib/dist"
TAR_NAME="${DIST_DIR}/${IMAGE_NAME}-${IMAGE_VERSION}.tar"

# Print banner
echo "=================================================="
echo "  Building ML Service Orchestrator Docker Image  "
echo "=================================================="
echo "Image: ${IMAGE_NAME}:${IMAGE_VERSION}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t ${IMAGE_NAME}:${IMAGE_VERSION} -f Dockerfile .

echo "\nImage built successfully!"
docker images | grep ${IMAGE_NAME}

# Ask if user wants to export the image
read -p "\nDo you want to export the image as a tar file for sharing? (y/n): " EXPORT_IMAGE

if [[ "$EXPORT_IMAGE" =~ ^[Yy]$ ]]; then
    # Ensure the distribution directory exists
    mkdir -p ${DIST_DIR}

    echo "\nExporting image to ${TAR_NAME}..."
    docker save -o ${TAR_NAME} ${IMAGE_NAME}:${IMAGE_VERSION}

    # Compress the tar file
    echo "Compressing image..."
    gzip ${TAR_NAME}

    echo "\nImage exported and compressed successfully to ${TAR_NAME}.gz"
    echo "File size: $(du -h ${TAR_NAME}.gz | cut -f1)"
    echo "\nTo share this image with others, provide them with the ${TAR_NAME}.gz file."
    echo "They can load it using: docker load -i ${TAR_NAME}.gz"
fi

echo "\nTo run the orchestrator:"
echo "docker run -d --name ml-orchestrator -p 8000:8000 -v \$(pwd)/config:/app/config ${IMAGE_NAME}:${IMAGE_VERSION}"

echo "\nDone!"
