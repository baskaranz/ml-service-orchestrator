# ML Orchestrator - Response Caching Implementation

I need you to implement a response caching system for the ML Orchestrator.

## Current Architecture Context
The ML Orchestrator has these relevant components:
- `app/services/proxy.py`: Handles proxying requests to model endpoints
- `app/services/model_registry.py`: Manages model configurations
- `app/core/models.py`: Contains Pydantic models for configuration
- FastAPI dependency injection for services

## Implementation Requirements
Based on this architecture, implement a caching system that:
1. Creates a new CacheService in app/services/cache.py
2. Adds cache configuration to ModelConfig in app/core/models.py
3. Integrates caching in the ProxyService in app/services/proxy.py
4. Adds cache metrics to health reporting
5. Supports request-level cache bypass

## Cache Functionality
The cache should:
- Use model ID and request content hash as cache keys
- Support TTL-based expiration configurable per model
- Include hit/miss metrics for monitoring
- Support cache bypass via request header
- Follow our existing async patterns

## Technical Guidelines
- Follow the dependency injection pattern used in other services
- Use proper type hints and comprehensive docstrings
- Use async/await consistently for all operations
- Integrate with existing error handling patterns
- Handle edge cases like cache invalidation on model updates

## Implementation Strategy

### 1. Define Cache Configuration Model
First, define the cache configuration in `app/core/models.py`:

```python
class CacheConfig(BaseModel):
    """Configuration for response caching."""
    
    enabled: bool = Field(default=False, description="Whether caching is enabled")
    ttl: int = Field(default=300, description="Time-to-live in seconds")
    max_size: int = Field(default=100, description="Maximum number of cached items")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "forbid"
```

Then add it to the `ModelConfig` class:

```python
class ModelConfig(BaseModel):
    # Existing fields...
    
    cache: Optional[CacheConfig] = Field(
        default=None,
        description="Cache configuration for model responses"
    )
```

### 2. Create the Cache Service
Implement a new service in `app/services/cache.py`:

```python
import asyncio
import hashlib
import json
from typing import Any, Dict, Optional, TypeVar, Generic, Callable

from fastapi import Depends
from pydantic import BaseModel

from app.core.models import ModelConfig
from app.utils.logging import get_logger

T = TypeVar("T")
logger = get_logger(__name__)

class CacheMetrics(BaseModel):
    """Metrics for cache operations."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        """Convert metrics to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions
        }

class CacheItem(Generic[T]):
    """A cached item with expiration."""
    
    def __init__(self, value: T, ttl: int):
        """Initialize a cache item.
        
        Args:
            value: The cached value
            ttl: Time-to-live in seconds
        """
        self.value = value
        self.expiration = asyncio.get_event_loop().time() + ttl
    
    def is_expired(self) -> bool:
        """Check if the item is expired."""
        return asyncio.get_event_loop().time() > self.expiration

class CacheService:
    """Service for caching model responses."""
    
    def __init__(self):
        """Initialize the cache service."""
        self._caches: Dict[str, Dict[str, CacheItem]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self.metrics: Dict[str, CacheMetrics] = {}
    
    def _get_model_cache(self, model_id: str) -> Dict[str, CacheItem]:
        """Get the cache for a specific model."""
        if model_id not in self._caches:
            self._caches[model_id] = {}
            self._locks[model_id] = asyncio.Lock()
            self.metrics[model_id] = CacheMetrics()
        return self._caches[model_id]
    
    def _get_cache_key(self, request_data: Any) -> str:
        """Generate a cache key from request data."""
        # Convert request data to a canonical string representation
        if isinstance(request_data, (dict, list)):
            serialized = json.dumps(request_data, sort_keys=True)
        else:
            serialized = str(request_data)
        
        # Generate a hash for the key
        return hashlib.md5(serialized.encode()).hexdigest()
    
    async def get(self, model_id: str, request_data: Any) -> Optional[Any]:
        """Get a cached response if available.
        
        Args:
            model_id: The model identifier
            request_data: The request data used for generating the cache key
            
        Returns:
            The cached response or None if not found
        """
        cache = self._get_model_cache(model_id)
        key = self._get_cache_key(request_data)
        
        # Check if the key exists and is not expired
        if key in cache:
            item = cache[key]
            if not item.is_expired():
                self.metrics[model_id].hits += 1
                logger.debug(f"Cache hit for model {model_id}")
                return item.value
            
            # Remove expired item
            async with self._locks[model_id]:
                if key in cache and cache[key].is_expired():
                    del cache[key]
        
        self.metrics[model_id].misses += 1
        logger.debug(f"Cache miss for model {model_id}")
        return None
    
    async def set(self, model_id: str, request_data: Any, response: Any, config: ModelConfig) -> None:
        """Cache a response.
        
        Args:
            model_id: The model identifier
            request_data: The request data used for generating the cache key
            response: The response to cache
            config: The model configuration with cache settings
        """
        if not config.cache or not config.cache.enabled:
            return
        
        ttl = config.cache.ttl
        max_size = config.cache.max_size
        
        cache = self._get_model_cache(model_id)
        key = self._get_cache_key(request_data)
        
        async with self._locks[model_id]:
            # Check cache size and evict if necessary
            if len(cache) >= max_size and key not in cache:
                # Simple eviction strategy: remove oldest item
                # In a real implementation, use LRU or similar strategy
                if cache:
                    oldest_key = next(iter(cache))
                    del cache[oldest_key]
                    self.metrics[model_id].evictions += 1
                    logger.debug(f"Cache eviction for model {model_id}")
            
            # Add the new item
            cache[key] = CacheItem(response, ttl)
            logger.debug(f"Cached response for model {model_id}, TTL: {ttl}s")
    
    async def invalidate(self, model_id: str) -> None:
        """Invalidate all cached responses for a model.
        
        Args:
            model_id: The model identifier
        """
        if model_id in self._caches:
            async with self._locks[model_id]:
                self._caches[model_id] = {}
                logger.info(f"Invalidated cache for model {model_id}")
    
    async def invalidate_all(self) -> None:
        """Invalidate all caches."""
        for model_id in list(self._caches.keys()):
            await self.invalidate(model_id)
    
    def get_metrics(self) -> Dict[str, Dict[str, int]]:
        """Get cache metrics for all models."""
        return {model_id: metrics.to_dict() for model_id, metrics in self.metrics.items()}

def get_cache_service() -> CacheService:
    """Dependency provider for the cache service."""
    return CacheService()
```

### 3. Integrate with ProxyService
Update `app/services/proxy.py` to use the cache:

```python
from fastapi import Request, Depends

from app.services.cache import CacheService, get_cache_service
# Other imports...

class ProxyService:
    """Service for proxying requests to model endpoints."""
    
    def __init__(
        self,
        model_registry: ModelRegistryService,
        orchestrator: Orchestrator,
        cache_service: CacheService = Depends(get_cache_service)
    ):
        """Initialize the proxy service.
        
        Args:
            model_registry: The model registry service
            orchestrator: The orchestrator service
            cache_service: The cache service
        """
        self.model_registry = model_registry
        self.orchestrator = orchestrator
        self.cache_service = cache_service
    
    async def proxy_to_model(self, model_id: str, request: Request) -> dict:
        """Proxy a request to a model endpoint.
        
        Args:
            model_id: The model ID to proxy to
            request: The FastAPI request object
            
        Returns:
            The model response
            
        Raises:
            ModelRequestError: If the request fails
        """
        try:
            # Get model configuration
            model_config = self.model_registry.get_model_config(model_id)
            
            # Extract request data for caching
            request_data = await self._extract_request_data(request)
            
            # Check if bypass header is present
            headers = dict(request.headers)
            bypass_cache = headers.get("X-Bypass-Cache", "").lower() == "true"
            
            # Try to get from cache if caching is enabled and not bypassed
            if model_config.cache and model_config.cache.enabled and not bypass_cache:
                cached_response = await self.cache_service.get(model_id, request_data)
                if cached_response is not None:
                    return cached_response
            
            # Forward request to the model via orchestrator
            response = await self.orchestrator.proxy_request(
                model_id,
                request_data,
                headers
            )
            
            # Cache the response if applicable
            if model_config.cache and model_config.cache.enabled and not bypass_cache:
                await self.cache_service.set(model_id, request_data, response, model_config)
            
            return response
        except CircuitBreakerError as e:
            raise ModelRequestError(
                message=f"Request failed: circuit breaker open for model {model_id}",
                status_code=503
            ) from e
        # Other exception handling...
    
    async def _extract_request_data(self, request: Request) -> Any:
        """Extract data from the request for caching."""
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            return await request.json()
        elif "application/x-www-form-urlencoded" in content_type:
            return await request.form()
        else:
            return await request.body()
```

### 4. Integrate with ModelRegistry
Update `app/services/model_registry.py` to handle cache invalidation:

```python
class ModelRegistryService:
    # Existing code...
    
    def __init__(
        self,
        config_manager: ModelConfigManager,
        cache_service: Optional[CacheService] = None
    ):
        """Initialize the model registry service.
        
        Args:
            config_manager: The model configuration manager
            cache_service: Optional cache service for invalidation
        """
        self.config_manager = config_manager
        self._models = {}
        self._cache_service = cache_service
    
    async def reload_configs(self) -> None:
        """Reload model configurations."""
        # Existing reload code...
        
        # Invalidate caches for updated models
        if self._cache_service:
            for model_id in self._models:
                await self._cache_service.invalidate(model_id)
```

### 5. Register in Main Application
Update `app/main.py` to register the cache service:

```python
from app.services.cache import get_cache_service

def create_app() -> FastAPI:
    # Existing code...
    
    # Add dependencies
    app.dependency_overrides[get_cache_service] = lambda: CacheService()
    
    # Existing code...
```

### 6. Update Health Endpoints
Update `app/api/routes/health.py` to include cache metrics:

```python
from app.services.cache import CacheService, get_cache_service

router = APIRouter()

@router.get("/health/details", response_model=HealthDetails)
async def health_details(
    cache_service: CacheService = Depends(get_cache_service),
    # Other dependencies...
):
    """Get detailed health status of the service."""
    # Existing code...
    
    # Add cache metrics
    components["cache"] = {
        "status": "ok",
        "metrics": cache_service.get_metrics()
    }
    
    # Existing code...
```

### 7. Test Implementation

Create `tests/test_services/test_cache.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.models import ModelConfig, CacheConfig
from app.services.cache import CacheService, get_cache_service

@pytest.fixture
def cache_service():
    """Create a cache service for testing."""
    return CacheService()

@pytest.fixture
def cache_config():
    """Create a cache configuration for testing."""
    return ModelConfig(
        id="test_model",
        name="Test Model",
        endpoint_url="http://example.com",
        cache=CacheConfig(
            enabled=True,
            ttl=10,
            max_size=5
        )
    )

@pytest.mark.asyncio
async def test_cache_hit(cache_service, cache_config):
    """Test cache hit functionality."""
    # Set up cache
    request_data = {"prompt": "test"}
    response_data = {"result": "cached response"}
    
    await cache_service.set("test_model", request_data, response_data, cache_config)
    
    # Test cache hit
    result = await cache_service.get("test_model", request_data)
    assert result == response_data
    assert cache_service.metrics["test_model"].hits == 1
    assert cache_service.metrics["test_model"].misses == 0

@pytest.mark.asyncio
async def test_cache_miss(cache_service):
    """Test cache miss functionality."""
    request_data = {"prompt": "test"}
    
    # Test cache miss
    result = await cache_service.get("test_model", request_data)
    assert result is None
    assert "test_model" in cache_service.metrics
    assert cache_service.metrics["test_model"].hits == 0
    assert cache_service.metrics["test_model"].misses == 1

@pytest.mark.asyncio
async def test_cache_invalidation(cache_service, cache_config):
    """Test cache invalidation."""
    # Set up cache
    request_data = {"prompt": "test"}
    response_data = {"result": "cached response"}
    
    await cache_service.set("test_model", request_data, response_data, cache_config)
    
    # Invalidate cache
    await cache_service.invalidate("test_model")
    
    # Test cache miss after invalidation
    result = await cache_service.get("test_model", request_data)
    assert result is None

@pytest.mark.asyncio
async def test_cache_eviction(cache_service, cache_config):
    """Test cache eviction when max size is reached."""
    # Fill cache to max size
    for i in range(5):
        request_data = {"prompt": f"test{i}"}
        response_data = {"result": f"response{i}"}
        await cache_service.set("test_model", request_data, response_data, cache_config)
    
    # Add one more item to trigger eviction
    new_request = {"prompt": "new_test"}
    new_response = {"result": "new_response"}
    await cache_service.set("test_model", new_request, new_response, cache_config)
    
    # Check metrics
    assert cache_service.metrics["test_model"].evictions == 1

@pytest.mark.asyncio
async def test_proxy_service_caching():
    """Test integration with proxy service."""
    # Mock dependencies
    mock_registry = MagicMock()
    mock_orchestrator = AsyncMock()
    mock_cache = AsyncMock()
    
    # Configure mock model config
    mock_config = ModelConfig(
        id="test_model",
        name="Test Model",
        endpoint_url="http://example.com",
        cache=CacheConfig(
            enabled=True,
            ttl=10,
            max_size=5
        )
    )
    mock_registry.get_model_config.return_value = mock_config
    
    # Configure mock request
    mock_request = AsyncMock()
    mock_request.headers = {"content-type": "application/json"}
    mock_request.json.return_value = {"prompt": "test"}
    
    # Configure cache miss then hit
    mock_cache.get.side_effect = [None, {"result": "cached"}]
    
    # Configure orchestrator response
    mock_orchestrator.proxy_request.return_value = {"result": "response"}
    
    # Create proxy service with mocked dependencies
    proxy_service = ProxyService(
        model_registry=mock_registry,
        orchestrator=mock_orchestrator,
        cache_service=mock_cache
    )
    
    # First request should miss cache and call orchestrator
    response1 = await proxy_service.proxy_to_model("test_model", mock_request)
    assert response1 == {"result": "response"}
    mock_cache.get.assert_called_once()
    mock_orchestrator.proxy_request.assert_called_once()
    mock_cache.set.assert_called_once()
    
    # Reset mocks for second request
    mock_cache.get.reset_mock()
    mock_orchestrator.proxy_request.reset_mock()
    mock_cache.set.reset_mock()
    
    # Second request should hit cache
    response2 = await proxy_service.proxy_to_model("test_model", mock_request)
    assert response2 == {"result": "cached"}
    mock_cache.get.assert_called_once()
    mock_orchestrator.proxy_request.assert_not_called()
    mock_cache.set.assert_not_called()

@pytest.mark.asyncio
async def test_cache_bypass(cache_service, cache_config):
    """Test cache bypass via header."""
    # Mock dependencies
    mock_registry = MagicMock()
    mock_orchestrator = AsyncMock()
    
    # Configure mock model config
    mock_registry.get_model_config.return_value = cache_config
    
    # Configure mock request with bypass header
    mock_request = AsyncMock()
    mock_request.headers = {
        "content-type": "application/json",
        "X-Bypass-Cache": "true"
    }
    mock_request.json.return_value = {"prompt": "test"}
    
    # Configure orchestrator response
    mock_orchestrator.proxy_request.return_value = {"result": "response"}
    
    # Create proxy service with real cache service
    proxy_service = ProxyService(
        model_registry=mock_registry,
        orchestrator=mock_orchestrator,
        cache_service=cache_service
    )
    
    # Request should bypass cache
    response = await proxy_service.proxy_to_model("test_model", mock_request)
    assert response == {"result": "response"}
    
    # Cache should be empty despite the request
    result = await cache_service.get("test_model", {"prompt": "test"})
    assert result is None
```

## Expected Deliverables
With this implementation, you will have:

1. A fully featured caching system integrated with the ML Orchestrator
2. Configuration options in the model YAML files
3. Metrics for monitoring cache performance
4. Comprehensive tests for the cache functionality
5. Integration with health monitoring

This implementation follows the ML Orchestrator's established patterns:
- Dependency injection for service integration
- Async/await for all operations
- Comprehensive error handling
- Type hints and docstrings
- Thorough testing
- Configuration-driven behavior