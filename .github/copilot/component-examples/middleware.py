"""
ML Orchestrator Middleware Patterns

This example demonstrates the middleware patterns used in the ML Orchestrator
for request processing, logging, telemetry, and error handling.
"""
import asyncio
import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import Message

# --- Context Variables for Request Tracking ---

# Context variables allow us to track request-specific data throughout the request lifecycle
request_id_ctx = ContextVar("request_id", default=None)
trace_id_ctx = ContextVar("trace_id", default=None)
start_time_ctx = ContextVar("start_time", default=None)
request_path_ctx = ContextVar("request_path", default=None)

logger = logging.getLogger(__name__)


# --- Request ID Middleware ---

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures each request has a unique ID.
    
    This ID is used for tracking requests through the system and 
    correlating logs and telemetry.
    """
    
    def __init__(
        self, 
        app: FastAPI, 
        header_name: str = "X-Request-ID",
        include_in_response: bool = True
    ):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application
            header_name: Name of the header to look for/set
            include_in_response: Whether to include the ID in the response headers
        """
        super().__init__(app)
        self.header_name = header_name
        self.include_in_response = include_in_response
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and set request ID."""
        # Check if there's already a request ID in the headers
        request_id = request.headers.get(self.header_name)
        
        # If not, generate a new one
        if not request_id:
            request_id = str(uuid.uuid4())
            
        # Store in context and request state
        request_id_ctx.set(request_id)
        request.state.request_id = request_id
        
        # Process the request
        response = await call_next(request)
        
        # Include the request ID in the response if configured
        if self.include_in_response:
            response.headers[self.header_name] = request_id
            
        return response


# --- Distributed Tracing Middleware ---

class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for distributed tracing.
    
    This middleware extracts tracing headers from incoming requests and
    propagates them through the system for distributed tracing.
    """
    
    def __init__(
        self, 
        app: FastAPI,
        trace_header: str = "X-Trace-ID"
    ):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application
            trace_header: Name of the trace ID header
        """
        super().__init__(app)
        self.trace_header = trace_header
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Extract and propagate tracing information."""
        # Extract tracing information from headers
        trace_id = request.headers.get(self.trace_header)
        
        # Generate a new trace ID if none exists
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        # Store in context and request state
        trace_id_ctx.set(trace_id)
        request.state.trace_id = trace_id
        
        # Process the request
        response = await call_next(request)
        
        # Include trace ID in response
        response.headers[self.trace_header] = trace_id
        
        return response


# --- Logging Middleware ---

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request logging.
    
    This middleware logs the beginning and end of each request with
    structured data including timing, status code, and request details.
    """
    
    def __init__(
        self, 
        app: FastAPI,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_length: int = 1000,
        exclude_paths: List[str] = None
    ):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application
            log_request_body: Whether to log request bodies
            log_response_body: Whether to log response bodies
            max_body_length: Maximum length to log for bodies
            exclude_paths: Paths to exclude from logging (e.g., health checks)
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_length = max_body_length
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Log request details before and after processing."""
        # Check if this path should be excluded
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Store the request start time and path
        start_time = time.time()
        start_time_ctx.set(start_time)
        request_path_ctx.set(request.url.path)
        
        # Get request ID and trace ID from context
        request_id = request_id_ctx.get()
        trace_id = trace_id_ctx.get()
        
        # Log request start
        request_log = {
            "request_id": request_id,
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Optionally log request body
        if self.log_request_body:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode("utf-8")
                    if len(body_str) > self.max_body_length:
                        body_str = f"{body_str[:self.max_body_length]}... [truncated]"
                    request_log["body"] = body_str
            except Exception as e:
                request_log["body_error"] = str(e)
                
            # We need to reset the request body for downstream consumers
            await request.body()
        
        logger.info(f"Request received: {request.method} {request.url.path}", extra=request_log)
        
        # Process the request and capture response
        try:
            response = await call_next(request)
            status_code = response.status_code
            response_log = "success"
        except Exception as e:
            logger.exception(f"Error processing request: {str(e)}", extra=request_log)
            raise
        
        # Calculate request duration
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        # Log response details
        response_log = {
            "request_id": request_id,
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Determine log level based on status code
        if status_code >= 500:
            log_method = logger.error
        elif status_code >= 400:
            log_method = logger.warning
        else:
            log_method = logger.info
        
        # Optionally log response body for non-success status codes
        if self.log_response_body and (self.log_response_body is True or status_code >= 400):
            try:
                # This is a bit tricky since we can't easily get the response body
                # We would need to use a custom StarletteResponse with a custom class that
                # allows us to capture the body. This is simplified for the example.
                response_log["response_headers"] = dict(response.headers)
            except Exception as e:
                response_log["response_error"] = str(e)
        
        log_method(
            f"Request completed: {request.method} {request.url.path} {status_code} {duration_ms}ms",
            extra=response_log
        )
        
        return response


# --- Telemetry Middleware ---

class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    Middleware for capturing request telemetry.
    
    This middleware collects metrics about requests including counts,
    latencies, and error rates.
    """
    
    def __init__(
        self, 
        app: FastAPI,
        metrics_registry = None,  # Would be a prometheus or statsd client in real code
        include_paths: List[str] = None,
        exclude_paths: List[str] = None
    ):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application
            metrics_registry: Registry for metrics collection
            include_paths: Paths to include in telemetry (None = all)
            exclude_paths: Paths to exclude from telemetry
        """
        super().__init__(app)
        self.metrics_registry = metrics_registry
        self.include_paths = include_paths
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]

        # In a real implementation, we would initialize metrics here:
        # self.request_counter = self.metrics_registry.counter("http_requests_total", "Total HTTP requests")
        # self.request_latency = self.metrics_registry.histogram("http_request_duration_ms", "HTTP request latency (ms)")
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Collect telemetry for the request."""
        # Check path filters
        path = request.url.path
        if self.exclude_paths and any(path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)
        if self.include_paths and not any(path.startswith(p) for p in self.include_paths):
            return await call_next(request)
        
        # Get start time
        start_time = time.time()
        
        # Process the request
        try:
            response = await call_next(request)
            status_code = response.status_code
            exception = None
        except Exception as e:
            exception = e
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # In a real implementation, we would record metrics:
            # self.request_counter.inc(labels={
            #     "method": request.method, 
            #     "path": request.url.path,
            #     "status": status_code // 100 * 100  # e.g., 200, 400, 500
            # })
            # self.request_latency.observe(duration_ms, labels={
            #     "method": request.method, 
            #     "path": request.url.path
            # })
            
            # Just log metrics for this example
            logger.debug(
                f"Telemetry: {request.method} {path} {status_code} {duration_ms:.2f}ms"
            )
        
        return response


# --- Circuit Breaker Integration Middleware ---

class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that integrates with circuit breakers.
    
    This middleware checks if a circuit breaker is open for a given endpoint
    and returns an error response if requests should be blocked.
    """
    
    def __init__(
        self, 
        app: FastAPI,
        circuit_breaker_config: Dict[str, Dict[str, Any]] = None
    ):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application
            circuit_breaker_config: Configuration mapping paths to circuit breakers
        """
        super().__init__(app)
        self.config = circuit_breaker_config or {}
        
        # In a real implementation, we would initialize circuit breakers here
        # from the config, e.g.:
        # self.circuit_breakers = {
        #     path: CircuitBreaker(**config)
        #     for path, config in self.config.items()
        # }
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Check circuit breaker state before processing request."""
        path = request.url.path
        
        # Find matching circuit breaker for this path
        cb_key = next((k for k in self.config if path.startswith(k)), None)
        
        if cb_key:
            # In a real implementation, we would check the circuit breaker:
            # circuit_breaker = self.circuit_breakers[cb_key]
            # if circuit_breaker.is_open():
            #     return JSONResponse(
            #         status_code=503,
            #         content={
            #             "error": "Service temporarily unavailable",
            #             "detail": f"Circuit breaker open for {cb_key}",
            #             "retry_after": circuit_breaker.time_until_retry
            #         }
            #     )
            pass
        
        # Circuit breaker is closed or not applicable, proceed with request
        return await call_next(request)


# --- Response Transformation Middleware ---

class ResponseTransformMiddleware(BaseHTTPMiddleware):
    """
    Middleware for transforming responses.
    
    This middleware applies transformations to responses based on rules,
    such as standardizing the format or adding common fields.
    """
    
    def __init__(
        self, 
        app: FastAPI,
        include_request_id: bool = True,
        include_time: bool = True,
        include_version: bool = True,
        api_version: str = "1.0",
        apply_to_paths: List[str] = None,
        exclude_paths: List[str] = None
    ):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application
            include_request_id: Whether to include request ID in responses
            include_time: Whether to include server time
            include_version: Whether to include API version
            api_version: API version string
            apply_to_paths: Paths to apply transformations to (None = all)
            exclude_paths: Paths to exclude from transformations
        """
        super().__init__(app)
        self.include_request_id = include_request_id
        self.include_time = include_time
        self.include_version = include_version
        self.api_version = api_version
        self.apply_to_paths = apply_to_paths
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Apply transformations to the response."""
        # Check path filters
        path = request.url.path
        
        # Skip transformation for excluded paths
        if self.exclude_paths and any(path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)
            
        # Skip transformation if not in the included paths
        if self.apply_to_paths and not any(path.startswith(p) for p in self.apply_to_paths):
            return await call_next(request)
        
        # Process the request
        response = await call_next(request)
        
        # We only transform JSON responses
        if "application/json" not in response.headers.get("content-type", ""):
            return response
            
        # Read the response body
        response_body = [section async for section in response.body_iterator]
        response.body_iterator = AsyncIterator(response_body)
        
        # Parse the JSON
        try:
            body = json.loads(b"".join(response_body).decode())
        except json.JSONDecodeError:
            # If not valid JSON, return as is
            return response
            
        # Apply transformations
        transformed_body = self.transform_response(body, request)
        
        # Create a new response with the transformed body
        return Response(
            content=json.dumps(transformed_body),
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type="application/json"
        )
    
    def transform_response(self, body: Dict[str, Any], request: Request) -> Dict[str, Any]:
        """Apply transformations to the response body."""
        # Skip transformation if already in expected format
        if isinstance(body, dict) and "data" in body and "meta" in body:
            return body
            
        # Get metadata to include
        meta = {}
        
        if self.include_request_id:
            request_id = getattr(request.state, "request_id", None)
            if request_id:
                meta["request_id"] = request_id
                
        if self.include_time:
            meta["server_time"] = datetime.utcnow().isoformat()
            
        if self.include_version:
            meta["api_version"] = self.api_version
            
        # Transform to standard format
        return {
            "data": body,
            "meta": meta
        }


# --- Helper Classes ---

class AsyncIterator:
    """
    Helper class for creating an async iterator from a list.
    Used for reconstructing response bodies in middleware.
    """
    
    def __init__(self, sequence):
        self.sequence = sequence
        self.iterator = iter(sequence)
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        try:
            return next(self.iterator)
        except StopIteration:
            raise StopAsyncIteration


# --- Middleware Application ---

def setup_middleware(app: FastAPI) -> None:
    """
    Set up all middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Order matters - middleware is executed in reverse order of addition
    
    # Response transformation should be applied first (last in the request cycle)
    app.add_middleware(
        ResponseTransformMiddleware,
        include_request_id=True,
        include_time=True,
        include_version=True,
        api_version="1.0",
        apply_to_paths=["/api/"]
    )
    
    # Circuit breaker should be checked early
    app.add_middleware(
        CircuitBreakerMiddleware,
        circuit_breaker_config={
            "/api/models/": {"max_failures": 5, "reset_timeout": 30},
            "/api/registry/": {"max_failures": 3, "reset_timeout": 60}
        }
    )
    
    # Telemetry collection
    app.add_middleware(
        TelemetryMiddleware,
        exclude_paths=["/health", "/metrics", "/docs"]
    )
    
    # Request logging
    app.add_middleware(
        RequestLoggingMiddleware,
        log_request_body=False,
        log_response_body=False,
        exclude_paths=["/health", "/metrics"]
    )
    
    # Distributed tracing
    app.add_middleware(
        TracingMiddleware,
        trace_header="X-Trace-ID"
    )
    
    # Request ID should be added last (first in the request cycle)
    app.add_middleware(
        RequestIdMiddleware,
        header_name="X-Request-ID",
        include_in_response=True
    )


# Example usage with FastAPI

"""
from fastapi import FastAPI

app = FastAPI()

# Set up all middleware
setup_middleware(app)

# Define routes
@app.get("/api/models")
async def list_models():
    return {"models": ["model1", "model2"]}

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""