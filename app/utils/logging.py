"""
Logging utilities for the application.
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """Get a logger with the specified name and level."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(
            logs_dir / f"{name.replace('.', '_')}.log",
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def setup_logging(level: int = logging.DEBUG, log_level: Optional[str] = None) -> None:
    """Set up logging configuration."""
    # Reset any existing configuration
    logging.getLogger().handlers = []
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    if log_level is not None and isinstance(log_level, str):
        level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                logs_dir / "app.log",
                encoding='utf-8'
            )
        ]
    )

class RequestLogContext(BaseModel):
    """Request logging context."""
    request_id: str
    method: str
    path: str
    client_ip: str
    model_id: Optional[str] = None

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""
    
    def __init__(self, app: Any):
        super().__init__(app)
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log details."""
        # Create request context
        context = RequestLogContext(
            request_id=str(request.headers.get("X-Request-ID", "")),
            method=str(request.method),
            path=str(request.url.path),
            client_ip=str(request.client.host if request.client else "")
        )
        
        # Log request start
        self.logger.info(
            f"Request started: {context.method} {context.path}",
            extra={"context": context.model_dump()}
        )
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Log request completion
            process_time = time.time() - start_time
            self.logger.info(
                f"Request completed: {context.method} {context.path} - {response.status_code} ({process_time:.2f}s)",
                extra={
                    "context": context.model_dump(),
                    "status_code": response.status_code,
                    "process_time": process_time
                }
            )
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            self.logger.error(
                f"Request failed: {context.method} {context.path} - {str(e)} ({process_time:.2f}s)",
                extra={
                    "context": context.model_dump(),
                    "error": str(e),
                    "process_time": process_time
                },
                exc_info=True
            )
            raise