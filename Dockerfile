# ML Service Orchestrator
# Production-ready Dockerfile

# Build stage for optimized dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir 'httpx[http2]'

# Final stage for runtime
FROM python:3.11-slim

LABEL maintainer="ML Orchestrator Team" \
      version="1.0.0" \
      description="ML Service Orchestrator for managing and routing requests to ML models"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000 \
    HOST=0.0.0.0 \
    WORKERS=4 \
    CONFIG_DIR=/app/config/production \
    MODELS_DIR=/app/config/production/models

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/config/production/models && \
    chmod -R 755 /app

# Copy application code
COPY app/ /app/app/
COPY config/ /app/config/
COPY scripts/ /app/scripts/

# Copy essential files
COPY README.md .
COPY run-instructions.md .

# Create a non-root user and change ownership
RUN groupadd -r orchestrator && \
    useradd -r -g orchestrator -d /app -s /bin/bash orchestrator && \
    chown -R orchestrator:orchestrator /app

# Switch to non-root user
USER orchestrator

# Expose the port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Command to run the application
CMD ["sh", "-c", "uvicorn app.main:app --host ${HOST} --port ${PORT} --workers ${WORKERS}"]