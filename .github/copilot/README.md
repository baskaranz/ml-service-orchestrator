# ML Orchestrator - GitHub Copilot Resources

This directory contains resources to help GitHub Copilot understand and generate code for the ML Orchestrator service. It's structured to provide comprehensive guidance, examples, and context for AI-assisted coding.

## Directory Structure

```
.github/copilot/
├── instructions.md                  # Main entry point with architectural overview
├── instructions/                    # Layer-specific guidance
│   ├── api_layer.md                # API layer patterns and examples
│   ├── config_layer.md             # Configuration layer patterns
│   ├── core_layer.md               # Core domain layer patterns
│   ├── service_layer.md            # External service integration patterns
│   └── test_patterns.md            # Testing guidance and examples
├── component-examples/              # Complete implementations of key patterns
│   ├── README.md                   # Guide to using component examples
│   ├── circuit_breaker.py          # Resilience pattern implementation
│   ├── model_config.py             # Configuration system implementation
│   ├── cache_implementation.py     # Caching pattern implementation
│   ├── auth_scheme.py              # Authentication pattern implementation
│   ├── error_handling.py           # Error handling pattern implementation
│   ├── middleware.py               # Middleware components implementation
│   ├── request_response_transform.py # Request/response transformation
│   └── testing_patterns.py         # Test pattern implementations
├── templates/                       # Templates for common tasks
│   ├── README.md                   # Guide to using templates
│   └── ml_orchestrator_templates.py # Template generation script
├── prompts/                         # Example prompts for AI assistants
│   ├── README.md                   # Guide to using prompts
│   ├── examples/                   # Example prompt files
│   │   ├── bug_circuit_breaker.yaml    # Bug fixing example
│   │   ├── feature_caching.yaml        # Feature implementation example
│   │   ├── refactor_model_registry.yaml # Refactoring example
│   │   └── test_orchestrator.yaml      # Testing example
│   └── ml_orchestrator/            # ML Orchestrator specific prompts
│       └── caching_example.md      # Detailed example of caching implementation
├── scripts/                         # Scripts for AI-assisted development
│   ├── README.md                   # Guide to using scripts
│   ├── agentic_prompts.py          # Prompt generation utility
│   ├── claude_agent.py             # Claude integration script
│   └── claude_commands.sh          # Shell utilities for Claude
├── ml_orchestrator_agentic.md       # Guide for AI-agentic coding with ML Orchestrator
├── vibe_workflows.txt               # Patterns for voice-based coding workflows
├── claude_code_guide.md             # Guide for efficient coding with Claude Code
├── claude_code_snippets.yaml        # Reusable snippets for Claude Code
└── *.md                             # File-specific documentation for key files
```

## How to Use This Directory

### For Developers

1. **Start with [`instructions.md`](./instructions.md)** for a high-level overview of the ML Orchestrator architecture, patterns, and conventions.

2. **Review layer-specific instructions** in the `instructions/` directory for guidance on implementing components in each architectural layer.

3. **Study component examples** in the `component-examples/` directory for concrete implementations of key patterns used throughout the codebase.

4. **Reference file-specific documentation** for understanding individual files and their role in the system.

### For GitHub Copilot

GitHub Copilot uses these files to better understand the code patterns, architectural decisions, and naming conventions in the ML Orchestrator codebase. This helps Copilot generate more contextually appropriate and idiomatically correct code.

## ML Orchestrator Architecture

The ML Orchestrator follows a layered architecture:

1. **Config Layer**: Configuration loading and validation
   - YAML configuration parsing
   - Environment variable substitution
   - Pydantic model validation

2. **API Layer**: HTTP interface and request handling
   - FastAPI routes and dependencies
   - Authentication and authorization
   - Request validation and response formatting

3. **Core Layer**: Core business logic and domain models
   - Orchestration logic
   - Model management
   - Request handling and transformation

4. **Service Layer**: Integration with external services
   - Model registry client
   - Proxy service for inference requests
   - Circuit breaker pattern for resilience

5. **Utils Layer**: Common utilities and helpers
   - HTTP utilities
   - Logging helpers
   - Metrics collection

## Key Patterns

The ML Orchestrator uses several key design patterns that should be consistently applied:

1. **Circuit Breaker**: For resilient service-to-service communication
2. **Dependency Injection**: Using FastAPI's dependency system
3. **Configuration-Driven Design**: Using YAML for model configurations
4. **Repository Pattern**: For data access abstraction
5. **Async-First**: Asynchronous code throughout the application
6. **Structured Logging**: Consistent, contextual logging
7. **Middleware Pipeline**: For cross-cutting concerns

## Contributing to These Resources

When adding new features or patterns to the ML Orchestrator, consider updating these Copilot resources:

1. Add examples of new patterns to the `component-examples/` directory
2. Update relevant instruction files with guidance on the new pattern
3. Create file-specific documentation for significant new files

This ensures that GitHub Copilot maintains an up-to-date understanding of the codebase patterns.

## Related Resources

- [ML Orchestrator Agentic Guide](./ml_orchestrator_agentic.md): Comprehensive guide for AI-agentic coding with ML Orchestrator
- [VIBE Workflows](./vibe_workflows.txt): Patterns for voice-based coding workflows
- [Claude Code Guide](./claude_code_guide.md): Guide for efficient coding with Claude Code
- [Claude Code Snippets](./claude_code_snippets.yaml): Reusable snippets for Claude Code
- [Templates](./templates/): Template generation for common ML Orchestrator tasks
- [Prompts](./prompts/): Example prompts for AI assistants
- [Scripts](./scripts/): Scripts for AI-assisted development