#!/bin/bash
# =============================================================================
# Aurite Agents Framework - Docker Build and Publish Script
# =============================================================================
# This script builds and publishes the Aurite Agents Docker image to DockerHub.
#
# Prerequisites:
#   - Docker installed and running
#   - Docker Hub account with push permissions to aurite/aurite-agents
#   - Logged in to Docker Hub: docker login
#
# Usage:
#   ./scripts/docker/build_and_publish.sh [version] [--push] [--latest]
#
# Examples:
#   ./scripts/docker/build_and_publish.sh 0.3.28 --push --latest
#   ./scripts/docker/build_and_publish.sh dev --push
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_REGISTRY="docker.io"
DOCKER_NAMESPACE="aurite"
IMAGE_NAME="aurite-agents"
DOCKERFILE="Dockerfile.public"

# Default values
VERSION=""
PUSH_IMAGE=false
TAG_LATEST=false
BUILD_PLATFORMS="linux/amd64,linux/arm64"
BUILD_ONLY=false

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [version] [options]"
    echo ""
    echo "Arguments:"
    echo "  version         Version tag for the image (e.g., 0.3.28, dev, latest)"
    echo ""
    echo "Options:"
    echo "  --build-only    Build and test locally without pushing (recommended for testing)"
    echo "  --push          Push the image to DockerHub after building"
    echo "  --latest        Also tag and push as 'latest'"
    echo "  --local-only    Build for local platform only (faster)"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --build-only               # Build and test current version locally"
    echo "  $0 0.3.28 --build-only       # Build and test specific version locally"
    echo "  $0 0.3.28 --push --latest    # Build, tag as 0.3.28 and latest, push both"
    echo "  $0 dev --push                # Build and push dev tag"
    echo "  $0 0.3.28 --local-only       # Build locally without pushing (no testing)"
}

# Function to validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."

    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    # Check if Dockerfile exists
    if [[ ! -f "$DOCKERFILE" ]]; then
        log_error "Dockerfile not found: $DOCKERFILE"
        exit 1
    fi

    # Check if we're in the right directory (should have pyproject.toml)
    if [[ ! -f "pyproject.toml" ]]; then
        log_error "pyproject.toml not found. Please run this script from the project root."
        exit 1
    fi

    # If pushing, check Docker Hub login
    if [[ "$PUSH_IMAGE" == true ]]; then
        log_info "Checking Docker Hub authentication..."
        if ! docker info | grep -q "Username:"; then
            log_warn "Not logged in to Docker Hub. Attempting login..."
            if ! docker login; then
                log_error "Failed to login to Docker Hub"
                exit 1
            fi
        fi
    fi

    log_info "Prerequisites validated successfully"
}

# Function to extract version from pyproject.toml
get_project_version() {
    if command -v python3 &> /dev/null; then
        python3 -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
print(data['project']['version'])
" 2>/dev/null || echo ""
    else
        # Fallback to grep if python3 not available
        grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' || echo ""
    fi
}

# Function to build the Docker image
build_image() {
    local version="$1"
    local full_image_name="${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/${IMAGE_NAME}"

    log_info "Building Docker image..."
    log_info "Image: ${full_image_name}:${version}"
    log_info "Dockerfile: ${DOCKERFILE}"
    log_info "Platforms: ${BUILD_PLATFORMS}"

    # Prepare build arguments
    local build_args=(
        "--file" "$DOCKERFILE"
        "--tag" "${full_image_name}:${version}"
        "--label" "org.opencontainers.image.version=${version}"
        "--label" "org.opencontainers.image.created=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        "--label" "org.opencontainers.image.revision=$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
    )

    # Add latest tag if requested
    if [[ "$TAG_LATEST" == true ]]; then
        build_args+=("--tag" "${full_image_name}:latest")
    fi

    # Use buildx for multi-platform builds if pushing
    if [[ "$PUSH_IMAGE" == true ]]; then
        log_info "Building multi-platform image with buildx..."
        docker buildx build \
            --platform "$BUILD_PLATFORMS" \
            --push \
            "${build_args[@]}" \
            .
    else
        log_info "Building local image..."
        docker build "${build_args[@]}" .
    fi

    log_info "Build completed successfully"
}

# Function to test the built image
test_image() {
    local version="$1"
    local full_image_name="${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/${IMAGE_NAME}:${version}"

    log_info "Testing built image..."

    # Test that the image can start and respond to health check
    local container_name="aurite-test-$$"

    log_debug "Starting test container: $container_name"
    docker run -d \
        --name "$container_name" \
        -e API_KEY=test-key \
        -e AURITE_AUTO_INIT=true \
        "$full_image_name" &> /dev/null

    # Wait for container to be healthy
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "unknown")

        if [[ "$health_status" == "healthy" ]]; then
            log_info "Container health check passed"
            break
        elif [[ "$health_status" == "unhealthy" ]]; then
            log_error "Container health check failed"
            docker logs "$container_name"
            docker rm -f "$container_name" &> /dev/null
            exit 1
        fi

        log_debug "Health status: $health_status (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    if [[ $attempt -gt $max_attempts ]]; then
        log_error "Container failed to become healthy within timeout"
        docker logs "$container_name"
        docker rm -f "$container_name" &> /dev/null
        exit 1
    fi

    # Clean up test container
    docker rm -f "$container_name" &> /dev/null
    log_info "Image test completed successfully"
}

# Function to display build summary
show_summary() {
    local version="$1"
    local full_image_name="${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/${IMAGE_NAME}"

    log_info "=============================================="
    log_info "Build Summary"
    log_info "=============================================="
    log_info "Image: ${full_image_name}:${version}"
    if [[ "$TAG_LATEST" == true ]]; then
        log_info "Also tagged as: ${full_image_name}:latest"
    fi
    log_info "Pushed to registry: $PUSH_IMAGE"
    log_info "Platforms: $BUILD_PLATFORMS"
    log_info "=============================================="

    if [[ "$PUSH_IMAGE" == true ]]; then
        log_info "Image is now available on DockerHub:"
        log_info "  docker pull ${full_image_name}:${version}"
        if [[ "$TAG_LATEST" == true ]]; then
            log_info "  docker pull ${full_image_name}:latest"
        fi
    else
        log_info "To push the image manually:"
        log_info "  docker push ${full_image_name}:${version}"
        if [[ "$TAG_LATEST" == true ]]; then
            log_info "  docker push ${full_image_name}:latest"
        fi
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only)
            BUILD_ONLY=true
            PUSH_IMAGE=false
            BUILD_PLATFORMS="linux/amd64"  # Local build only
            shift
            ;;
        --push)
            PUSH_IMAGE=true
            BUILD_ONLY=false
            shift
            ;;
        --latest)
            TAG_LATEST=true
            shift
            ;;
        --local-only)
            BUILD_PLATFORMS="linux/amd64"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$VERSION" ]]; then
                VERSION="$1"
            else
                log_error "Multiple version arguments provided"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Determine version if not provided
if [[ -z "$VERSION" ]]; then
    PROJECT_VERSION=$(get_project_version)
    if [[ -n "$PROJECT_VERSION" ]]; then
        VERSION="$PROJECT_VERSION"
        log_info "Using version from pyproject.toml: $VERSION"
    else
        log_error "No version specified and could not extract from pyproject.toml"
        show_usage
        exit 1
    fi
fi

# Main execution
main() {
    if [[ "$BUILD_ONLY" == true ]]; then
        log_info "Starting Docker build and test process (build-only mode)..."
    else
        log_info "Starting Docker build and publish process..."
    fi
    log_info "Version: $VERSION"

    validate_prerequisites
    build_image "$VERSION"

    # Always test locally built images (not multi-platform builds that are pushed)
    if [[ "$PUSH_IMAGE" == false ]]; then
        test_image "$VERSION"
    fi

    show_summary "$VERSION"

    if [[ "$BUILD_ONLY" == true ]]; then
        log_info "✅ Build and test completed successfully!"
        log_info "The image is ready for local testing. To publish to DockerHub:"
        log_info "  ./scripts/docker/build_and_publish.sh $VERSION --push"
    else
        log_info "Process completed successfully!"
    fi
}

# Run main function
main
