# ML Orchestrator Templates

This directory contains templates and scripts for working with the ML Orchestrator project. These templates provide structured guidance for common tasks and help maintain consistency across the codebase.

## Contents

- `ml_orchestrator_templates.py`: A script for generating tailored task templates for the ML Orchestrator service
- Template files for common operations like implementing model configurations, enhancing circuit breakers, and implementing caching

## Using the Templates

The `ml_orchestrator_templates.py` script provides several predefined templates that you can use as starting points for working with the ML Orchestrator. To use it:

```bash
# List available templates
python ml_orchestrator_templates.py --list

# Generate a specific template
python ml_orchestrator_templates.py model_config

# Save the generated template to a file
python ml_orchestrator_templates.py caching --output my_template.md
```

Each template will prompt you for specific parameters that will be used to customize the output.

## Available Templates

- **model_config**: For extending the model configuration system
- **circuit_breaker**: For enhancing the circuit breaker implementation
- **caching**: For implementing a response caching system
- **model_registry**: For optimizing the ModelRegistry service
- **orchestrator_tests**: For implementing comprehensive Orchestrator tests
- **health_monitoring**: For enhancing the health monitoring system
- **error_handling**: For improving the error handling system
- **api_endpoints**: For implementing new API endpoints
- **metrics**: For implementing a metrics collection system

## Integration with GitHub Copilot

These templates are designed to provide GitHub Copilot with domain-specific context and patterns for the ML Orchestrator service. They can be referenced in comments or documentation to help Copilot understand the expected implementation patterns.

Example:
```python
# TODO: Implement caching for model responses using the pattern from
# .github/copilot/templates/README.md - See the 'caching' template
```

## Related Resources

- [ML Orchestrator Agentic Guide](..//ml_orchestrator_agentic.md): Comprehensive guide for AI-agentic coding with ML Orchestrator
- [Component Examples](../component-examples/): Reference implementations of key patterns
- [Instructions](../instructions/): Detailed guidance for each architectural layer