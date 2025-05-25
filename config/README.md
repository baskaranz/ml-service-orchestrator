# Environment-Specific Configurations

This directory contains environment-specific configuration files for the ML Orchestrator application.

## Available Configurations

1. **Development** (`config/dev/app.cfg`)
   - Debug mode enabled
   - More verbose logging
   - Local development database (SQLite)
   - Higher timeouts for development

2. **Staging** (`config/stg/app.cfg`)
   - Debug mode disabled
   - Staging database and services
   - Moderate logging

3. **Production** (`config/prod/app.cfg`)
   - Optimized for performance
   - Production database and services
   - Minimal logging
   - Security-focused settings

## Deployment Instructions

### For Development
1. Copy the development config:
   ```bash
   cp config/dev/app.cfg config/local/app.cfg
   ```
2. Update any local paths or settings in `config/local/app.cfg`

### For Staging
1. Copy the staging config:
   ```bash
   cp config/stg/app.cfg config/app.cfg
   ```
2. Set required environment variables (database credentials, secrets, etc.)
3. Deploy the application

### For Production
1. Copy the production config:
   ```bash
   cp config/prod/app.cfg config/app.cfg
   ```
2. Set up secrets management for sensitive data
3. Configure monitoring and alerting
4. Deploy the application

## Configuration Override Order

1. Base configuration (`config/app.cfg`)
2. Environment-specific configuration (`config/{env}/app.cfg`)
3. Local overrides (`config/local/app.cfg`)
4. Environment variables (for sensitive data)

## Security Considerations

- Never commit sensitive data to version control
- Use environment variables or a secrets manager for production credentials
- Set appropriate file permissions for configuration files
- Rotate secrets and API keys regularly
