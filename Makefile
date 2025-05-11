.PHONY: help setup lint test test-cov coverage docker run clean format check update-deps

# Default python interpreter
PYTHON ?= python

# Default virtual environment dir
VENV_DIR ?= venv

# Application port
PORT ?= 8000

# Default settings
ENV ?= development

help:
	@echo "ML Orchestrator Service"
	@echo "======================="
	@echo "make setup        - Create virtual environment and install dependencies"
	@echo "make lint         - Run linting checks"
	@echo "make test         - Run tests"
	@echo "make test-cov     - Run tests with coverage"
	@echo "make coverage     - Generate HTML coverage report"
	@echo "make docker       - Build Docker image"
	@echo "make run          - Run the application"
	@echo "make clean        - Clean up build artifacts"
	@echo "make format       - Format code with black and ruff"
	@echo "make check        - Run all checks (lint, typecheck, test)"
	@echo "make update-deps  - Update dependencies in requirements.txt"

setup:
	@echo "Setting up development environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -r requirements.txt
	$(VENV_DIR)/bin/pip install -e .
	$(VENV_DIR)/bin/pip install pytest pytest-cov pytest-asyncio black ruff mypy pre-commit
	pre-commit install
	@echo "Setup complete! Activate your virtual environment with:"
	@echo "source $(VENV_DIR)/bin/activate"

lint:
	@echo "Running linters..."
	ruff check app tests
	black --check app tests
	mypy app

test:
	@echo "Running tests..."
	pytest -v

test-cov:
	@echo "Running tests with coverage..."
	pytest --cov=app --cov-report=term-missing

coverage:
	@echo "Generating coverage report..."
	pytest --cov=app --cov-report=html
	@echo "Coverage report generated in htmlcov/ directory"
	@echo "Open htmlcov/index.html in your browser to view"

docker:
	@echo "Building Docker image..."
	docker build -t ml-orchestrator:latest .

run:
	@echo "Running the application..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port $(PORT) --log-level debug

clean:
	@echo "Cleaning up..."
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

format:
	@echo "Formatting code..."
	black app tests
	ruff check --fix app tests

check: lint test
	@echo "All checks passed!"

update-deps:
	@echo "Updating dependencies..."
	pip freeze | grep -v ml-orchestrator > requirements.txt
	@echo "Dependencies updated in requirements.txt"