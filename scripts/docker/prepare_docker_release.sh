#!/bin/bash
# =============================================================================
# Aurite Agents Framework - Docker Release Preparation Script
# =============================================================================
# This script performs all necessary preparation steps before pushing the
# Docker image to DockerHub, including building, security scanning, and testing.
#
# Usage:
#   ./scripts/docker/prepare_docker_release.sh [VERSION]
#
# Example:
#   ./scripts/docker/prepare_docker_release.sh 0.4.0
#   ./scripts/docker/prepare_docker_release.sh  # Uses version from pyproject.toml
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DOCKER_REPO="aurite/aurite-agents"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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

log_step() {
    echo -e "\n${CYAN}===> $1${NC}"
}

# Function to extract version from pyproject.toml
get_version_from_pyproject() {
    # Try using grep and sed to extract version from pyproject.toml
    grep -E '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/' | head -1
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*)    echo "macos" ;;
        Linux*)     echo "linux" ;;
        *)          echo "unknown" ;;
    esac
}

# Function to install Trivy
install_trivy() {
    local os=$(detect_os)

    log_info "Trivy is not installed but is required for security scanning."
    echo ""
    read -p "Would you like to install Trivy now? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Trivy is required for Docker release preparation"
        log_info "Please install Trivy manually:"
        if [ "$os" = "macos" ]; then
            log_info "  brew install trivy"
        else
            log_info "  curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin"
        fi
        log_info "Or visit: https://github.com/aquasecurity/trivy"
        return 1
    fi

    log_step "Installing Trivy"

    if [ "$os" = "macos" ]; then
        if command_exists brew; then
            log_info "Installing Trivy via Homebrew..."
            if brew install trivy; then
                log_info "✓ Trivy installed successfully"
                return 0
            else
                log_error "Failed to install Trivy via Homebrew"
                return 1
            fi
        else
            log_error "Homebrew is not installed. Please install Homebrew first:"
            log_info "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            return 1
        fi
    elif [ "$os" = "linux" ]; then
        log_info "Installing Trivy for Linux..."
        log_info "This requires sudo access."

        if curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin; then
            log_info "✓ Trivy installed successfully"
            return 0
        else
            log_error "Failed to install Trivy"
            return 1
        fi
    else
        log_error "Unsupported operating system: $(uname -s)"
        log_info "Please install Trivy manually from: https://github.com/aquasecurity/trivy"
        return 1
    fi
}

# Function to run tests on the Docker image
test_docker_image() {
    local image_tag="$1"

    log_info "Testing shell access..."
    if docker run --rm -it "$image_tag" bash -c 'echo "Shell test passed" && whoami && pwd' | grep -q "appuser"; then
        log_info "✓ Shell access test passed (running as non-root user)"
    else
        log_error "✗ Shell access test failed"
        return 1
    fi

    log_info "Testing CLI functionality..."
    if docker run --rm "$image_tag" aurite --version | grep -q "aurite"; then
        log_info "✓ CLI test passed"
    else
        log_error "✗ CLI test failed"
        return 1
    fi

    log_info "Testing API server startup..."
    container_id=$(docker run -d --rm -e API_KEY=test-key-123 -p 8001:8000 "$image_tag")
    sleep 5

    if curl -s -H "X-API-Key: test-key-123" http://localhost:8001/health | grep -q "ok"; then
        log_info "✓ API server test passed"
        docker stop "$container_id" >/dev/null 2>&1
    else
        log_error "✗ API server test failed"
        docker stop "$container_id" >/dev/null 2>&1
        return 1
    fi

    return 0
}

# Main execution
main() {
    cd "$PROJECT_ROOT"

    # Display banner
    echo -e "${CYAN}"
    echo "=============================================="
    echo "   Aurite Docker Release Preparation"
    echo "=============================================="
    echo -e "${NC}"

    # Determine version
    if [ -n "$1" ]; then
        VERSION="$1"
        log_info "Using provided version: $VERSION"
    else
        VERSION=$(get_version_from_pyproject)
        if [ -z "$VERSION" ]; then
            log_error "Could not determine version from pyproject.toml"
            log_info "Please provide version as argument: $0 <VERSION>"
            exit 1
        fi
        log_info "Using version from pyproject.toml: $VERSION"
    fi

    # Check prerequisites
    log_step "Checking prerequisites"

    if ! command_exists docker; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_info "✓ Docker is installed"

    if ! command_exists trivy; then
        if ! install_trivy; then
            log_error "Cannot proceed without Trivy"
            exit 1
        fi
    fi
    log_info "✓ Trivy is installed"

    # Update version in Dockerfile
    log_step "Updating version in Dockerfile"
    sed -i.bak "s/org\.opencontainers\.image\.version=\"[^\"]*\"/org.opencontainers.image.version=\"$VERSION\"/" "$PROJECT_ROOT/Dockerfile"
    rm -f "$PROJECT_ROOT/Dockerfile.bak"
    log_info "✓ Updated Dockerfile version to $VERSION"

    # Update version in docker-entrypoint.sh
    log_step "Updating version in docker-entrypoint.sh"
    sed -i.bak "s/Aurite Agents Framework v[0-9.]\+/Aurite Agents Framework v$VERSION/" "$PROJECT_ROOT/docker-entrypoint.sh"
    rm -f "$PROJECT_ROOT/docker-entrypoint.sh.bak"
    log_info "✓ Updated entrypoint script version to $VERSION"

    # Build the Docker image
    log_step "Building Docker image"

    GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

    log_info "Building with metadata:"
    log_info "  - Version: $VERSION"
    log_info "  - Git commit: $GIT_COMMIT"
    log_info "  - Build date: $BUILD_DATE"

    if docker build \
        --build-arg GIT_COMMIT="$GIT_COMMIT" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        -t "$DOCKER_REPO:$VERSION" \
        -t "$DOCKER_REPO:latest" \
        "$PROJECT_ROOT"; then
        log_info "✓ Docker image built successfully"
    else
        log_error "✗ Docker build failed"
        exit 1
    fi

    # Display image info
    log_step "Image information"
    docker images "$DOCKER_REPO" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

    # Run security scan (mandatory)
    log_step "Running security scan with Trivy"

    log_info "Scanning for vulnerabilities..."
    trivy image --severity HIGH,CRITICAL --format json "$DOCKER_REPO:$VERSION" > /tmp/trivy-report.json 2>&1

    # Also generate human-readable report
    trivy image --severity HIGH,CRITICAL "$DOCKER_REPO:$VERSION" > /tmp/trivy-report.txt 2>&1

    # Check for vulnerabilities in JSON output (more reliable)
    if command_exists jq; then
        # Use jq if available for precise parsing
        vuln_count=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH" or .Severity == "CRITICAL")] | length' /tmp/trivy-report.json 2>/dev/null || echo "error")

        if [ "$vuln_count" = "0" ]; then
            log_info "✓ No HIGH or CRITICAL vulnerabilities found"
        elif [ "$vuln_count" = "error" ]; then
            # Fallback to text parsing if jq fails
            if grep -q "Vulnerabilities" /tmp/trivy-report.txt && ! grep -qE "(HIGH|CRITICAL)" /tmp/trivy-report.txt; then
                log_info "✓ No HIGH or CRITICAL vulnerabilities found"
            else
                log_warn "Could not parse vulnerability report. Check /tmp/trivy-report.txt manually"
                log_warn "Showing potential issues:"
                grep -E "(HIGH|CRITICAL)" /tmp/trivy-report.txt | head -20 || echo "No HIGH/CRITICAL keywords found"

                read -p "Continue anyway? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    log_info "Aborting due to uncertainty about vulnerabilities"
                    exit 1
                fi
            fi
        else
            log_warn "Found $vuln_count HIGH/CRITICAL vulnerabilities"
            log_warn "Full report saved to /tmp/trivy-report.txt"

            # Show summary from text report
            grep -E "(HIGH|CRITICAL)" /tmp/trivy-report.txt | head -20

            read -p "Continue despite vulnerabilities? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Aborting due to security vulnerabilities"
                exit 1
            fi
        fi
    else
        # Fallback when jq is not available - check text report
        if grep -q "Vulnerabilities" /tmp/trivy-report.txt && ! grep -qE "(HIGH|CRITICAL)" /tmp/trivy-report.txt; then
            log_info "✓ No HIGH or CRITICAL vulnerabilities found"
        else
            # Check if there are actual vulnerability entries
            if grep -qE "│.*│.*(HIGH|CRITICAL).*│" /tmp/trivy-report.txt; then
                log_warn "Security vulnerabilities detected:"
                grep -E "(HIGH|CRITICAL)" /tmp/trivy-report.txt | head -20
                log_warn "Full report saved to /tmp/trivy-report.txt"

                read -p "Continue despite vulnerabilities? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    log_info "Aborting due to security vulnerabilities"
                    exit 1
                fi
            else
                log_info "✓ No HIGH or CRITICAL vulnerabilities found"
            fi
        fi
    fi

    # Run functional tests
    log_step "Running functional tests"

    if test_docker_image "$DOCKER_REPO:$VERSION"; then
        log_info "✓ All functional tests passed"
    else
        log_error "✗ Some functional tests failed"
        exit 1
    fi

    # Summary
    log_step "Release preparation complete!"

    echo -e "\n${GREEN}✓ Docker image is ready for release${NC}"
    echo -e "  Repository: ${CYAN}$DOCKER_REPO${NC}"
    echo -e "  Version:    ${CYAN}$VERSION${NC}"
    echo -e "  Tags:       ${CYAN}$VERSION, latest${NC}"

    echo -e "\n${YELLOW}Next steps:${NC}"
    echo "1. Review the changes above"
    echo "2. If everything looks good, push to DockerHub:"
    echo -e "   ${CYAN}docker push $DOCKER_REPO:$VERSION${NC}"
    echo -e "   ${CYAN}docker push $DOCKER_REPO:latest${NC}"
    echo ""
    echo "Or use the publish script:"
    echo -e "   ${CYAN}./scripts/docker/build_and_publish.sh${NC}"

    # Optionally ask if user wants to push now
    echo ""
    read -p "Would you like to push to DockerHub now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_step "Pushing to DockerHub"

        if ! docker info 2>/dev/null | grep -q "Username"; then
            log_info "Please log in to DockerHub:"
            docker login
        fi

        log_info "Pushing $DOCKER_REPO:$VERSION..."
        docker push "$DOCKER_REPO:$VERSION"

        log_info "Pushing $DOCKER_REPO:latest..."
        docker push "$DOCKER_REPO:latest"

        log_info "✓ Successfully pushed to DockerHub!"
        echo -e "\n${GREEN}🎉 Release complete!${NC}"
        echo "View on DockerHub: https://hub.docker.com/r/$DOCKER_REPO"
    else
        log_info "Skipping push to DockerHub"
        log_info "You can push manually later with:"
        echo -e "   ${CYAN}docker push $DOCKER_REPO:$VERSION${NC}"
        echo -e "   ${CYAN}docker push $DOCKER_REPO:latest${NC}"
    fi
}

# Run main function
main "$@"
