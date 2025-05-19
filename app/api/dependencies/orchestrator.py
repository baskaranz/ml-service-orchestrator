"""
Dependencies for the orchestrator service.
"""
import asyncio
import threading
from typing import Optional, Dict, Any
from fastapi import Depends
from app.services.orchestrator import Orchestrator
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Global instance of the orchestrator and lock
_orchestrator = None
_orchestrator_lock = threading.Lock()
_initialization_lock = asyncio.Lock()

async def get_orchestrator_async() -> Orchestrator:
    """
    Get or create the orchestrator instance asynchronously.
    
    This is an async dependency that ensures the orchestrator is properly initialized.
    It creates a single instance of the orchestrator that's shared across all requests.
    
    Returns:
        Orchestrator: The shared orchestrator instance
    """
    global _orchestrator
    
    if _orchestrator is None:
        async with _initialization_lock:
            if _orchestrator is None:
                logger.info("Initializing orchestrator asynchronously...")
                _orchestrator = Orchestrator()
                await _orchestrator.startup()
                logger.info("Orchestrator initialized successfully")
    
    return _orchestrator

def get_orchestrator() -> Orchestrator:
    """
    Get or create the orchestrator instance synchronously.
    
    This is a synchronous dependency that ensures the orchestrator is properly initialized.
    It creates a single instance of the orchestrator that's shared across all requests.
    
    Returns:
        Orchestrator: The shared orchestrator instance
    """
    global _orchestrator
    
    if _orchestrator is None:
        with _orchestrator_lock:
            if _orchestrator is None:
                logger.info("Initializing orchestrator synchronously...")
                _orchestrator = Orchestrator()
                
                # Create a new event loop for this thread if needed
                try:
                    # Try to get the current event loop
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # If there's no current event loop, create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Check if the loop is running
                if loop.is_running():
                    # If the loop is already running, we can't use run_until_complete
                    # Instead, we'll run the startup in a new task
                    async def startup():
                        await _orchestrator.startup()
                    
                    # Create a new event loop for the startup
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        new_loop.run_until_complete(startup())
                    finally:
                        new_loop.close()
                        # Restore the original event loop
                        asyncio.set_event_loop(loop)
                else:
                    # If the loop is not running, we can use run_until_complete
                    loop.run_until_complete(_orchestrator.startup())
                
                logger.info("Orchestrator initialized successfully")
    
    return _orchestrator
