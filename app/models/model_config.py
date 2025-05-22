from typing import Any, Dict, Optional

from pydantic import BaseModel


class ModelConfig(BaseModel):
    """Configuration for a model endpoint."""

    id: str
    name: str
    endpoint_url: str
    active: bool = True
    description: Optional[str] = None
    version: Optional[str] = None
    error_handling: Optional[Dict[str, Any]] = None
    circuit_breaker: Optional[Dict[str, Any]] = None
