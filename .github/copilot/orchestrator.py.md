# Create instructions for orchestrator.py
Create a core orchestrator class that:
1. Routes requests to appropriate model endpoints based on path
2. Handles request and response transformations
3. Implements fallback logic for failures
4. Supports request validation against model-specific schemas
5. Handles timeouts and circuit breaking
6. Implements load balancing if multiple endpoints are available for a model
7. Supports response caching for idempotent operations
8. Collects metrics on request latency and success rate