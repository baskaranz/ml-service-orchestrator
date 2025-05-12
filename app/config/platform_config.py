"""
Platform configuration management.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from app.models.config_models import LLMProviderConfig
from app.utils.logging import get_logger

logger = get_logger(__name__)

class PlatformConfig:
    """Manages platform-wide configuration."""
    
    def __init__(self, config_dir: str = "config/platform"):
        """Initialize the platform configuration manager."""
        self.config_dir = config_dir
        self._llm_config: Optional[LLMProviderConfig] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load platform configuration files."""
        try:
            config_path = Path(self.config_dir)
            if not config_path.exists():
                logger.warning(f"Platform config directory not found: {self.config_dir}")
                return
            
            # Load LLM configuration
            llm_config_path = config_path / "llm_config.yaml"
            if llm_config_path.exists():
                with open(llm_config_path, "r") as f:
                    llm_config = yaml.safe_load(f)
                
                # Get environment-specific config or use default
                env = os.getenv("APP_ENV", "development").lower()
                env_config = llm_config.get("environments", {}).get(env, llm_config.get("default_provider", {}))
                
                self._llm_config = LLMProviderConfig(**env_config)
                logger.info(f"Loaded LLM configuration for environment: {env}")
            else:
                logger.warning(f"LLM configuration file not found: {llm_config_path}")
        
        except Exception as e:
            logger.error(f"Error loading platform configuration: {str(e)}")
            raise
    
    @property
    def llm_config(self) -> Optional[LLMProviderConfig]:
        """Get the LLM provider configuration."""
        return self._llm_config

# Create a singleton instance
platform_config = PlatformConfig() 