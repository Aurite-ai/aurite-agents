# =============================================================================
# Aurite Agents Framework - Public Docker Image
# =============================================================================
# This Dockerfile creates a production-ready container for the Aurite Agents
# framework, installing it as a proper Python package.
#
# Build:
#   docker build -t aurite/aurite-agents:latest .
#   docker build --build-arg GIT_COMMIT=$(git rev-parse HEAD) \
#                --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
#                -t aurite/aurite-agents:latest .
#
# Usage:
#   docker run -v /path/to/project:/app/project -p 8000:8000 \
#              -e API_KEY=your-secure-key aurite/aurite-agents
#
# Security Notes:
#   - Container runs as non-root user (appuser, UID 1000)
#   - API_KEY environment variable is required for API authentication
#   - Use reverse proxy with TLS in production
#   - Consider using Docker secrets for sensitive data
#
# For more examples, see: https://github.com/Aurite-ai/aurite-agents
# =============================================================================

# Build stage
FROM python:3.12-slim@sha256:d67a7b66b989ad6b6d6b10d428dcc5e0bfc3e5f88906e67d490c4d3daac57047 AS builder

# Install build dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        python3-dev \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory for build
WORKDIR /build

# Upgrade pip for better wheel handling
RUN pip install --upgrade pip

# Copy the requirements files first for better caching
COPY src/ ./src/
COPY pyproject.toml .
COPY docker-entrypoint.sh .
COPY LICENSE .
COPY README.md .
COPY requirements.txt .

# Build wheel for aurite-agents and all its dependencies
# This creates wheels in /wheels directory for faster installation
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

# Install all wheels (aurite-agents and dependencies)
RUN pip install --no-cache-dir --no-deps /wheels/*.whl

# =============================================================================
# Runtime stage
# =============================================================================
FROM python:3.12-slim@sha256:d67a7b66b989ad6b6d6b10d428dcc5e0bfc3e5f88906e67d490c4d3daac57047

# Build arguments for metadata
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown

# Add metadata labels for DockerHub
LABEL org.opencontainers.image.title="Aurite Agents Framework" \
      org.opencontainers.image.description="A Python framework for building, testing, and running AI agents with MCP integration" \
      org.opencontainers.image.url="https://github.com/Aurite-ai/aurite-agents" \
      org.opencontainers.image.source="https://github.com/Aurite-ai/aurite-agents" \
      org.opencontainers.image.documentation="https://github.com/Aurite-ai/aurite-agents/blob/main/README.md" \
      org.opencontainers.image.vendor="Aurite AI" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="0.4.0" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="Ryan W <ryan@aurite.ai>, Blake R <blake@aurite.ai>, Jiten Oswal <jiten@aurite.ai>" \
      maintainer="Aurite AI <hello@aurite.ai>"


# Install runtime dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security with explicit home directory
RUN useradd -m -u 1000 -d /home/appuser appuser

# Create application directories
RUN mkdir -p /app/project /app/cache && \
    chown -R appuser:appuser /app

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy entrypoint script if it exists
COPY --chown=appuser:appuser docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Set working directory to where user projects will be mounted
WORKDIR /app/project

# Set environment variables
# No PYTHONPATH needed - aurite is properly installed as a package
ENV PYTHONUNBUFFERED=1 \
    AURITE_PROJECT_DIR=/app/project

# Expose the API port
EXPOSE 8000

# Health check using Python to check the health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${AURITE_API_PORT:-8000}/health').read()" || exit 1

# Use custom entrypoint script for initialization logic
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command - start the API server
CMD ["python", "-m", "uvicorn", "aurite.bin.api.api:app", "--host", "0.0.0.0", "--port", "8000"]
