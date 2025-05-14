#!/bin/bash

# Simple script to build and run the Docker container in ../Dockerfile using ../.env for env vars

# Set script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from .env file
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
else
    echo "Error: .env file not found in $PROJECT_ROOT"
    exit 1
fi

# Build the Docker image
IMAGE_NAME="aurite-agents-dev:latest"
DOCKERFILE_PATH="$PROJECT_ROOT/Dockerfile.dev"
docker build -t "$IMAGE_NAME" -f "$DOCKERFILE_PATH" "$PROJECT_ROOT"

# Run the Docker container
docker run --rm -it \
    -p 8000:8000 \
    --env-file "$PROJECT_ROOT/.env" \
    "$IMAGE_NAME"
