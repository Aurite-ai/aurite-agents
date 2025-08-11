#!/bin/bash

# This script builds the backend Docker image, runs it, tests the health endpoint, and cleans up.

# Exit immediately if a command exits with a non-zero status.
set -e

# Define variables for clarity
IMAGE_NAME="aurite-api-test-image"
CONTAINER_NAME="aurite-api-test-container"
HOST_PORT=8000

# --- Build Phase ---
echo "Building Docker image '$IMAGE_NAME' from Dockerfile..."
docker build -t $IMAGE_NAME -f Dockerfile .
echo "Image build complete."
echo "----------------------------------"

# --- Run Phase ---
echo "Running container '$CONTAINER_NAME'..."
# Use --env-file to pass environment variables from .env, which is required for the API_KEY
docker run -d --name $CONTAINER_NAME --env-file .env -p $HOST_PORT:8000 $IMAGE_NAME
echo "Container started."
echo "----------------------------------"

# --- Health Check Phase ---
echo "Waiting for the container to become healthy..."
# Loop for up to 60 seconds, checking the container's health status every 5 seconds.
for i in {1..12}; do
    HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME)
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        echo "Container is healthy!"
        break
    fi
    echo "Current status: $HEALTH_STATUS. Retrying in 5 seconds..."
    sleep 5
done

# Final check to ensure the container is healthy before proceeding
HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME)
if [ "$HEALTH_STATUS" != "healthy" ]; then
    echo "Error: Container failed to become healthy."
    echo "Dumping container logs:"
    docker logs $CONTAINER_NAME
    # Cleanup before exiting
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    exit 1
fi
echo "----------------------------------"

# --- Test Endpoint Phase ---
echo "Testing the /health endpoint..."
# Use curl with -f to fail on server errors (HTTP status code >= 400)
if curl -f http://localhost:$HOST_PORT/health; then
    echo
    echo "✅ Health endpoint test PASSED."
else
    echo
    echo "❌ Health endpoint test FAILED."
    # Cleanup before exiting
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    exit 1
fi
echo "----------------------------------"

# --- Cleanup Phase ---
echo "Shutting down and removing the container..."
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME
echo "Cleanup complete."
echo "----------------------------------"

echo "🎉 Backend Docker test script finished successfully!"
