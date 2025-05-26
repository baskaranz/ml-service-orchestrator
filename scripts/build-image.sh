#!/bin/bash
set -e

# Default values
ENVIRONMENT="local"
TAG="latest"
SAVE_TO_DIST=true
DIST_DIR="${DIST_DIR:-./dist}"
IMAGE_NAME="ml-orchestrator"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift # past argument
      shift # past value
      ;;
    -t|--tag)
      TAG="$2"
      shift # past argument
      shift # past value
      ;;
    --no-save)
      SAVE_TO_DIST=false
      shift # past argument
      ;;
    --dist-dir)
      DIST_DIR="$2"
      shift # past argument
      shift # past value
      ;;
    --image-name)
      IMAGE_NAME="$2"
      shift # past argument
      shift # past value
      ;;
    *)
      echo "Unknown parameter: $1"
      exit 1
      ;;
  esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(local|dev|stg|prod)$ ]]; then
  echo "Error: Invalid environment. Must be one of: local, dev, stg, prod"
  exit 1
fi

# Build the image
echo "Building $IMAGE_NAME:$ENVIRONMENT-$TAG for $ENVIRONMENT environment..."
docker build \
  --build-arg ENVIRONMENT=$ENVIRONMENT \
  -t $IMAGE_NAME:$ENVIRONMENT-$TAG \
  -t $IMAGE_NAME:$ENVIRONMENT-latest \
  .

# Save to dist directory if enabled
if [ "$SAVE_TO_DIST" = true ]; then
  mkdir -p "$DIST_DIR"
  IMAGE_FILE="$DIST_DIR/$IMAGE_NAME-$ENVIRONMENT-$(date +%Y%m%d-%H%M%S).tar"

  echo "Saving image to $IMAGE_FILE..."
  docker save $IMAGE_NAME:$ENVIRONMENT-$TAG -o "$IMAGE_FILE"

  # Create a symlink to the latest build
  LATEST_SYMLINK="$DIST_DIR/$IMAGE_NAME-$ENVIRONMENT-latest.tar"
  ln -sf "$(basename "$IMAGE_FILE")" "$LATEST_SYMLINK"

  echo "Image saved to $IMAGE_FILE"
  echo "Latest build symlink: $LATEST_SYMLINK"

  # Show disk usage
  echo -e "\nDisk usage:"
  du -h "$IMAGE_FILE"
  echo -e "\nTotal size of $DIST_DIR:"
  du -sh "$DIST_DIR"
else
  echo "Skipping save to dist directory (--no-save flag was used)"
fi

echo "\nBuild complete!"
echo "To run the container:"
echo "  docker run -p 8000:8000 $IMAGE_NAME:$ENVIRONMENT-$TAG"

if [ "$SAVE_TO_DIST" = true ]; then
  echo "\nTo load the saved image on another machine:"
  echo "  docker load -i $LATEST_SYMLINK"
fi
