FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mock model server
COPY model_server.py .

# Set environment variables
ENV PORT=8000
ENV MODEL_NAME=mock-model
ENV MODEL_VERSION=1.0.0
ENV LOG_LEVEL=INFO

# Expose the port
EXPOSE ${PORT}

# Run the application
CMD ["sh", "-c", "uvicorn model_server:app --host 0.0.0.0 --port $PORT"]
