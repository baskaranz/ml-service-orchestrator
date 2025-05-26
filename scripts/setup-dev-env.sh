#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up development environment...${NC}"

# Create necessary directories
mkdir -p config/dev/models
mkdir -p logs

# Create .env file if it doesn't exist
if [ ! -f .env.dev ]; then
    echo -e "${GREEN}Creating .env.dev file...${NC}"
    cat > .env.dev <<EOL
# Development Environment Variables
ENVIRONMENT=dev
LOG_LEVEL=DEBUG
PORT=8000
HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://devuser:devpassword@db:5432/devdb

# Redis
REDIS_URL=redis://redis:6379/0

# Security (generate new secrets for production!)
SECRET_KEY=dev-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS
CORS_ORIGINS=["*"]

# Model Configuration
MODEL_CONFIG_DIR=/app/config/dev/models

# Development Settings
RELOAD=true
WORKERS=2
EOL
    echo -e "${GREEN}.env.dev created${NC}"
else
    echo -e "${GREEN}.env.dev already exists, skipping...${NC}"
fi

# Create a basic model configuration if none exists
if [ ! -f config/dev/models/example_model.json ]; then
    echo -e "${GREEN}Creating example model configuration...${NC}"
    mkdir -p config/dev/models
    cat > config/dev/models/example_model.json <<EOL
{
  "name": "example-model",
  "version": "1.0.0",
  "endpoint": "http://example-model:8000/predict",
  "timeout": 30,
  "max_retries": 3,
  "batch_size": 32,
  "enabled": true,
  "metadata": {
    "description": "Example model configuration",
    "author": "Development Team"
  }
}
EOL
    echo -e "${GREEN}Example model configuration created at config/dev/models/example_model.json${NC}"
fi

echo -e "${GREEN}Development environment setup complete!${NC}"
echo -e "${GREEN}To start the development environment, run:${NC}"
echo "docker-compose -f docker-compose.cloud-dev.yml up --build"
