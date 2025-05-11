#!/usr/bin/env python3
"""
Agentic Coding Prompt Generator

This script generates task prompts that enable the AI to work autonomously
on code-related tasks. It provides different templates for various types of
coding tasks with appropriate context and autonomy guidelines.

Usage:
  python agentic_prompts.py [task_type] [--options]
"""

import argparse
import os
import sys
import json
import yaml
from datetime import datetime
from pathlib import Path

# ANSI colors for terminal output
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

# Project information
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_NAME = "ML Orchestrator Service"

# Templates for different task types
TEMPLATES = {
    "feature": {
        "name": "Feature Implementation",
        "description": "Autonomous implementation of a new feature",
        "template": """
I need you to implement {feature_name} for the {project_name}. 

## Feature Description
{feature_description}

## Requirements
{requirements}

## Technical Guidelines
{technical_guidelines}

## Autonomy Level
You have full autonomy to:
- Design the implementation details
- Choose appropriate data structures and algorithms
- Create or modify necessary files
- Add tests for the new functionality
- Refactor existing code as needed for integration

Please ask for guidance only on:
- Major architectural changes
- Changes to public APIs
- External dependency additions

## Expected Deliverables
1. Complete implementation of the feature
2. Appropriate tests with good coverage
3. Any necessary documentation updates
4. Brief explanation of key design decisions

I trust your judgment on the implementation details. Focus on creating 
a solution that's maintainable, performant, and follows the project's 
existing patterns.
"""
    },
    "bug": {
        "name": "Bug Fix",
        "description": "Autonomous diagnosis and fixing of a bug",
        "template": """
I need you to fix a bug in the {project_name} related to {bug_area}.

## Bug Description
{bug_description}

## Expected Behavior
{expected_behavior}

## Current Behavior
{current_behavior}

## Autonomy Level
You have full autonomy to:
- Investigate the root cause
- Identify the appropriate fix
- Implement the solution
- Add tests to prevent regression
- Make related improvements if needed

Please ask for guidance only on:
- Fixes that could have broader impacts
- Solutions requiring architectural changes
- Changes to public interfaces

## Expected Deliverables
1. Root cause analysis
2. The implemented fix
3. Tests that verify the fix works
4. Brief explanation of what caused the bug and how your solution addresses it

Focus on creating a robust solution that addresses the underlying issue, not just the symptoms.
"""
    },
    "refactor": {
        "name": "Code Refactoring",
        "description": "Autonomous refactoring of existing code",
        "template": """
I need you to refactor {refactor_target} in the {project_name}.

## Refactoring Goal
{refactoring_goal}

## Current Issues
{current_issues}

## Constraints
{constraints}

## Autonomy Level
You have full autonomy to:
- Redesign internal implementation details
- Improve code structure and organization
- Enhance performance and readability
- Add or modify tests as needed
- Apply best practices and patterns

Please ask for guidance only on:
- Changes to public interfaces
- Breaking changes that affect other components
- Major architectural decisions

## Expected Deliverables
1. Refactored implementation
2. Updated or new tests
3. Brief explanation of your changes and their benefits
4. Any recommendations for further improvements

Focus on creating a cleaner, more maintainable implementation while preserving the existing functionality.
"""
    },
    "test": {
        "name": "Test Implementation",
        "description": "Autonomous creation of tests",
        "template": """
I need you to implement tests for {test_target} in the {project_name}.

## Testing Goals
{testing_goals}

## Test Coverage Requirements
{coverage_requirements}

## Technical Context
{technical_context}

## Autonomy Level
You have full autonomy to:
- Design test cases and scenarios
- Create appropriate fixtures and mocks
- Implement all necessary tests
- Refactor existing tests if needed
- Add helper functions for testing

Please ask for guidance only on:
- Testing approach for complex integrations
- Mocking external dependencies
- Test data privacy considerations

## Expected Deliverables
1. Comprehensive test suite
2. Any necessary test fixtures or helpers
3. Brief explanation of your testing approach
4. Test coverage report or summary

Focus on creating meaningful tests that verify behavior correctly, not just achieve line coverage.
"""
    },
    "analyze": {
        "name": "Code Analysis",
        "description": "Autonomous analysis of code quality, performance, or architecture",
        "template": """
I need you to analyze {analysis_target} in the {project_name}.

## Analysis Goals
{analysis_goals}

## Areas of Focus
{focus_areas}

## Context
{context}

## Autonomy Level
You have full autonomy to:
- Explore the codebase as needed
- Identify issues and improvement opportunities
- Suggest specific solutions or approaches
- Provide code examples for recommendations
- Assess trade-offs between different options

## Expected Deliverables
1. Comprehensive analysis findings
2. Specific recommendations for improvements
3. Code examples or patterns to implement
4. Prioritized list of suggested changes
5. Any additional insights discovered during analysis

Focus on providing actionable insights that would meaningfully improve the code.
"""
    },
    "architecture": {
        "name": "Architecture Design",
        "description": "Autonomous design of a system architecture",
        "template": """
I need you to design an architecture for {design_target} in the {project_name}.

## Architecture Goals
{architecture_goals}

## Requirements
{requirements}

## Constraints
{constraints}

## Autonomy Level
You have full autonomy to:
- Design the overall architecture
- Define component boundaries and interfaces
- Choose appropriate patterns and approaches
- Consider performance, scalability, and maintainability
- Suggest implementation strategies

Please ask for guidance only on:
- Major technology stack decisions
- Changes affecting existing architecture
- External system integrations

## Expected Deliverables
1. High-level architecture design
2. Component definitions and responsibilities
3. Key interfaces and data flows
4. Considerations for performance, security, and maintenance
5. Implementation strategy and recommendations

Focus on creating a clean, maintainable architecture that meets the requirements
while integrating well with the existing system.
"""
    },
    "optimize": {
        "name": "Performance Optimization",
        "description": "Autonomous optimization of code performance",
        "template": """
I need you to optimize {optimization_target} in the {project_name}.

## Optimization Goals
{optimization_goals}

## Current Performance Issues
{performance_issues}

## Constraints
{constraints}

## Autonomy Level
You have full autonomy to:
- Identify performance bottlenecks
- Implement optimization strategies
- Refactor code for better performance
- Update or add benchmarks/tests
- Make architectural changes if necessary

Please ask for guidance only on:
- Changes that significantly alter behavior
- Trade-offs that might affect maintainability
- Solutions requiring new dependencies

## Expected Deliverables
1. Optimized implementation
2. Performance benchmarks or metrics
3. Explanation of the optimizations made
4. Analysis of performance improvement
5. Any recommendations for further optimization

Focus on creating solutions that meaningfully improve performance while maintaining
code quality and correctness.
"""
    }
}

def generate_prompt(task_type, **kwargs):
    """Generate a prompt based on task type and parameters."""
    if task_type not in TEMPLATES:
        print(f"{RED}Error: Unknown task type '{task_type}'{RESET}")
        print(f"Available task types: {', '.join(TEMPLATES.keys())}")
        return None
    
    template = TEMPLATES[task_type]["template"]
    
    # Add project name if not provided
    kwargs.setdefault("project_name", PROJECT_NAME)
    
    # Try to format the template with provided kwargs
    try:
        formatted_prompt = template.format(**kwargs)
        return formatted_prompt
    except KeyError as e:
        print(f"{RED}Error: Missing required parameter {e}{RESET}")
        return None

def save_prompt(prompt, filename=None):
    """Save prompt to a file."""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"agentic_prompt_{timestamp}.txt"
    
    prompt_dir = PROJECT_ROOT / "prompts"
    prompt_dir.mkdir(exist_ok=True)
    
    file_path = prompt_dir / filename
    with open(file_path, "w") as f:
        f.write(prompt)
    
    print(f"{GREEN}Prompt saved to: {file_path}{RESET}")
    return file_path

def load_template_params(task_type):
    """Load the parameters needed for a template."""
    if task_type not in TEMPLATES:
        return None
    
    # Parse the template to extract required parameters
    template = TEMPLATES[task_type]["template"]
    params = []
    
    # Extract parameters from {parameter} format in the template
    import re
    pattern = r'\{([a-zA-Z_]+)\}'
    matches = re.findall(pattern, template)
    
    # Remove duplicates and project_name (which is auto-filled)
    params = [p for p in set(matches) if p != "project_name"]
    
    return params

def interactive_prompt(task_type):
    """Interactively collect parameters for a prompt template."""
    params = load_template_params(task_type)
    if not params:
        print(f"{RED}Error: Could not load parameters for task type '{task_type}'{RESET}")
        return None
    
    print(f"{BLUE}Generating an agentic prompt for: {TEMPLATES[task_type]['name']}{RESET}")
    print(f"{CYAN}Please provide the following information:{RESET}")
    
    kwargs = {"project_name": PROJECT_NAME}
    for param in params:
        # Format the parameter name for display
        display_name = param.replace("_", " ").title()
        
        # Check if it's likely a multi-line parameter
        is_multiline = any(ml in param for ml in ["description", "requirements", "context", "issues", "goals", "guidelines", "behavior", "constraints", "areas"])
        
        if is_multiline:
            print(f"\n{YELLOW}{display_name}:{RESET} (type your input and finish with a line containing only 'END')")
            lines = []
            while True:
                line = input()
                if line == "END":
                    break
                lines.append(line)
            kwargs[param] = "\n".join(lines)
        else:
            kwargs[param] = input(f"{YELLOW}{display_name}:{RESET} ")
    
    return generate_prompt(task_type, **kwargs)

def main():
    """Main function for the script."""
    parser = argparse.ArgumentParser(description="Generate agentic coding prompts")
    parser.add_argument("task_type", nargs="?", help="Type of task (feature, bug, refactor, test, analyze, architecture, optimize)")
    parser.add_argument("--list", action="store_true", help="List available task types")
    parser.add_argument("--params", action="store_true", help="Show parameters for a task type")
    parser.add_argument("--output", "-o", help="Output filename")
    parser.add_argument("--json", "-j", help="JSON file with parameters")
    
    args = parser.parse_args()
    
    # List available task types
    if args.list:
        print(f"{BLUE}Available task types:{RESET}")
        for task_type, details in TEMPLATES.items():
            print(f"  {YELLOW}{task_type}{RESET}: {details['description']}")
        return 0
    
    # Show parameters for a task type
    if args.params:
        if not args.task_type:
            print(f"{RED}Error: Please specify a task type with --params{RESET}")
            return 1
        
        params = load_template_params(args.task_type)
        if not params:
            print(f"{RED}Error: Unknown task type '{args.task_type}'{RESET}")
            return 1
        
        print(f"{BLUE}Parameters for '{args.task_type}' task:{RESET}")
        for param in sorted(params):
            print(f"  {YELLOW}{param}{RESET}")
        return 0
    
    # Generate a prompt
    if not args.task_type:
        print(f"{BLUE}Available task types:{RESET}")
        for i, (task_type, details) in enumerate(TEMPLATES.items(), 1):
            print(f"  {i}. {YELLOW}{task_type}{RESET}: {details['description']}")
        
        choice = input(f"\n{YELLOW}Select a task type (1-{len(TEMPLATES)}): {RESET}")
        try:
            index = int(choice) - 1
            task_types = list(TEMPLATES.keys())
            if 0 <= index < len(task_types):
                args.task_type = task_types[index]
            else:
                print(f"{RED}Invalid selection. Please enter a number between 1 and {len(TEMPLATES)}.{RESET}")
                return 1
        except ValueError:
            print(f"{RED}Invalid selection. Please enter a number.{RESET}")
            return 1
    
    # Check for JSON parameters
    if args.json:
        try:
            with open(args.json, 'r') as f:
                if args.json.endswith('.yaml') or args.json.endswith('.yml'):
                    kwargs = yaml.safe_load(f)
                else:
                    kwargs = json.load(f)
            
            prompt = generate_prompt(args.task_type, **kwargs)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            print(f"{RED}Error parsing parameter file: {e}{RESET}")
            return 1
        except FileNotFoundError:
            print(f"{RED}Error: File {args.json} not found{RESET}")
            return 1
    else:
        # Interactive parameter collection
        prompt = interactive_prompt(args.task_type)
    
    if prompt:
        # Print the prompt
        print(f"\n{BLUE}Generated Prompt:{RESET}")
        print(f"{CYAN}{'-'*80}{RESET}")
        print(prompt)
        print(f"{CYAN}{'-'*80}{RESET}")
        
        # Save to file if requested
        save_option = input(f"\n{YELLOW}Save this prompt to a file? (y/N): {RESET}").lower()
        if save_option == 'y':
            save_prompt(prompt, args.output)
        
        # Copy to clipboard if pyperclip is available
        try:
            import pyperclip
            pyperclip.copy(prompt)
            print(f"{GREEN}Prompt copied to clipboard!{RESET}")
        except (ImportError, ModuleNotFoundError):
            pass
        
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())