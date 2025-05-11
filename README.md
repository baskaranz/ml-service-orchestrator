# Service Orchestrator

A flexible and robust service orchestrator that provides unified access, monitoring, and management capabilities for various services including ML models, databases, and external APIs.

## Features

- **Unified API Gateway**: Single entry point for all your services
- **Dynamic Service Registration**: Add or remove services without restart
- **Circuit Breaker**: Automatic failure detection and recovery
- **Request/Response Transformation**: Transform data between different service formats
- **Health Monitoring**: Real-time health checks for all services
- **Authentication**: Flexible authentication mechanisms per service
- **Caching**: Optional response caching with configurable TTL
- **Metrics & Logging**: Comprehensive monitoring and debugging
- **Data Integration**: Connect to databases and external APIs
- **Service Composition**: Combine multiple services into unified workflows

## Quick Start

1. **Installation**:

```bash
# Clone the repository
git clone <repository-url>
cd service-orchestrator

# Set up development environment
./scripts/setup_dev.sh

# Activate virtual environment
source venv/bin/activate
```

2. **Running Dummy Models**:

The orchestrator comes with a set of dummy model servers for testing. To start them:

```bash
# Start dummy model servers (runs on ports 8001-8010)
python app/scripts/run_dummy_servers.py
```

3. **Running the Orchestrator**:

```bash
# Start the orchestrator (runs on port 8000)
python app/main.py
```

## Model Configuration

### Model Configuration Structure

Each model is configured using a YAML file in the `config/models` directory. Example configuration:

```yaml
active: true
circuit_breaker:
  failure_threshold: 5
  reset_timeout: 60.0
  exclude_exceptions: []
description: "A dummy model for testing"
endpoint_url: http://localhost:8001
headers: {}
id: dummy-model-1
max_retries: 3
name: Dummy Model 1
timeout: 30.0
version: 1.0.0
```

### Generating Dummy Model Configurations

To generate configurations for dummy models:

```bash
# Generate configurations for 10 dummy models
python app/scripts/generate_dummy_configs.py
```

This will create YAML files for 10 dummy models in the `config/models` directory.

## API Usage

### Model Endpoints

```bash
# Forward a request to a model
curl -X POST http://localhost:8000/orchestrator/models/{model_id} \
  -H "Content-Type: application/json" \
  -d '{"input": "your input data"}'

# Example with dummy-model-1
curl -X POST http://localhost:8000/orchestrator/models/dummy-model-1 \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'
```

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health status
curl http://localhost:8000/health/details
```

## Development

### Project Structure

```
service-orchestrator/
├── app/
│   ├── api/          # API routes and endpoints
│   ├── core/         # Core orchestrator logic
│   ├── models/       # Pydantic models
│   ├── services/     # Service implementations
│   ├── scripts/      # Utility scripts
│   └── config/       # Configuration files
├── config/
│   └── models/       # Model configurations
├── logs/            # Application logs
└── tests/           # Test files
```

### Logging

The application uses a structured logging system that writes logs to both the console and files:

- Console output: All logs are displayed in the console with timestamps and log levels
- File logs: Logs are written to the `logs` directory with the following structure:
  - `app.log`: Main application log file
  - `{module_name}.log`: Individual module log files (e.g., `model_registry.log`)

Log files are automatically rotated and managed. The `logs` directory is git-ignored to prevent committing log files to the repository.

### Key Components

1. **Model Registry**: Manages model configurations and provides access to model metadata
2. **Orchestrator**: Handles request routing and service coordination
3. **Proxy Service**: Manages communication with individual model services
4. **Circuit Breaker**: Implements failure detection and recovery
5. **Health Monitor**: Tracks service health and availability

### Development Workflow

1. Start dummy model servers:

   ```bash
   python app/scripts/run_dummy_servers.py
   ```

2. Start the orchestrator:

   ```bash
   python app/main.py
   ```

3. Test model endpoints:

   ```bash
   curl -X POST http://localhost:8000/orchestrator/models/dummy-model-1 \
     -H "Content-Type: application/json" \
     -d '{"input": "test"}'
   ```

4. Monitor health:
   ```bash
   curl http://localhost:8000/health/details
   ```

## Troubleshooting

### Common Issues

1. **Port Conflicts**:

   - If you see "Address already in use" errors, kill existing processes:

   ```bash
   pkill -9 -f python
   ```

2. **Model Not Found**:

   - Ensure model configurations exist in `config/models/`
   - Check model IDs match between config and requests

3. **Connection Errors**:
   - Verify model servers are running
   - Check endpoint URLs in model configurations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
