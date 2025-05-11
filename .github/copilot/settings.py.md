# Create instructions for settings.py
Create a settings class using pydantic-settings that:
1. Loads configuration from environment variables
2. Provides default values for all settings
3. Includes settings for API server (host, port, etc.)
4. Includes settings for config loading (directory, watch interval, etc.)
5. Includes settings for logging
6. Includes settings for security (admin API key, etc.)
7. Includes settings for proxy (default timeout, retries, etc.)
8. Validates settings on startup