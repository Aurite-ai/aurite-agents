#!/bin/bash

# Script to build the production-like Docker image for Aurite Agents.

# Set script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

IMAGE_NAME="aurite-agents-prodlike"
IMAGE_TAG="latest"
DOCKERFILE_PATH="$PROJECT_ROOT/Dockerfile" # Use the non-dev Dockerfile

echo "Building $IMAGE_NAME:$IMAGE_TAG from $DOCKERFILE_PATH..."

docker build -t "$IMAGE_NAME:$IMAGE_TAG" -f "$DOCKERFILE_PATH" "$PROJECT_ROOT"

if [ $? -eq 0 ]; then
  echo "Successfully built $IMAGE_NAME:$IMAGE_TAG"
else
  echo "Failed to build $IMAGE_NAME:$IMAGE_TAG"
  exit 1
fi
