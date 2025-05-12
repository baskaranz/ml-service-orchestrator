"""Test initialization.

This module sets up all necessary patches for testing.
"""

import os
import sys
from unittest.mock import patch

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Add mocks directory to the Python path
mocks_dir = os.path.join(os.path.dirname(__file__), "mocks")
sys.path.insert(0, mocks_dir)

# Set test environment
os.environ["APP_ENV"] = "test"

# Create tmp test directory if it doesn't exist
os.makedirs("/tmp/test_config", exist_ok=True)
os.makedirs("/tmp/test_config/models", exist_ok=True)

# Import our mock settings
from tests.mocks.settings import settings as mock_settings

# Patch app.config.settings with our mock
sys.modules["app.config.settings"] = sys.modules["tests.mocks.settings"]