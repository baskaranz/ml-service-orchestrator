# Cloud Development Guide

This guide explains how to set up and use the development environment for the ML Service Orchestrator in cloud environments like AWS EC2 or ECS.

## Prerequisites

- Docker and Docker Compose installed
- Access to a cloud environment with Docker
- Sufficient resources (at least 2GB RAM, 2 vCPUs recommended)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd lasso
   ```

2. **Make the setup script executable**
   ```bash
   chmod +x scripts/setup-dev-env.sh
   ```

3. **Run the setup script**
   ```bash
   ./scripts/setup-dev-env.sh
   ```

4. **Start the development environment**
   ```bash
   docker-compose -f docker-compose.cloud-dev.yml up --build
   ```

5. **Access the application**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Redoc: http://localhost:8000/redoc

## Development Features

- **Hot Reloading**: Code changes are automatically detected and the server restarts
- **Debugging**: Debug logs are enabled by default
- **Database**: PostgreSQL with persistent storage
- **Caching**: Redis for caching
- **Documentation**: Interactive API documentation

## Environment Variables

Key environment variables for development:

- `ENVIRONMENT=dev`: Sets the environment to development
- `LOG_LEVEL=DEBUG`: Enables debug logging
- `RELOAD=true`: Enables auto-reload on code changes
- `DATABASE_URL`: Connection string for PostgreSQL
- `REDIS_URL`: Connection string for Redis

## Running Tests

To run tests in the development environment:

```bash
docker-compose -f docker-compose.cloud-dev.yml exec orchestrator pytest
```

## Debugging

1. **View Logs**
   ```bash
   docker-compose -f docker-compose.cloud-dev.yml logs -f
   ```

2. **Access the Container**
   ```bash
   docker-compose -f docker-compose.cloud-dev.yml exec orchestrator bash
   ```

## Stopping the Environment

To stop the development environment:

```bash
docker-compose -f docker-compose.cloud-dev.yml down
```

To stop and remove all data (including database):

```bash
docker-compose -f docker-compose.cloud-dev.yml down -v
```

## Best Practices

1. **Environment Variables**
   - Never commit sensitive information to version control
   - Use `.env.dev` for local development overrides

2. **Code Changes**
   - The application will automatically reload when you make changes to Python files
   - For changes to dependencies, rebuild the containers

3. **Database Migrations**
   - Any database schema changes should be handled via migrations
   - Run migrations after pulling changes that include them

## Troubleshooting

### Port Already in Use
If you get a port conflict, either stop the conflicting service or change the port in `.env.dev`.

### Docker Permissions
If you encounter permission issues with Docker, ensure your user is in the `docker` group:

```bash
sudo usermod -aG docker $USER
```

### Resource Issues
If containers are failing to start, check resource usage:

```bash
docker stats
```

## Next Steps

- [ ] Set up your IDE for remote debugging
- [ ] Configure additional services as needed
- [ ] Review the API documentation at `/docs`
- [ ] Add your model configurations to `config/dev/models/`
