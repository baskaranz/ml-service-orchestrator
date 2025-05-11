# Create instructions for proxy.py
Create a proxy service that:
1. Forwards HTTP requests to model endpoints using httpx or aiohttp
2. Implements connection pooling for better performance
3. Configures timeouts for requests
4. Implements circuit breaker pattern for fault tolerance
5. Handles HTTP errors with proper status code mapping
6. Supports request and response transformations
7. Implements retry logic for transient failures
8. Adds proper headers like X-Forwarded-For
9. Supports response streaming