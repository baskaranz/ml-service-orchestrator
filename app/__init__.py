"""
Main application package.
"""

from app.config import BaseAppSettings, get_settings, settings

__version__ = "1.0.0"
__all__ = ["BaseAppSettings", "settings", "get_settings"]
