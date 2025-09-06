# =============================================================================
# Aurite Agents Framework - Public Docker Image
# =============================================================================
# This Dockerfile creates a production-ready container for the Aurite Agents
# framework that can be published to DockerHub for public use.
#
# Usage:
#   docker run -v /path/to/project:/app/project -p 8000:8000 aurite/aurite-agents
#
# For more examples, see: https://github.com/Aurite-ai/aurite-agents
# =============================================================================

# Build stage
FROM python:3.12-slim AS builder

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

# Copy the entire project context
# .dockerignore will handle exclusions
COPY . .

# Install poetry
RUN pip install poetry

# Configure poetry to install packages to the system python
RUN poetry config virtualenvs.create false

# Install all dependencies, including the project itself in editable mode
# This is the single source of truth for dependencies
# Install dependencies using the lock file
RUN poetry install --no-root --with storage

# Then install the project itself
RUN poetry install --only-root


# =============================================================================
# Runtime stage
# =============================================================================
FROM python:3.12-slim

# Add metadata labels for DockerHub
LABEL org.opencontainers.image.title="Aurite Agents Framework" \
      org.opencontainers.image.description="A Python framework for building, testing, and running AI agents with MCP integration" \
      org.opencontainers.image.url="https://github.com/Aurite-ai/aurite-agents" \
      org.opencontainers.image.source="https://github.com/Aurite-ai/aurite-agents" \
      org.opencontainers.image.documentation="https://github.com/Aurite-ai/aurite-agents/blob/main/README.md" \
      org.opencontainers.image.vendor="Aurite AI" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="0.3.28" \
      org.opencontainers.image.authors="Ryan W <ryan@aurite.ai>, Blake R <blake@aurite.ai>, Jiten Oswal <jiten@aurite.ai>" \
      org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
      maintainer="Aurite AI <hello@aurite.ai>"

# Install runtime dependencies
# We need curl for healthcheck, libpq5 for psycopg2, python3 for health check script
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Create application directories
RUN mkdir -p /app/src /app/project /app/cache && \
    chown -R appuser:appuser /app

# Copy necessary artifacts from the builder stage
# Copy installed Python packages (including dev dependencies and editable install)
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
# Copy the source code (needed for editable install runtime and reload)
COPY --from=builder /build/src/ /app/src/
# Copy pyproject.toml (might be needed by runtime tools or for reference)
COPY --from=builder /build/pyproject.toml /app/
# Copy entrypoint script
COPY --from=builder /build/docker-entrypoint.sh /app/

# Make entrypoint executable and ensure proper ownership
RUN chmod +x /app/docker-entrypoint.sh && \
    chown appuser:appuser /app/docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Set working directory to where user projects will be mounted
WORKDIR /app/project

# Set environment variables
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

# Expose the API port
EXPOSE 8000

# Health check - use Python to check the health endpoint
# This avoids dependency on external tools and provides better error messages
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${AURITE_API_PORT:-8000}/health').read()" || exit 1

# Use custom entrypoint script for initialization logic
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command - start the API server
CMD ["python", "-m", "uvicorn", "aurite.bin.api.api:app", "--host", "0.0.0.0", "--port", "8000"]
