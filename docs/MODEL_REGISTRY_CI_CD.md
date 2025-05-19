# Model Registry CI/CD Pipeline

This document outlines the CI/CD pipeline for managing model configurations in a GitOps-style workflow.

## Repository Structure

```
model-registry-repo/
├── .github/
│   └── workflows/
│       ├── validate-models.yml   # CI: Validate model configs on PR
│       └── register-models.yml   # CD: Register models on merge to main
└── config/
    └── models/                   # Model configuration files
        ├── model1.yaml
        └── model2.yaml
```

## CI: Model Validation Workflow

Runs on every pull request that modifies model configurations.

### Features:
- Validates YAML syntax
- Checks for required fields
- Validates endpoint URLs
- Runs on every PR

### Workflow File: `.github/workflows/validate-models.yml`

```yaml
name: Validate Model Configurations

on:
  pull_request:
    paths:
      - 'config/models/**'
      - '.github/workflows/validate-models.yml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyyaml pydantic
          
      - name: Validate model configurations
        run: |
          python -c "
          import yaml
          from pydantic import BaseModel, HttpUrl, validator
          from typing import Optional, Dict, Any
          import sys
          import glob

          class PlatformConfig(BaseModel):
              name: str
              config: Dict[str, Any] = {}

          class ModelConfig(BaseModel):
              id: str
              name: str
              endpoint_url: HttpUrl
              active: bool = True
              platform: PlatformConfig
              version: Optional[str] = '1.0.0'
              description: Optional[str] = None

          # Validate all YAML files in config/models
          has_errors = False
          for file in glob.glob('config/models/*.yaml') + glob.glob('config/models/*.yml'):
              try:
                  with open(file, 'r') as f:
                      data = yaml.safe_load(f)
                      ModelConfig(**data)
                  print(f'✅ {file} is valid')
              except Exception as e:
                  print(f'❌ {file} is invalid: {str(e)}')
                  has_errors = True

          if has_errors:
              sys.exit(1)
          "
```

## CD: Model Registration Workflow

Triggers on merge to main after successful validation.

### Features:
- Registers/updates models in the orchestrator
- Runs on merge to main
- Provides deployment status

### Workflow File: `.github/workflows/register-models.yml`

```yaml
name: Register Models

on:
  push:
    branches: [ main ]
    paths:
      - 'config/models/**'
      - '.github/workflows/register-models.yml'

jobs:
  register:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests pyyaml
          
      - name: Register models
        env:
          ORCHESTRATOR_URL: ${{ secrets.ORCHESTRATOR_URL }}
          ADMIN_API_KEY: ${{ secrets.ADMIN_API_KEY }}
        run: |
          python -c "
          import os
          import yaml
          import requests
          import glob
          from urllib.parse import urljoin

          ORCHESTRATOR_URL = os.environ['ORCHESTRATOR_URL']
          ADMIN_API_KEY = os.environ['ADMIN_API_KEY']
          HEADERS = {
              'X-API-Key': ADMIN_API_KEY,
              'Content-Type': 'application/json'
          }

          def register_model(model_config):
              url = urljoin(f'{ORCHESTRATOR_URL}/', 'admin/register-model')
              try:
                  response = requests.post(
                      url,
                      json={'model': model_config},
                      headers=HEADERS,
                      timeout=10
                  )
                  response.raise_for_status()
                  return True, None
              except requests.exceptions.RequestException as e:
                  return False, str(e)

          # Process all YAML files in config/models
          for file in glob.glob('config/models/*.yaml') + glob.glob('config/models/*.yml'):
              try:
                  with open(file, 'r') as f:
                      model_config = yaml.safe_load(f)
                      success, error = register_model(model_config)
                      if success:
                          print(f'✅ Successfully registered model: {model_config[\"id\"]}')
                      else:
                          print(f'❌ Failed to register model {model_config[\"id\"]}: {error}')
                          exit(1)
              except Exception as e:
                  print(f'❌ Error processing {file}: {str(e)}')
                  exit(1)
          "
```

## Local Development

### Validation Script

Create a local validation script at `scripts/validate_model.py`:

```python
import yaml
import sys
from pathlib import Path
from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Dict, Any
import glob

class PlatformConfig(BaseModel):
    name: str
    config: Dict[str, Any] = {}

class ModelConfig(BaseModel):
    id: str
    name: str
    endpoint_url: HttpUrl
    active: bool = True
    platform: PlatformConfig
    version: Optional[str] = '1.0.0'
    description: Optional[str] = None

def validate_model_file(file_path: Path):
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            ModelConfig(**data)
        print(f'✅ {file_path} is valid')
        return True
    except Exception as e:
        print(f'❌ {file_path} is invalid: {str(e)}')
        return False

if __name__ == '__main__':
    has_errors = False
    model_files = list(Path('config/models').glob('*.yaml')) + list(Path('config/models').glob('*.yml'))
    
    if not model_files:
        print('No model configuration files found in config/models/')
        sys.exit(1)
    
    for file in model_files:
        if not validate_model_file(file):
            has_errors = True
    
    if has_errors:
        sys.exit(1)
```

### Usage

1. Install dependencies:
   ```bash
   pip install pyyaml pydantic requests
   ```

2. Validate models locally:
   ```bash
   python scripts/validate_model.py
   ```

## Required Secrets

Set these in your repository's secrets:

1. `ORCHESTRATOR_URL`: Base URL of the orchestrator API
2. `ADMIN_API_KEY`: API key with admin privileges

## Best Practices

1. **Version Control**:
   - Keep model configurations in version control
   - Use meaningful commit messages
   - Include model version in the configuration

2. **Security**:
   - Never commit sensitive data
   - Use environment variables for secrets
   - Limit access to the repository

3. **CI/CD**:
   - Require PR reviews
   - Run tests before merging
   - Monitor deployment status

4. **Documentation**:
   - Document model purpose and usage
   - Include example requests/responses
   - Document any dependencies

## Example Model Configuration

```yaml
id: sentiment-analyzer
name: "Sentiment Analysis"
description: "Analyzes text sentiment"
version: "1.2.0"
endpoint_url: "https://api.example.com/v1/predict"
active: true
platform:
  name: "rest"
  config:
    timeout: 30
    max_retries: 3
    health_check:
      endpoint: "/health"
      interval: 30
      timeout: 5
      failure_threshold: 3

auth:
  type: "api_key"
  config:
    header_name: "X-API-Key"
    api_key: "${SENTIMENT_API_KEY}"

metadata:
  owner: "ml-team@example.com"
  environment: "production"
  created: "2025-05-17"
  updated: "2025-05-17"
```

## Troubleshooting

### Common Issues

1. **Validation Fails**
   - Check YAML syntax
   - Verify all required fields are present
   - Ensure endpoint URLs are valid

2. **Registration Fails**
   - Check orchestrator logs
   - Verify API key has correct permissions
   - Check network connectivity

3. **Environment Variables**
   - Ensure all required secrets are set
   - Check for typos in variable names
   - Verify values are properly escaped