# ML Model Orchestrator Deployment

This directory contains the deployment configuration for the ML Model Orchestrator and its associated mock model services.

## Services

1. **Orchestrator** - Routes requests to appropriate models
   - Port: 8000
   - Health check: `GET /health`

2. **Mock Model 1** - Example model service 1
   - Port: 8001
   - Health check: `GET /health`

3. **Mock Model 2** - Example model service 2
   - Port: 8002
   - Health check: `GET /health`

## Prerequisites

- Docker
- Docker Compose

## Getting Started

### 1. Start all services

```bash
docker-compose up --build -d
```

### 2. Verify services are running

```bash
docker-compose ps
```

You should see all three services with a status of "running".

## API Endpoints

### Check orchestrator health

```bash
curl http://localhost:8000/health
```

### List available models

```bash
curl http://localhost:8000/models
```

### Check model health

```bash
# Check health of mock-model-1
curl http://localhost:8000/models/mock-model-1/health

# Check health of mock-model-2
curl http://localhost:8000/models/mock-model-2/health
```

### Make predictions

#### Using mock-model-1

```bash
curl -X POST http://localhost:8000/models/mock-model-1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, model 1!"}'
```

#### Using mock-model-2

```bash
curl -X POST http://localhost:8000/models/mock-model-2/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, model 2!"}'
```

## Scaling Services

You can scale the mock model instances using:

```bash
docker-compose up -d --scale mock-model-1=2 --scale mock-model-2=2
```

## Viewing Logs

### All services

```bash
docker-compose logs -f
```

### Specific service

```bash
docker-compose logs -f mock-model-1
docker-compose logs -f mock-model-2
docker-compose logs -f orchestrator
```

## Stopping Services

To stop all services:

```bash
docker-compose down
```

To stop and remove all containers, networks, and volumes:

```bash
docker-compose down -v
```

## Development

### Directory Structure

```
deploy/
├── docker-compose.yml    # Docker Compose configuration
├── mock-model-1/         # Mock Model 1 service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py
├── mock-model-2/         # Mock Model 2 service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py
└── orchestrator/         # Orchestrator service
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        └── main.py
```

### Adding a New Model

1. Create a new directory for your model service
2. Add a `Dockerfile`, `requirements.txt`, and your application code
3. Update the `docker-compose.yml` to include your new service
4. Update the `MODEL_REGISTRY` in `orchestrator/app/main.py` to include your new model

## Troubleshooting

- If you get port conflicts, check if the ports (8000, 8001, 8002) are already in use
- Check the logs for any errors: `docker-compose logs`
- Ensure all services are running: `docker-compose ps`
- If you make changes to the code, rebuild the containers: `docker-compose up --build -d`
