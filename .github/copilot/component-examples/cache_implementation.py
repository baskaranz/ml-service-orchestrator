"""
ML Orchestrator Cache Implementation Pattern

This example demonstrates the caching pattern used in the ML Orchestrator
for optimizing repeated requests and reducing load on downstream services.
"""
import asyncio
import functools
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, cast

import orjson
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")

class CacheEntry(BaseModel):
    """Model representing a cache entry with expiration time."""
    value: Any
    expires_at: datetime = Field(..., description="Expiration timestamp")
    
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.utcnow() > self.expires_at


class AsyncLRUCache:
    """
    Async-friendly LRU Cache implementation for ML Orchestrator.
    
    Features:
    - Configurable TTL (time-to-live) for entries
    - Async-compatible for use with FastAPI and async functions
    - LRU (least-recently-used) eviction policy
    - Thread-safe implementation
    - Metrics capture for cache hits/misses
    """
    
    def __init__(
        self, 
        max_size: int = 100, 
        default_ttl_seconds: int = 300,
        namespace: str = "default"
    ):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of items to store in the cache
            default_ttl_seconds: Default time-to-live for cache entries in seconds
            namespace: Namespace for the cache (used for metrics and logging)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl_seconds
        self._namespace = namespace
        self._access_order: list = []
        self._lock = asyncio.Lock()
        
        # Metrics
        self.hits = 0
        self.misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get an item from the cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            The cached value or None if not found or expired
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self.misses += 1
                logger.debug(f"Cache miss for key: {key} in namespace: {self._namespace}")
                return None
                
            if entry.is_expired:
                logger.debug(f"Cache entry expired for key: {key} in namespace: {self._namespace}")
                del self._cache[key]
                self._access_order.remove(key)
                self.misses += 1
                return None
                
            # Update access order (move to end = most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            
            self.hits += 1
            logger.debug(f"Cache hit for key: {key} in namespace: {self._namespace}")
            return entry.value
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        async with self._lock:
            # If we're at capacity and this is a new key, remove the least recently used item
            if len(self._cache) >= self._max_size and key not in self._cache:
                if self._access_order:
                    lru_key = self._access_order.pop(0)
                    del self._cache[lru_key]
                    logger.debug(f"Evicted LRU key: {lru_key} from namespace: {self._namespace}")
            
            # Add or update the entry
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            logger.debug(f"Set cache for key: {key} in namespace: {self._namespace}, expires: {expires_at}")
    
    async def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if the key was found and invalidated, False otherwise
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_order.remove(key)
                logger.debug(f"Invalidated cache key: {key} in namespace: {self._namespace}")
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all entries from the cache."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.debug(f"Cleared all cache entries in namespace: {self._namespace}")


def generate_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    Generate a deterministic cache key from function arguments.
    
    Args:
        prefix: Prefix for the cache key (usually function name)
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        A unique cache key string
    """
    # Convert all arguments to a serializable format
    key_dict = {
        "args": args,
        "kwargs": kwargs
    }
    
    # Use orjson for fast, deterministic serialization
    serialized = orjson.dumps(key_dict, option=orjson.OPT_SORT_KEYS)
    
    # Create a hash of the serialized data
    key_hash = hashlib.sha256(serialized).hexdigest()
    
    return f"{prefix}:{key_hash}"


def async_cached(
    cache_instance: AsyncLRUCache,
    ttl_seconds: Optional[int] = None,
    key_prefix: Optional[str] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for caching async function results.
    
    Args:
        cache_instance: The cache instance to use
        ttl_seconds: Optional TTL override for this function
        key_prefix: Optional key prefix (defaults to function name)
        
    Returns:
        Decorated function with caching behavior
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        prefix = key_prefix or func.__name__
        
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key from function name and arguments
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get result from cache first
            cached_result = await cache_instance.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # If not in cache, call the original function
            result = await func(*args, **kwargs)
            
            # Store result in cache
            await cache_instance.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    
    return decorator


# Example Usage

# 1. Create a cache instance for a specific domain
model_cache = AsyncLRUCache(
    max_size=50,
    default_ttl_seconds=600,  # 10 minutes
    namespace="model_registry"
)

# 2. Apply the cached decorator to a function
@async_cached(model_cache, ttl_seconds=300)
async def fetch_model_metadata(model_id: str) -> Dict[str, Any]:
    """
    Fetch model metadata from the model registry.
    This function is expensive, so we cache the results.
    """
    # This would normally be an API call to a model registry service
    await asyncio.sleep(1)  # Simulate slow API call
    
    # Return mock data for demonstration
    return {
        "model_id": model_id,
        "version": "1.0.0",
        "created_at": datetime.utcnow().isoformat(),
        "metrics": {
            "accuracy": 0.95,
            "f1_score": 0.94
        }
    }

# 3. Example of cache invalidation when model is updated
async def update_model_metadata(model_id: str, updated_data: Dict[str, Any]) -> None:
    """Update model metadata and invalidate the cache."""
    # Update model in external service
    # ...
    
    # Invalidate the cache for this model
    cache_key = generate_cache_key("fetch_model_metadata", model_id)
    await model_cache.invalidate(cache_key)
"""