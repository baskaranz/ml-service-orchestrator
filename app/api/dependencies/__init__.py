"""
Dependencies package for the API.

This package contains dependency injection functions for the API.
"""

# Import dependencies to make them available when importing from app.api.dependencies
from .orchestrator import get_orchestrator
from .auth import get_api_key

__all__ = ["get_orchestrator", "get_api_key"]
