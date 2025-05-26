FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create config directory and copy model configurations
RUN mkdir -p /app/config/models
COPY config/local/models/*.yaml /app/config/models/

# Copy application code
COPY ./app /app

# Expose the port the app runs on
EXPOSE 8000

# Set environment variables
ENV MODEL_CONFIG_DIR=/app/config/models
ENV PYTHONPATH=/app

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
