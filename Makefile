.PHONY: help setup venv install dev-install lint test test-cov test-e2e test-integration coverage docker docker-compose docker-compose-safe docker-compose-down docker-push docker-push-local docker-save run run-mock mock-up mock-down clean clean-all distclean format check update-deps verify-models verify-orchestrator configure-models-host configure-models-docker

# Default Python interpreter (3.8+ required)
PYTHON ?= python3

# Virtual environment directory
VENV_DIR ?= .venv
PYTHON_BIN ?= $(VENV_DIR)/bin/python
PIP_BIN ?= $(VENV_DIR)/bin/pip

# Application settings
APP_MODULE = app.main:app
HOST ?= 0.0.0.0
PORT ?= 8000
ENV ?= development
WORKERS ?= 1

# Docker settings
DOCKER_COMPOSE = docker-compose
DOCKER_COMPOSE_FILE = docker-compose.yml
DOCKER_IMAGE = ml-orchestrator
DOCKER_TAG = latest
DOCKER_REGISTRY ?= 

# Help message
help:
	@echo "\nML Service Orchestrator"
	@echo "======================="
	@echo "\nDevelopment:"
	@echo "  make setup         - Create virtual environment and install all dependencies"
	@echo "  make dev-install   - Install in development mode (-e flag)"
	@echo "  make install       - Install the package"
	@echo "  make venv          - Create virtual environment"
	@echo "  make lint          - Run linting checks (ruff, black, mypy)"
	@echo "  make format        - Format code with black and ruff"
	@echo "  make update-deps   - Update dependencies in requirements.txt"
	@echo "\nTesting:"
	@echo "  make test          - Run unit tests"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo "  make test-e2e      - Run end-to-end tests with mock models"
	@echo "  make test-integration - Run integration tests"
	@echo "  make check         - Run all checks (lint, typecheck, test)"
	@echo "  make verify-models - Verify mock models are running correctly"
	@echo "  make verify-orchestrator - Verify orchestrator is running correctly"
	@echo "\nModel Configuration:"
	@echo "  make configure-models-host   - Configure models for host-to-container communication"
	@echo "  make configure-models-docker - Configure models for container-to-container communication"
	@echo "\nRunning:"
	@echo "  make run           - Run the orchestrator application"
	@echo "  make mock-up       - Start mock models with Docker Compose"
	@echo "  make mock-down     - Stop mock models"
	@echo "  make docker        - Build Docker image and start containers"
	@echo "  make docker-compose - Run with docker-compose"
	@echo "  make docker-compose-safe - Run with docker-compose ensuring network exists"
	@echo "  make docker-push   - Push Docker image to registry"
	@echo "  make docker-push-local - Push Docker image to local registry"
	@echo "  make docker-save   - Save Docker image to dist/ folder as tar file"
	@echo "\nCleanup:"
	@echo "  make clean         - Clean up build artifacts"
	@echo "  make clean-all     - Clean everything including virtualenv and Docker resources"

# Setup
setup: venv install dev-install

# Create virtual environment
venv:
	@echo "Creating virtual environment in $(VENV_DIR)..."
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP_BIN) install --upgrade pip setuptools wheel

# Install package in development mode
dev-install:
	@echo "Installing in development mode..."
	$(PIP_BIN) install -e ".[dev]"
	pre-commit install

# Install package
install:
	@echo "Installing package..."
	$(PIP_BIN) install .

# Linting and formatting
lint:
	@echo "Running linters..."
	$(VENV_DIR)/bin/ruff check app tests
	$(VENV_DIR)/bin/black --check app tests
	$(VENV_DIR)/bin/mypy app

format:
	@echo "Formatting code..."
	$(VENV_DIR)/bin/ruff check --fix app tests
	$(VENV_DIR)/bin/black app tests

# Testing
test:
	@echo "Running unit tests..."
	$(VENV_DIR)/bin/pytest -v tests/

test-cov:
	@echo "Running tests with coverage..."
	$(VENV_DIR)/bin/pytest --cov=app --cov-report=term-missing --cov-report=html tests/

test-e2e: mock-up
	@echo "Running end-to-end tests with mock models..."
	@echo "Waiting for mock models to start..."
	sleep 3
	@echo "Verifying mock models..."
	$(MAKE) verify-models
	@echo "Configuring models for host-to-container communication..."
	$(MAKE) configure-models-host
	@echo "Starting orchestrator..."
	APP_ENV=test $(VENV_DIR)/bin/python -m app.main & echo $$! > orchestrator.pid
	@echo "Waiting for orchestrator to start..."
	sleep 3
	@echo "Verifying orchestrator..."
	$(MAKE) verify-orchestrator
	@echo "Running test requests..."
	curl -s -X POST http://localhost:8000/api/v1/models/mock-model-1 -H "Content-Type: application/json" -d '{"input": "test input"}' | jq || echo "Test failed"
	@echo "Stopping orchestrator..."
	-kill `cat orchestrator.pid` && rm orchestrator.pid
	$(MAKE) mock-down
	@echo "End-to-end tests completed"

test-integration:
	@echo "Running integration tests..."
	$(VENV_DIR)/bin/pytest -v tests/test_integration/

coverage: test-cov

verify-models:
	@echo "Verifying mock models..."
	curl -s http://localhost:8001/health || echo "Mock model 1 not responding"
	curl -s http://localhost:8002/health || echo "Mock model 2 not responding"
	curl -s http://localhost:8003/health || echo "Mock model 3 not responding"

verify-orchestrator:
	@echo "Verifying orchestrator..."
	curl -s http://localhost:8000/health || echo "Orchestrator not responding"
	curl -s http://localhost:8000/api/v1/models || echo "Orchestrator models endpoint not responding"

check: lint test

# Running the application
run:
	@echo "Starting ML Service Orchestrator..."
	$(VENV_DIR)/bin/uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

# Mock model commands
mock-up:
	@echo "Starting mock models..."
	docker-compose -f mocks/docker-compose.yml up -d

mock-down:
	@echo "Stopping mock models..."
	docker-compose -f mocks/docker-compose.yml down

# Model configuration commands
configure-models-host:
	@echo "Configuring models for host-to-container communication..."
	@mkdir -p config/local/models
	@if [ -f config/local/models/mock-model-1.yaml ]; then \
		sed -i '' 's|http://mock-model-1:8000|http://localhost:8001|g' config/local/models/mock-model-1.yaml || \
		sed -i 's|http://mock-model-1:8000|http://localhost:8001|g' config/local/models/mock-model-1.yaml; \
	fi
	@if [ -f config/local/models/mock-model-2.yaml ]; then \
		sed -i '' 's|http://mock-model-2:8000|http://localhost:8002|g' config/local/models/mock-model-2.yaml || \
		sed -i 's|http://mock-model-2:8000|http://localhost:8002|g' config/local/models/mock-model-2.yaml; \
	fi
	@if [ -f config/local/models/mock-model-3.yaml ]; then \
		sed -i '' 's|http://mock-model-3:8000|http://localhost:8003|g' config/local/models/mock-model-3.yaml || \
		sed -i 's|http://mock-model-3:8000|http://localhost:8003|g' config/local/models/mock-model-3.yaml; \
	fi
	@echo "Models configured for host-to-container communication"

configure-models-docker:
	@echo "Configuring models for container-to-container communication..."
	@mkdir -p config/local/models
	@if [ -f config/local/models/mock-model-1.yaml ]; then \
		sed -i '' 's|http://localhost:8001|http://mock-model-1:8000|g' config/local/models/mock-model-1.yaml || \
		sed -i 's|http://localhost:8001|http://mock-model-1:8000|g' config/local/models/mock-model-1.yaml; \
	fi
	@if [ -f config/local/models/mock-model-2.yaml ]; then \
		sed -i '' 's|http://localhost:8002|http://mock-model-2:8000|g' config/local/models/mock-model-2.yaml || \
		sed -i 's|http://localhost:8002|http://mock-model-2:8000|g' config/local/models/mock-model-2.yaml; \
	fi
	@if [ -f config/local/models/mock-model-3.yaml ]; then \
		sed -i '' 's|http://localhost:8003|http://mock-model-3:8000|g' config/local/models/mock-model-3.yaml || \
		sed -i 's|http://localhost:8003|http://mock-model-3:8000|g' config/local/models/mock-model-3.yaml; \
	fi
	@echo "Models configured for container-to-container communication"

# Docker commands
docker:
	@echo "Building Docker image..."
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "Starting Docker containers..."
	$(MAKE) docker-compose-safe

# Push Docker image to registry
# Usage: make docker-push DOCKER_REGISTRY=your-registry.com/
docker-push:
	@echo "Pushing Docker image to registry..."
	@if [ -z "$(DOCKER_REGISTRY)" ]; then \
		echo "Error: DOCKER_REGISTRY is not set. Usage: make docker-push DOCKER_REGISTRY=your-registry.com/"; \
		exit 1; \
	fi
	@echo "Using registry: $(DOCKER_REGISTRY)"
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_REGISTRY)$(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push $(DOCKER_REGISTRY)$(DOCKER_IMAGE):$(DOCKER_TAG)

# Push Docker image to local registry
docker-push-local:
	@echo "Pushing Docker image to local registry..."
	@echo "Using local registry: localhost:5001"
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) localhost:5001/$(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push localhost:5001/$(DOCKER_IMAGE):$(DOCKER_TAG)
	@echo "Image pushed to local registry and available as: localhost:5001/$(DOCKER_IMAGE):$(DOCKER_TAG)"

# Save Docker image to a tar file in the dist directory
docker-save:
	@echo "Saving Docker image to dist/$(DOCKER_IMAGE)-$(DOCKER_TAG).tar..."
	@mkdir -p dist
	docker save $(DOCKER_IMAGE):$(DOCKER_TAG) -o dist/$(DOCKER_IMAGE)-$(DOCKER_TAG).tar
	@echo "Image saved to dist/$(DOCKER_IMAGE)-$(DOCKER_TAG).tar"

docker-compose:
	@echo "Starting services with docker-compose..."
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) up --build -d

docker-compose-safe:
	@echo "Ensuring Docker network exists..."
	docker network inspect ml-network >/dev/null 2>&1 || docker network create ml-network
	@echo "Starting services with docker-compose..."
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) up --build -d

docker-compose-down:
	@echo "Stopping Docker Compose services..."
	$(DOCKER_COMPOSE) down

run-mock:
	@echo "Starting mock models..."
	$(DOCKER_COMPOSE) -f mocks/$(DOCKER_COMPOSE_FILE) up --build -d

# Cleanup commands
clean:
	@echo "Cleaning up build artifacts..."
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Remove all build artifacts
distclean: clean
	@echo "Removing build artifacts..."
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/

# Remove everything including virtual environment and Docker resources
clean-all: clean distclean mock-down docker-compose-down
	@echo "Removing virtual environment and cleaning Docker resources..."
	rm -rf $(VENV_DIR)
	docker system prune -f

# Update dependencies
update-deps:
	@echo "Updating requirements files..."
	$(PIP_BIN) freeze > requirements.txt

# Default target
.DEFAULT_GOAL := help
