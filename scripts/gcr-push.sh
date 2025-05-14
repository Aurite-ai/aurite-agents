#!/bin/bash

# Script to tag and push the aurite-agents-prodlike image to GCR.

# Set script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

LOCAL_IMAGE_NAME="aurite-agents-prodlike"
LOCAL_IMAGE_TAG="latest" # Assumes gcr-build.sh was run and created this tag

GCR_PROJECT_ID="aurite-dev"
GCR_IMAGE_NAME="aurite-agents"
GCR_IMAGE_TAG="${1:-prodlike-v0.1}" # Use first argument as tag, or default to prodlike-v0.1

GCR_FULL_IMAGE_NAME="gcr.io/$GCR_PROJECT_ID/$GCR_IMAGE_NAME:$GCR_IMAGE_TAG"

echo "Tagging $LOCAL_IMAGE_NAME:$LOCAL_IMAGE_TAG as $GCR_FULL_IMAGE_NAME..."
docker tag "$LOCAL_IMAGE_NAME:$LOCAL_IMAGE_TAG" "$GCR_FULL_IMAGE_NAME"

if [ $? -ne 0 ]; then
  echo "Failed to tag image."
  exit 1
fi

echo "Pushing $GCR_FULL_IMAGE_NAME to GCR..."
docker push "$GCR_FULL_IMAGE_NAME"

if [ $? -eq 0 ]; then
  echo "Successfully pushed $GCR_FULL_IMAGE_NAME"
  echo "Ensure your Kubernetes deployment manifest (e.g., k8s/aurite-agents/aurite-agents-deployment.yaml) uses this image path: $GCR_FULL_IMAGE_NAME"
else
  echo "Failed to push $GCR_FULL_IMAGE_NAME"
  exit 1
fi
