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

# Set working directory
WORKDIR /build

# Copy the entire project context
# .dockerignore will handle exclusions
COPY . .

# Install poetry
RUN pip install poetry

# Configure poetry to install packages to the system python
RUN poetry config virtualenvs.create false

# Install all dependencies, including the project itself in editable mode, from the lock file.
# This is the single source of truth for dependencies.
RUN poetry install --with storage

# Runtime stage
FROM python:3.12-slim

# Install runtime dependencies
# We need curl and netcat for healthcheck, libpq5 for psycopg2
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
        netcat-traditional && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy necessary artifacts from the builder stage
# Copy installed Python packages (including dev dependencies and editable install)
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
# Copy the source code (needed for editable install runtime and reload)
COPY --from=builder /build/src/ ./src/
# Copy pyproject.toml (might be needed by runtime tools or for reference)
COPY --from=builder /build/pyproject.toml .
# tests/ directory is not copied to the production image

# Create cache directory with proper permissions
# Ensure the directory exists before changing ownership
RUN mkdir -p /app/cache && chown -R appuser:appuser /app /app/cache && chmod 755 /app/cache

# Switch to non-root user
USER appuser

# Set environment variables
# - PYTHONPATH ensures modules in /app/src are found
# - PROJECT_CONFIG_PATH points to the desired config file
# - Other vars as needed
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    ENV=production \
    CACHE_DIR=/app/cache \
    PROJECT_CONFIG_PATH=/app/config/projects/testing_config.json \
    AURITE_ALLOW_DYNAMIC_REGISTRATION=true \
    LOG_LEVEL=INFO

# Expose the correct port (default 8000 for the API)
EXPOSE 8000

# Health check - use netcat to check if port is open first, then curl health endpoint
# Use port 8000 and correct path /health
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD nc -z localhost 8000 && curl -f http://localhost:8000/health || exit 1

# Command to run the application
# Point to the correct app location: aurite.bin.api.api:app
# Use port 8000
CMD ["python", "-m", "uvicorn", "aurite.bin.api.api:app", "--host", "0.0.0.0", "--port", "8000"]
