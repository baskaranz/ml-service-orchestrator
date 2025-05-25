"""Root conftest.py for setting up the global test environment.

This file ensures that the project root is added to the Python path for all tests.
It is intentionally kept minimal, with most test fixtures defined in tests/conftest.py
and specialized fixture modules in tests/fixtures/.

For test-specific fixtures, see:
- tests/conftest.py: Main test configuration and fixtures
- tests/fixtures/: Specialized fixture modules
"""

import os
import sys
from pathlib import Path

# Set test environment variable if not already set
if "APP_ENV" not in os.environ:
    os.environ["APP_ENV"] = "test"

# Add the project root directory to the Python path using absolute path
project_root = Path(__file__).resolve().absolute().parent
sys.path.insert(0, str(project_root))


# Print debug information when running with pytest -v
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: mark a test as a unit test")
    config.addinivalue_line("markers", "integration: mark a test as an integration test")
    config.addinivalue_line("markers", "slow: mark a test as slow-running")

    # Print environment information in verbose mode
    if config.option.verbose > 0:
        print(f"\nTest Environment: {os.environ.get('APP_ENV', 'not set')}")
        print(f"Project Root: {project_root}")
