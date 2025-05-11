# Create instructions for orchestrator_routes.py
Create a FastAPI router for the orchestrator that:
1. Dynamically routes requests based on URL path to appropriate model endpoints
2. Extracts path parameters and query parameters and forwards them properly
3. Validates request bodies against model-specific schemas
4. Handles different HTTP methods (GET, POST, etc.)
5. Forwards headers and cookies as appropriate
6. Implements proper error handling for model endpoint failures
7. Adds request ID and correlation ID to requests
8. Logs request and response details with appropriate data masking