# Local Development Scripts

This directory contains scripts to manage the local development environment for the ML Orchestrator.

## Available Scripts

### 1. Start a Mock Model
```bash
./scripts/start-mock-model.sh <model-name> <port>
```
Example:
```bash
# Start a model (active by default)
./scripts/start-mock-model.sh model1 8001
```

### 2. Start the Orchestrator
```bash
./scripts/start-orchestrator.sh [port]
```
Example:
```bash
# Start on default port (8000)
./scripts/start-orchestrator.sh

# Start on custom port
./scripts/start-orchestrator.sh 9000
```

### 3. Clean Up
```bash
./scripts/cleanup.sh
```
This will stop and remove all mock models and the orchestrator.

## Example Workflow

1. Start two mock models:
   ```bash
   ./scripts/start-mock-model.sh model1 8001
   ./scripts/start-mock-model.sh model2 8002
   ```

2. Start the orchestrator:
   ```bash
   ./scripts/start-orchestrator.sh 8000
   ```

3. Test the setup:
   ```bash
   # Test model1 directly
   curl http://localhost:8001/health
   
   # Test model1 through orchestrator
   curl http://localhost:8000/api/v1/models/model1/health
   
   # List all models
   curl http://localhost:8000/api/v1/models
   ```

4. Clean up when done:
   ```bash
   ./scripts/cleanup.sh
   ```

## Notes

- Mock models are accessible at `http://localhost:<port>`
- The orchestrator is accessible at `http://localhost:8000`
- API documentation is available at `http://localhost:8000/docs`
- All containers are connected to the `ml-network` Docker network
