FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY mocks/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt requests

# Copy mock model server
COPY mocks/model_server.py .

# Create config directory
RUN mkdir -p /app/config/models

# Set default environment variables
ENV PORT=8000
ENV MODEL_NAME=mock-model
ENV MODEL_VERSION=1.0.0
ENV LOG_LEVEL=INFO

# Expose the port the app runs on
EXPOSE ${PORT}

# Run the application
CMD exec uvicorn model_server:app --host 0.0.0.0 --port $PORT