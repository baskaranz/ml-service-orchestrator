# ML Orchestrator AI Scripts

This directory contains scripts for working with AI assistants like Claude to help with ML Orchestrator development. These scripts provide utilities for generating prompts, creating templates, and managing AI-assisted workflows.

## Scripts

### `agentic_prompts.py`

A utility for generating and managing agentic prompts for AI assistants. It helps create structured prompts for common tasks like implementing features, fixing bugs, or writing tests.

Usage:
```bash
python agentic_prompts.py --template feature_implementation --output my_prompt.md
```

### `claude_agent.py`

A script for working with Claude as an agent for ML Orchestrator development. It provides utilities for sending prompts to Claude and processing responses.

Usage:
```bash
python claude_agent.py --prompt prompts/examples/feature_caching.yaml
```

### `claude_commands.sh`

Shell commands and utilities for working with Claude from the command line.

Usage:
```bash
source claude_commands.sh
claude_implement_feature "Add caching to model registry"
```

## Integration with Templates

These scripts integrate with the templates in the `../templates/` directory. You can use them together to generate consistent, high-quality prompts and code.

## Related Resources

- [ML Orchestrator Agentic Guide](../ml_orchestrator_agentic.md): Comprehensive guide for AI-agentic coding
- [Prompts](../prompts/): Example prompts for common tasks
- [Templates](../templates/): Templates for common ML Orchestrator tasks
- [Component Examples](../component-examples/): Reference implementations of key patterns