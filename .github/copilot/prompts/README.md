# ML Orchestrator Prompts

This directory contains example prompts and templates for working with the ML Orchestrator project. These prompts provide structured guidance for common tasks and help maintain consistency across the codebase.

## Directory Structure

```
prompts/
├── examples/                   # Example prompt files
│   ├── bug_circuit_breaker.yaml    # Example prompt for fixing circuit breaker bugs
│   ├── feature_caching.yaml        # Example prompt for implementing caching
│   ├── refactor_model_registry.yaml # Example prompt for refactoring model registry
│   └── test_orchestrator.yaml      # Example prompt for testing orchestrator
└── ml_orchestrator/           # ML Orchestrator specific prompts
    └── caching_example.md     # Detailed example of caching implementation
```

## Using These Prompts

These prompts can be used as starting points when working with AI assistants like Claude or GitHub Copilot. They provide structured guidance for common tasks in the ML Orchestrator codebase, such as:

1. Implementing new features
2. Fixing bugs
3. Refactoring components
4. Writing tests

## Integration with Scripts

These prompts can be used with the scripts in the `../scripts/` directory, particularly:

- `agentic_prompts.py`: For generating and managing prompts
- `claude_agent.py`: For working with Claude as an agent

## Related Resources

- [ML Orchestrator Agentic Guide](../ml_orchestrator_agentic.md): Comprehensive guide for AI-agentic coding
- [Templates](../templates/): Templates for common ML Orchestrator tasks
- [Component Examples](../component-examples/): Reference implementations of key patterns