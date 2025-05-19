"""Configuration management for the application."""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from configparser import ConfigParser

class AppConfig:
    """Application configuration manager."""
    
    def __init__(self, env: str = None):
        """Initialize configuration.
        
        Args:
            env: Environment name (dev, stg, prod). If None, uses APP_ENV environment variable.
        """
        self.env = env or os.getenv("APP_ENV", "dev").lower()
        self.config = self._load_config()
    
    def _get_config_path(self) -> Path:
        """Get the path to the configuration file.
        
        Returns:
            Path: Path to the app.cfg file in the config directory
        """
        config_path = Path(__file__).parent.parent.parent / "config" / "app.cfg"
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}"
            )
            
        return config_path
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from the config file.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        config_path = self._get_config_path()
        
        # Use ConfigParser to read the .cfg file
        config_parser = ConfigParser()
        config_parser.read(config_path)
        
        # Convert to dictionary
        config = {}
        for section in config_parser.sections():
            config[section] = dict(config_parser[section])
        
        # Add environment
        config["ENV"] = self.env
        
        # Process any environment variables in paths
        if "paths" in config:
            for key, value in config["paths"].items():
                config["paths"][key] = value.replace("{env}", self.env)
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        # Try to find the key in any section
        for section in self.config.values():
            if isinstance(section, dict) and key in section:
                return section[key]
        return default
    
    def __getitem__(self, key: str) -> Any:
        """Get a configuration value using dict-style access."""
        value = self.get(key)
        if value is None:
            raise KeyError(f"Configuration key not found: {key}")
        return value
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value."""
        value = self.get(key, str(default)).lower()
        return value in ('true', '1', 't', 'y', 'yes')
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer configuration value."""
        try:
            return int(self.get(key, default))
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float configuration value."""
        try:
            return float(self.get(key, default))
        except (ValueError, TypeError):
            return default

# Global configuration instance
config = AppConfig()
