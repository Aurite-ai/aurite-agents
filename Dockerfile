# Build stage
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update &&
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libpq-dev &&
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY config/ ./config/

COPY alembic.ini .

# Install dependencies and build package
RUN pip install --no-cache-dir .

# Runtime stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update &&
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        libpq5 &&
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy built package and dependencies from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /build/src/ ./src/
COPY --from=builder /build/alembic.ini .

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV APPLY_MIGRATIONS=true
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health/live || exit 1

# Run the application
CMD ["python", "-c", "from src.app import start; start()"]
