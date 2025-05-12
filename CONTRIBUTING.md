# Contributing to ML Orchestrator Service

Thank you for your interest in contributing to the ML Orchestrator Service! This guide will help you get started with the development process.

## Development Environment Setup

### Quick Setup

Use our setup script for a quick start:

```bash
./scripts/setup_dev.sh
```

### Manual Setup

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
pip install -e .  # Install project in development mode
pip install pytest pytest-cov pytest-asyncio black ruff mypy pre-commit
```

3. Install pre-commit hooks:

```bash
pre-commit install
```

## Development Workflow

### Makefile Commands

We provide a Makefile with common development commands:

- `make setup` - Set up the development environment
- `make lint` - Run linting checks
- `make test` - Run the test suite
- `make test-cov` - Run tests with coverage
- `make format` - Format code with black and ruff
- `make run` - Run the application locally

### Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test files
pytest tests/test_api/test_dependencies.py
```

### Code Formatting

Format your code with black:

```bash
black app tests
```

Check your code with ruff:

```bash
ruff check app tests
```

Type checking with mypy:

```bash
mypy app
```

## Git Workflow

### Branching Strategy

We follow a feature branch workflow:

1. Create a branch for your feature or fix:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make changes, commit with descriptive messages, and push:

   ```bash
   git add .
   git commit -m "Add feature xyz"
   git push origin feature/your-feature-name
   ```

3. Create a pull request on GitHub

### Commit Message Guidelines

Follow these guidelines for commit messages:

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests after the first line

Example:

```
Add circuit breaker pattern to model requests

- Implement CircuitBreaker class
- Add automatic recovery mechanism
- Add tests for circuit breaker functionality

Fixes #123
```

## Code Review Process

### Pull Request Guidelines

When submitting a PR:

1. Fill out the PR template
2. Include test coverage for new code
3. Make sure all CI checks pass
4. Update documentation if necessary
5. Reference any related issues

### Review Criteria

Pull requests are evaluated based on:

- Functional correctness
- Test coverage (aim for 80%+)
- Code quality and style
- Documentation quality
- Performance considerations

## Testing Guidelines

### Test Coverage

Aim for at least 80% test coverage for new code. Use the coverage report to identify untested code:

```bash
pytest --cov=app --cov-report=term-missing
```

### Test Structure

- Place tests in the `tests/` directory following the application structure
- Name test files with a `test_` prefix
- Name test functions with descriptive names indicating what they test
- Use pytest fixtures for test setup and teardown

### Test Types

Write different types of tests:

- **Unit tests**: Test individual functions or classes
- **Integration tests**: Test interactions between components
- **API tests**: Test API endpoints using FastAPI TestClient
- **Async tests**: Use pytest-asyncio for testing async code

## Documentation

### Code Documentation

- Document all public functions, classes, and methods with docstrings
- Use type hints for function parameters and return values
- Add inline comments for complex code sections

### API Documentation

API endpoints are documented using OpenAPI/Swagger. Access the docs at:

- `/docs` - Swagger UI
- `/redoc` - ReDoc UI

## Troubleshooting

### Common Issues

- **Import errors**: Make sure your PYTHONPATH includes the project root
- **Test failures**: Check for missing test dependencies
- **Pre-commit hook failures**: Run the failed hooks manually to debug

### Getting Help

If you need help, you can:

- Open an issue on GitHub
- Ask in the project's discussions area
- Contact the maintainers directly

## Architecture Overview

### Key Components

1. **API Layer** (`app/api/`):

   - API routes and endpoint handlers
   - Request/response models
   - Dependency injection

2. **Service Layer** (`app/services/`):

   - Business logic implementation
   - Model registry service
   - Proxy service for model requests

3. **Core Layer** (`app/core/`):

   - Core domain models
   - Orchestrator implementation
   - Exception handling

4. **Configuration** (`app/config/`):

   - Application settings
   - Model configuration management

5. **Utilities** (`app/utils/`):
   - HTTP utilities
   - Logging setup
   - Shared helper functions

## License

By contributing to this project, you agree that your contributions will be licensed under the project's license.

## Configuration and Testing System Updates

### Configuration Management

- The application uses Pydantic's `BaseSettings` for configuration, defined in `app/config/settings.py`.
- Environment variables and config files in `config/env/` are supported. `.env` files are not required; settings can be overridden via environment variables or config files.
- Default values are provided in the settings classes, making local development and CI setup easier.

### Test Settings

- Test settings are managed via the `TestSettings` class in `tests/mocks/settings.py`.
- The test environment is set automatically (`APP_ENV=test`), and test-specific config files can be placed in `config/env/test.cfg` if needed.

### Model Registry

- The legacy `MODELS_REGISTRY_FILE` has been removed. The application now uses per-model config files in the `config/models/` directory.
- Each model has its own YAML or JSON config file, improving modularity and maintainability.

### Deprecation Warnings

- You may see warnings about Pydantic V1 `@validator` usage and FastAPI's `@app.on_event` deprecation. These do not affect functionality but should be addressed in future updates:
  - Migrate to Pydantic V2 `@field_validator`.
  - Use FastAPI lifespan event handlers instead of `@app.on_event`.
