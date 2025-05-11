# Create instructions for main.py
Create a FastAPI application entry point that:
1. Initializes configuration loading from YAML files
2. Sets up middleware for request logging, correlation IDs, and error handling
3. Includes routers for health checks, the main orchestrator, and admin endpoints
4. Configures exception handlers for custom exceptions
5. Sets up startup and shutdown events for resource management
6. Initializes the model registry on startup
7. Implements graceful shutdown for any background tasks