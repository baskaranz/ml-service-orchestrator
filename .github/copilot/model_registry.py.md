# Create instructions for model_registry.py
Create a model registry service that:
1. Maintains an in-memory registry of model endpoints
2. Provides methods to add, update, and remove models
3. Handles model lookup by name or path pattern
4. Validates model configurations before adding them
5. Supports versioning of model endpoints
6. Implements proper locking for thread safety
7. Publishes events when models are added/updated/removed
8. Supports filtering and listing models with pagination