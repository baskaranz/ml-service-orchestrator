"""
Dependencies package for the API.

This package contains dependency injection functions for the API.
"""

# Import dependencies to make them available when importing from app.api.dependencies
from .auth import get_api_key
from .orchestrator import get_orchestrator

__all__ = ["get_orchestrator", "get_api_key"]
