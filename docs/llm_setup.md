# LLM Provider Setup and Configuration

This document describes how to configure and use LLM providers in the platform for error classification and other features.

## Configuration

The platform uses a YAML-based configuration system for LLM providers. The configuration is environment-aware and can be customized for different deployment environments.

### Configuration File

The LLM configuration is defined in `config/platform/llm_config.yaml`:

```yaml
# Default provider configuration
default_provider:
  type: "huggingface" # or "ollama"
  model_name: "mistralai/Mistral-7B-Instruct-v0.2" # optional
  timeout: 30.0
  max_retries: 3

# Environment-specific overrides
environments:
  development:
    type: "ollama" # Use local Ollama in development
    model_name: "mistral"
    timeout: 30
    max_retries: 3

  production:
    type: "huggingface" # Use Hugging Face in production
    model_name: "mistralai/Mistral-7B-Instruct-v0.2"
    timeout: 45
    max_retries: 5

  test:
    type: "huggingface" # Use smaller model for testing
    model_name: "google/flan-t5-small"
    timeout: 10
    max_retries: 2
```

### Configuration Parameters

- `type`: The LLM provider type ("huggingface" or "ollama")
- `model_name`: The name or ID of the model to use
- `timeout`: Request timeout in seconds
- `max_retries`: Maximum number of retry attempts
- `api_key`: (Optional) API key for the provider

## Environment Setup

### Hugging Face

1. Get an API key from [Hugging Face](https://huggingface.co/settings/tokens)
2. Set the API key in your environment:
   ```bash
   export HUGGINGFACE_API_KEY='your-api-key-here'
   ```
   Or add it to your `.env` file:
   ```
   HUGGINGFACE_API_KEY=your-api-key-here
   ```

### Ollama

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull the desired model:
   ```bash
   ollama pull mistral
   ```
3. Ensure Ollama is running locally (default port: 11434)

## Usage

The platform automatically loads the appropriate configuration based on the `APP_ENV` environment variable. If not set, it defaults to "development".

### Error Classification

The LLM is used for intelligent error classification and retry decisions. Error classifications include:

1. **Transient**: Temporary errors that should be retried
2. **Permanent**: Errors that should not be retried
3. **Rate Limit**: Errors that should be retried with backoff
4. **Authentication**: Authentication-related errors
5. **Input Validation**: Invalid input errors

### Retry Behavior

The system implements smart retry logic with exponential backoff:

- Transient errors are retried immediately
- Rate limit errors use exponential backoff
- Other errors are not retried

## Best Practices

1. **Development Environment**:

   - Use Ollama for local development
   - Faster iteration and no API costs
   - No need for API keys

2. **Production Environment**:

   - Use Hugging Face for production
   - Configure appropriate timeouts and retries
   - Set up proper API key management

3. **Testing Environment**:
   - Use smaller models for faster tests
   - Configure shorter timeouts
   - Reduce retry attempts

## Troubleshooting

### Common Issues

1. **API Key Not Found**:

   - Check if the API key is set in the environment
   - Verify the key is valid and has proper permissions

2. **Model Loading Issues**:

   - For Hugging Face: Check if the model is available
   - For Ollama: Ensure the model is pulled and Ollama is running

3. **Timeout Errors**:
   - Adjust the timeout value in the configuration
   - Consider using a smaller model for faster responses

### Logging

The system logs important events and errors:

- Configuration loading
- Error classifications
- Retry attempts
- API errors

## Performance Considerations

1. **Model Selection**:

   - Choose models based on your needs
   - Consider response time vs. accuracy trade-offs

2. **Timeout Settings**:

   - Development: 30 seconds
   - Production: 45 seconds
   - Testing: 10 seconds

3. **Retry Strategy**:
   - Development: 3 retries
   - Production: 5 retries
   - Testing: 2 retries
