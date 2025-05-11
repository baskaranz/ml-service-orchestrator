#!/usr/bin/env python3
"""
ML Orchestrator Agentic Task Templates

This script provides tailored agentic task templates specific to the ML Orchestrator
codebase. These templates incorporate knowledge of the project's architecture, 
patterns, and components to enable more effective agentic coding.

Usage:
  python ml_orchestrator_templates.py [template_name] [--output FILENAME]
"""

import argparse
import os
import sys
from pathlib import Path
import yaml
import json
from datetime import datetime

# ANSI colors for terminal output
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

# Project root
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Template definitions specific to ML Orchestrator patterns
TEMPLATES = {
    "model_config": {
        "name": "Model Configuration Extension",
        "description": "Extend the model configuration system with new features",
        "template": """
I need you to extend the ML Orchestrator's model configuration system to support {feature_name}.

## Current Architecture Context
The ML Orchestrator uses a YAML-driven configuration system with these components:
- `app/core/models.py`: Contains the ModelConfig Pydantic model and related schemas
- `app/config/models_config.py`: Handles loading and parsing YAML configurations
- Configuration files in `config/models/` directory define actual model endpoints
- Environment variable substitution using ${VAR:default} syntax
- Hot-reloading capability for configuration changes

## Implementation Requirements
Based on this architecture, implement a new configuration feature that:
1. Adds {feature_description}
2. Updates the ModelConfig Pydantic model with appropriate new fields
3. Updates YAML parsing in ModelConfigManager to handle the new configuration
4. Adds proper validation and default values
5. Updates the Orchestrator to use the new configuration feature
6. Adds comprehensive tests for the new functionality

## Technical Guidelines
- Follow the existing pattern of nested Pydantic models for structured config
- Ensure backward compatibility with existing configuration files
- Use proper type hints and validation
- Add descriptive docstrings that match the existing style
- Maintain the hot-reloading capability
- Update test fixtures to include the new configuration

## Similar Examples to Follow
- Study how similar features like circuit_breaker and auth are implemented
- The caching configuration provides a good example of optional features
- See how timeout and retry settings are handled

## Testing Guidelines
- Add unit tests for the Pydantic model in tests/test_core/test_models.py
- Add configuration loading tests in tests/test_config/test_models_config.py
- Add integration tests for the feature in relevant service tests

You have full autonomy to implement this feature following ML Orchestrator's established patterns.
"""
    },
    "circuit_breaker": {
        "name": "Circuit Breaker Enhancement",
        "description": "Enhance the circuit breaker implementation",
        "template": """
I need you to enhance the circuit breaker implementation in the ML Orchestrator.

## Current Implementation
The current circuit breaker is implemented in `app/core/orchestrator.py` with these characteristics:
- CircuitBreaker class tracks failure counts and open/closed state
- Simple state model without half-open state
- Individual breakers per model endpoint
- Basic timeout-based reset mechanism
- Limited metrics on circuit state

## Enhancement Requirements
Implement these specific enhancements:
1. Add a half-open state that allows a single test request
2. Implement {enhancement_feature}
3. Add more detailed metrics for circuit breaker operations
4. Improve the failure detection logic to be more robust
5. Add appropriate logging for state transitions

## Technical Guidelines
- Maintain backward compatibility with existing configuration
- Follow the async patterns established in the codebase
- Use proper type hints and validation
- Add detailed docstrings and code comments
- Implement comprehensive tests for each state transition

## Implementation Strategy
1. First, study the current CircuitBreaker class and how it's used in Orchestrator
2. Extend the CircuitBreaker state model to include half-open state
3. Update the proxy_request method to handle the enhanced circuit breaker
4. Add appropriate logging for circuit breaker state changes
5. Update tests to cover new states and transitions

## Testing Guidelines
- Add unit tests for the CircuitBreaker class in tests/test_core/
- Test all state transitions and edge cases
- Ensure proper async test patterns with pytest.mark.asyncio
- Use AsyncMock for mocking async functions

You have full autonomy to enhance this critical component following the established patterns.
"""
    },
    "caching": {
        "name": "Response Caching Implementation",
        "description": "Implement a caching system for model responses",
        "template": """
I need you to implement a response caching system for the ML Orchestrator.

## Current Architecture Context
The ML Orchestrator has these relevant components:
- `app/services/proxy.py`: Handles proxying requests to model endpoints
- `app/services/model_registry.py`: Manages model configurations
- `app/core/models.py`: Contains Pydantic models for configuration
- FastAPI dependency injection for services

## Implementation Requirements
Based on this architecture, implement a caching system that:
1. Creates a new CacheService in app/services/cache.py
2. Adds cache configuration to ModelConfig in app/core/models.py
3. Integrates caching in the ProxyService in app/services/proxy.py
4. Adds cache metrics to health reporting
5. {additional_requirement}

## Cache Functionality
The cache should:
- Use model ID and request content hash as cache keys
- Support TTL-based expiration configurable per model
- Include hit/miss metrics for monitoring
- Support cache bypass via request header
- Follow our existing async patterns

## Technical Guidelines
- Follow the dependency injection pattern used in other services
- Use proper type hints and comprehensive docstrings
- Use async/await consistently for all operations
- Integrate with existing error handling patterns
- Handle edge cases like cache invalidation on model updates

## Testing Guidelines
- Create tests in tests/test_services/test_cache.py
- Test cache hits, misses, and expiration
- Test integration with ProxyService
- Test cache bypass functionality
- Ensure proper async testing with pytest.mark.asyncio

You have full autonomy to implement this feature following our established patterns.
"""
    },
    "model_registry": {
        "name": "Model Registry Optimization",
        "description": "Optimize the ModelRegistry service for better performance",
        "template": """
I need you to optimize the ModelRegistry service in the ML Orchestrator.

## Current Implementation
The current implementation in `app/services/model_registry.py` has these performance issues:
- Linear search for model lookups (O(n) complexity)
- Inefficient model updates requiring full reload
- No concurrency control for simultaneous operations
- Limited error handling for edge cases
- {additional_issue}

## Optimization Requirements
Implement these specific optimizations:
1. Change the internal data structure for O(1) lookups
2. Implement efficient partial updates
3. Add proper async locking for thread safety
4. Improve error handling for missing models
5. Add registry metrics for monitoring

## Technical Constraints
- Maintain the existing public API
- Follow our async/await patterns
- Ensure backward compatibility
- Keep the hot-reload capability
- Maintain 100% test coverage for this module

## Implementation Strategy
1. Study the current ModelRegistry implementation carefully
2. Develop a more efficient data structure for model storage
3. Implement proper locking mechanism for updates
4. Enhance error handling with specific error types
5. Add appropriate logging and metrics

## Testing Guidelines
- Update tests in tests/test_services/test_model_registry.py
- Test concurrent operations for thread safety
- Test all error conditions and edge cases
- Benchmark performance improvements
- Ensure all async functions are properly tested

You have full autonomy to refactor this service for better performance.
"""
    },
    "orchestrator_tests": {
        "name": "Orchestrator Testing",
        "description": "Implement comprehensive tests for the Orchestrator",
        "template": """
I need you to implement comprehensive tests for the Orchestrator component in the ML Orchestrator service.

## Current State
The current test coverage for `app/core/orchestrator.py` is approximately 65%.
These areas need better test coverage:
- Circuit breaker state transitions and recovery
- Request routing with different model configurations
- Error handling for various failure scenarios
- Timeout and retry mechanism
- Authentication header processing
- {additional_area}

## Testing Requirements
Implement tests in tests/test_core/test_orchestrator.py that:
1. Cover all the areas mentioned above
2. Test both success and failure paths
3. Test edge cases and error conditions
4. Achieve at least 90% test coverage
5. Follow our established testing patterns

## ML Orchestrator Testing Patterns
When implementing these tests, follow these project-specific patterns:
- Use pytest.mark.asyncio for async tests
- Use AsyncMock for mocking async functions
- Create appropriate fixtures in tests/conftest.py as needed
- Study existing tests in tests/test_core/ for guidance
- Use clear assertion messages for test failures

## Implementation Strategy
1. Study the orchestrator.py implementation to identify untested paths
2. Create mock model configurations for different scenarios
3. Test each orchestrator method with various inputs
4. Test the circuit breaker functionality comprehensively
5. Mock external dependencies appropriately

## Testing Guidelines
- Test normal operation of all methods
- Test error conditions and exception handling
- Test circuit breaker state transitions
- Test timeout and retry logic
- Test authentication and header processing

You have full autonomy to implement these tests following our established patterns.
"""
    },
    "health_monitoring": {
        "name": "Health Monitoring Enhancement",
        "description": "Enhance the health monitoring system",
        "template": """
I need you to enhance the health monitoring system in the ML Orchestrator.

## Current Implementation
The current health monitoring is implemented in `app/api/routes/health.py` with:
- Basic /health endpoint for simple status
- /health/details endpoint for component status
- Limited metrics and monitoring capabilities
- {current_limitation}

## Enhancement Requirements
Implement these specific enhancements:
1. Add model endpoint health checking
2. Implement detailed component status reporting
3. Add performance metrics collection
4. Create alerting thresholds for health status
5. {enhancement_requirement}

## Technical Guidelines
- Build on the existing health endpoints in app/api/routes/health.py
- Follow the async patterns established in the codebase
- Use proper Pydantic models for responses
- Implement health checks that don't impact performance
- Add appropriate caching for health status

## Implementation Strategy
1. Study the current health implementation
2. Design enhanced health check models and responses
3. Implement model endpoint health probing
4. Add performance metric collection
5. Integrate with the circuit breaker system for status

## Testing Guidelines
- Update tests in tests/test_api/test_health.py
- Test all health endpoints and scenarios
- Test error conditions and degraded status
- Ensure proper async testing with pytest.mark.asyncio
- Mock dependencies appropriately

You have full autonomy to enhance this health monitoring system.
"""
    },
    "error_handling": {
        "name": "Error Handling Improvement",
        "description": "Improve the error handling system",
        "template": """
I need you to improve the error handling system in the ML Orchestrator.

## Current Implementation
The current error handling is implemented in `app/core/exceptions.py` with:
- Basic custom exception types
- FastAPI exception handlers
- Limited error details and context
- Inconsistent error propagation patterns
- {current_limitation}

## Improvement Requirements
Implement these specific improvements:
1. Create a more structured exception hierarchy
2. Add detailed error context to exceptions
3. Implement consistent error propagation patterns
4. Improve error responses with more details
5. {improvement_requirement}

## Technical Guidelines
- Build on the existing exceptions in app/core/exceptions.py
- Follow FastAPI exception handling patterns
- Use proper type hints and docstrings
- Ensure errors are properly logged with context
- Maintain backward compatibility for API consumers

## Implementation Strategy
1. Study the current exception types and handlers
2. Design an improved exception hierarchy
3. Update exception handlers for better error responses
4. Update services to use the new exception types
5. Add context information to exceptions

## Testing Guidelines
- Update tests in tests/test_core/test_exceptions.py
- Test all exception types and handlers
- Test error propagation across components
- Ensure consistent error responses
- Test logging and context information

You have full autonomy to improve this error handling system.
"""
    },
    "api_endpoints": {
        "name": "API Endpoint Implementation",
        "description": "Implement new API endpoints",
        "template": """
I need you to implement new API endpoints for {feature_name} in the ML Orchestrator.

## Current Architecture
The ML Orchestrator's API is organized with:
- FastAPI application in app/main.py
- Route modules in app/api/routes/
- Dependencies in app/api/dependencies.py
- Services injected via dependency injection
- {architecture_detail}

## Endpoint Requirements
Implement these new endpoints:
1. {endpoint_1_description}
2. {endpoint_2_description}
3. Ensure proper authentication via API key where needed
4. Add comprehensive request/response validation
5. Implement proper error handling

## Technical Guidelines
- Follow the existing patterns in app/api/routes/
- Use Pydantic models for request/response
- Use dependency injection for services
- Follow our async/await patterns
- Add proper documentation with docstrings

## Implementation Strategy
1. Study the existing routes for patterns
2. Create new route module or extend existing one
3. Define appropriate Pydantic models
4. Implement endpoint handlers with proper authentication
5. Register routes in app/main.py

## Testing Guidelines
- Add tests in tests/test_api/
- Test successful operations
- Test authentication failures
- Test validation errors
- Test with various inputs

You have full autonomy to implement these endpoints following our established patterns.
"""
    },
    "metrics": {
        "name": "Metrics Collection System",
        "description": "Implement a metrics collection system",
        "template": """
I need you to implement a metrics collection system for the ML Orchestrator.

## Current State
The ML Orchestrator currently has:
- Limited health monitoring in app/api/routes/health.py
- No centralized metrics collection
- Manual logging of important events
- {current_limitation}

## Metrics Requirements
Implement a metrics system that collects:
1. Request counts and latencies per model
2. Success/failure rates and error types
3. Circuit breaker state changes
4. Cache hit/miss rates (if applicable)
5. {additional_metric}

## Technical Guidelines
- Create a new metrics service in app/services/metrics.py
- Use an in-memory storage with configurable persistence
- Follow our dependency injection patterns
- Make metrics collection lightweight and non-blocking
- Add endpoints for metrics retrieval

## Implementation Strategy
1. Design the metrics data models
2. Implement the metrics collection service
3. Integrate with existing components via hooks
4. Add metrics endpoint in app/api/routes/
5. Update health endpoints to include metrics

## Testing Guidelines
- Add tests in tests/test_services/test_metrics.py
- Test metrics collection accuracy
- Test concurrent metrics updates
- Test metrics retrieval
- Test integration with other components

You have full autonomy to implement this metrics system following our established patterns.
"""
    }
}

def get_templates():
    """Get the list of available templates."""
    return TEMPLATES

def get_template(name):
    """Get a specific template by name."""
    return TEMPLATES.get(name)

def list_templates():
    """Display the list of available templates."""
    print(f"{BLUE}Available ML Orchestrator templates:{RESET}\n")
    for key, template in TEMPLATES.items():
        print(f"{YELLOW}{key}{RESET}: {template['description']}")

def generate_prompt(template_name, params=None):
    """Generate a prompt from a template and parameters."""
    if template_name not in TEMPLATES:
        print(f"{RED}Error: Unknown template '{template_name}'{RESET}")
        list_templates()
        return None
    
    template = TEMPLATES[template_name]["template"]
    
    # If no params provided, use interactive mode to collect them
    if not params:
        params = {}
        # Extract parameter placeholders from the template
        import re
        placeholders = re.findall(r'\{([^{}]+)\}', template)
        placeholders = list(set(placeholders))  # Remove duplicates
        
        print(f"{BLUE}Generating template: {TEMPLATES[template_name]['name']}{RESET}")
        print(f"{YELLOW}Please provide values for the following parameters:{RESET}\n")
        
        for placeholder in placeholders:
            # Format the placeholder name for display
            display_name = placeholder.replace("_", " ").title()
            
            # Check if it might need a multi-line input
            is_multiline = any(ml in placeholder for ml in ["description", "requirement", "detail", "issue", "limitation"])
            
            if is_multiline:
                print(f"{CYAN}{display_name}:{RESET} (Enter text, finish with a line containing only 'END')")
                lines = []
                while True:
                    line = input()
                    if line == "END":
                        break
                    lines.append(line)
                value = "\n".join(lines)
            else:
                value = input(f"{CYAN}{display_name}:{RESET} ")
            
            params[placeholder] = value
    
    try:
        # Format the template with the provided parameters
        prompt = template.format(**params)
        return prompt
    except KeyError as e:
        print(f"{RED}Error: Missing parameter {e}{RESET}")
        return None

def save_prompt(prompt, filename=None):
    """Save the generated prompt to a file."""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ml_orchestrator_prompt_{timestamp}.txt"
    
    prompts_dir = PROJECT_ROOT / "prompts" / "ml_orchestrator"
    prompts_dir.mkdir(exist_ok=True, parents=True)
    
    file_path = prompts_dir / filename
    with open(file_path, "w") as f:
        f.write(prompt)
    
    print(f"{GREEN}Prompt saved to: {file_path}{RESET}")
    return file_path

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="ML Orchestrator Agentic Task Templates")
    parser.add_argument("template", nargs="?", help="Template name to use")
    parser.add_argument("--list", action="store_true", help="List available templates")
    parser.add_argument("--output", "-o", help="Output filename")
    parser.add_argument("--params", "-p", help="JSON or YAML file with template parameters")
    
    args = parser.parse_args()
    
    # List available templates
    if args.list:
        list_templates()
        return 0
    
    # If no template specified, show menu
    if not args.template:
        list_templates()
        print(f"\n{YELLOW}Select a template by name or number:{RESET}")
        choice = input("> ")
        
        # Check if input is a number
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(TEMPLATES):
                templates = list(TEMPLATES.keys())
                args.template = templates[choice_num - 1]
            else:
                print(f"{RED}Invalid selection.{RESET}")
                return 1
        except ValueError:
            # Input is not a number, treat as template name
            args.template = choice
    
    # Check if template exists
    if args.template not in TEMPLATES:
        print(f"{RED}Error: Unknown template '{args.template}'{RESET}")
        list_templates()
        return 1
    
    # Load parameters from file if specified
    params = None
    if args.params:
        try:
            with open(args.params, 'r') as f:
                if args.params.endswith(('.yaml', '.yml')):
                    params = yaml.safe_load(f)
                else:
                    params = json.load(f)
        except (FileNotFoundError, yaml.YAMLError, json.JSONDecodeError) as e:
            print(f"{RED}Error loading parameters: {e}{RESET}")
            return 1
    
    # Generate the prompt
    prompt = generate_prompt(args.template, params)
    if not prompt:
        return 1
    
    # Print the prompt
    print(f"\n{BLUE}Generated ML Orchestrator Prompt:{RESET}")
    print(f"{CYAN}{'-'*80}{RESET}")
    print(prompt)
    print(f"{CYAN}{'-'*80}{RESET}")
    
    # Save to file if requested
    save_option = input(f"\n{YELLOW}Save this prompt to a file? (y/N): {RESET}").lower()
    if save_option == 'y':
        save_prompt(prompt, args.output)
    
    # Try to copy to clipboard
    try:
        import pyperclip
        pyperclip.copy(prompt)
        print(f"{GREEN}Prompt copied to clipboard!{RESET}")
    except ImportError:
        pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main())