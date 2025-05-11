#!/bin/bash
# Setup script for ML Orchestrator development environment

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== ML Orchestrator Development Environment Setup ===${NC}"

# Check if Python 3.11+ is installed
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo -e "${BLUE}Detected Python version: ${python_version}${NC}"

python_major=$(echo $python_version | cut -d'.' -f1)
python_minor=$(echo $python_version | cut -d'.' -f2)

if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 11 ]); then
    echo -e "${RED}Python 3.11 or higher is required!${NC}"
    echo -e "${YELLOW}Please install Python 3.11+ and try again.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv venv
else
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install -r requirements.txt

# Install development dependencies
echo -e "${BLUE}Installing development dependencies...${NC}"
pip install pytest pytest-cov pytest-asyncio black ruff mypy pre-commit

# Setup pre-commit hooks
echo -e "${BLUE}Setting up pre-commit hooks...${NC}"
if [ ! -f ".git/hooks/pre-commit" ]; then
    pre-commit install
else
    echo -e "${YELLOW}Pre-commit hooks already installed.${NC}"
fi

# Create default config directories
echo -e "${BLUE}Setting up config directories...${NC}"
mkdir -p config/models

# Create default environment variables file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating default .env file...${NC}"
    cat > .env << EOF
# ML Orchestrator Environment Variables
APP_NAME=ML Orchestrator
APP_VERSION=1.0.0
DEBUG=True

# Server settings
HOST=0.0.0.0
PORT=8000
WORKERS=1

# Config file paths
CONFIG_DIR=./config
MODELS_REGISTRY_FILE=./config/models_registry.yaml

# Default service settings
DEFAULT_TIMEOUT=30.0
DEFAULT_MAX_RETRIES=3

# Circuit breaker defaults
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RESET_TIMEOUT=30.0

# Admin API settings
ADMIN_API_ENABLED=True
ADMIN_API_KEY=dev_admin_key

# Metrics settings
METRICS_ENABLED=False

# Logging
LOG_LEVEL=INFO
EOF
else
    echo -e "${YELLOW}.env file already exists.${NC}"
fi

# Create default models registry file if it doesn't exist
if [ ! -f "config/models_registry.yaml" ]; then
    echo -e "${BLUE}Creating default models registry file...${NC}"
    cat > config/models_registry.yaml << EOF
# ML Orchestrator Models Registry
version: "1.0"
models:
  - id: model_1
    file: models/model_1.yaml
  - id: model_2
    file: models/model_2.yaml
EOF
else
    echo -e "${YELLOW}models_registry.yaml already exists.${NC}"
fi

# Create default model configuration files
for model in model_1 model_2; do
    if [ ! -f "config/models/${model}.yaml" ]; then
        echo -e "${BLUE}Creating default config for ${model}...${NC}"
        cat > "config/models/${model}.yaml" << EOF
# ${model} Configuration
id: ${model}
name: Example ${model}
description: Example model for development
endpoint_url: http://localhost:8888/${model}
version: "1.0"
timeout: 10.0
max_retries: 2
circuit_breaker:
  failure_threshold: 3
  reset_timeout: 15.0
auth:
  type: api_key
  key_name: X-API-Key
  key_value: "dev_model_key"
  location: header
cache:
  enabled: true
  ttl: 300
  max_size: 100
headers:
  X-Source: ml-orchestrator
active: true
EOF
    else
        echo -e "${YELLOW}Configuration for ${model} already exists.${NC}"
    fi
done

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}To activate the virtual environment, run:${NC}"
echo -e "    source venv/bin/activate"
echo -e "${BLUE}To run the application:${NC}"
echo -e "    python -m app.main"
echo -e "${BLUE}To run tests:${NC}"
echo -e "    python -m pytest"
echo -e "${BLUE}To run tests with coverage:${NC}"
echo -e "    python -m pytest --cov=app"
echo -e "${BLUE}Happy coding!${NC}"