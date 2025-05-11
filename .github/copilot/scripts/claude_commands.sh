#!/bin/bash
# Claude Code workflow helper script
# This script provides quick reference for common Claude Code commands

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Function to display a section heading
section() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n"
}

# Function to display a command example
command_example() {
    echo -e "${YELLOW}$1${NC}"
    echo -e "${CYAN}$2${NC}\n"
}

# Check if a specific command was requested
if [ "$1" == "help" ] || [ -z "$1" ]; then
    echo -e "${GREEN}Claude Code Command Helper${NC}"
    echo -e "${YELLOW}Usage: ${NC}"
    echo -e "  ./claude_commands.sh [category]"
    echo -e "\n${YELLOW}Available categories:${NC}"
    echo -e "  search     - Commands for searching code"
    echo -e "  read       - Commands for reading files"
    echo -e "  edit       - Commands for editing code"
    echo -e "  test       - Commands for testing"
    echo -e "  plan       - Commands for planning work"
    echo -e "  debug      - Commands for debugging"
    echo -e "  analyze    - Commands for code analysis"
    echo -e "  patterns   - Efficient command patterns"
    echo -e "  batch      - Batch operation examples"
    echo -e "  all        - Show all commands"
    exit 0
fi

# Show search-related commands
if [ "$1" == "search" ] || [ "$1" == "all" ]; then
    section "Search Commands"
    
    command_example "Search for files by pattern:" \
        "Find all Python files that contain 'circuit_breaker'"
    
    command_example "Search for class definitions:" \
        "Find all files that define a class related to logging"
    
    command_example "Search for function usage:" \
        "Find all places where the function 'get_model_config' is called"
    
    command_example "Search across specific directories:" \
        "Search for 'health check' implementations in the api directory"
    
    command_example "Combined search:" \
        "Find all files that import HttpClient and use circuit breaker pattern"
fi

# Show read-related commands
if [ "$1" == "read" ] || [ "$1" == "all" ]; then
    section "Read Commands"
    
    command_example "Read specific file:" \
        "Show me the contents of app/core/models.py"
    
    command_example "Read file with context:" \
        "Show me the ModelConfig class definition in app/core/models.py"
    
    command_example "Read multiple files:" \
        "Let's look at the health check implementation across all files"
    
    command_example "Read with line numbers:" \
        "Show me lines 50-100 of app/services/proxy.py"
    
    command_example "Batch reading:" \
        "Read all test files related to the model registry service"
fi

# Show edit-related commands
if [ "$1" == "edit" ] || [ "$1" == "all" ]; then
    section "Edit Commands"
    
    command_example "Add new functionality:" \
        "Add a timeout parameter to the HttpClient class in app/utils/http.py"
    
    command_example "Modify existing code:" \
        "Update the circuit breaker pattern to use exponential backoff"
    
    command_example "Fix a bug:" \
        "Fix the issue in app/services/proxy.py where timeout isn't properly propagated"
    
    command_example "Create new file:" \
        "Create a new module for caching at app/services/cache.py"
    
    command_example "Batch edits:" \
        "Update all services to use the new logging pattern"
fi

# Show test-related commands
if [ "$1" == "test" ] || [ "$1" == "all" ]; then
    section "Test Commands"
    
    command_example "Create a test file:" \
        "Create tests for the CircuitBreaker class in app/core/orchestrator.py"
    
    command_example "Add specific test cases:" \
        "Add tests for error handling in the proxy service"
    
    command_example "Run tests:" \
        "Run all tests related to the model registry service"
    
    command_example "Check test coverage:" \
        "Check test coverage for app/utils/http.py and suggest improvements"
    
    command_example "Create comprehensive test suite:" \
        "Implement a complete test suite for the new caching functionality"
fi

# Show planning commands
if [ "$1" == "plan" ] || [ "$1" == "all" ]; then
    section "Planning Commands"
    
    command_example "Plan a feature implementation:" \
        "Let's plan how to implement response caching for model endpoints"
    
    command_example "Break down tasks:" \
        "Break down the implementation of the metrics collection system into steps"
    
    command_example "Estimate complexity:" \
        "Analyze the circuit breaker implementation and estimate complexity"
    
    command_example "Dependency analysis:" \
        "Identify all dependencies needed for implementing the new auth system"
    
    command_example "Implementation strategy:" \
        "What's the best approach to refactor the model registry for better performance?"
fi

# Show debugging commands
if [ "$1" == "debug" ] || [ "$1" == "all" ]; then
    section "Debugging Commands"
    
    command_example "Diagnose an error:" \
        "Help debug this error: [error message]"
    
    command_example "Trace code execution:" \
        "Walk through the execution flow when a model request fails"
    
    command_example "Find a bug:" \
        "Find the bug causing timeouts when multiple requests are sent"
    
    command_example "Fix specific issue:" \
        "Fix the race condition in the circuit breaker implementation"
    
    command_example "Performance issue:" \
        "Debug why the model registry is slow when loading many models"
fi

# Show code analysis commands
if [ "$1" == "analyze" ] || [ "$1" == "all" ]; then
    section "Code Analysis Commands"
    
    command_example "Architecture overview:" \
        "Explain the overall architecture of the ML orchestrator service"
    
    command_example "Component analysis:" \
        "Analyze how the proxy service works and its main components"
    
    command_example "Interface review:" \
        "Review the API endpoints for the admin interface"
    
    command_example "Code quality check:" \
        "Assess the code quality in app/core/orchestrator.py"
    
    command_example "Security review:" \
        "Analyze the authentication system for security issues"
fi

# Show efficient command patterns
if [ "$1" == "patterns" ] || [ "$1" == "all" ]; then
    section "Efficient Command Patterns"
    
    command_example "Search → Read → Modify pattern:" \
        "Find all places using hardcoded timeouts, then update them to use configuration"
    
    command_example "Plan → Implement → Test pattern:" \
        "Let's implement circuit breaker: first plan approach, then code it, then test it"
    
    command_example "Iterate → Refine pattern:" \
        "Implement basic caching first, then let's refine it with more features"
    
    command_example "Diagnose → Fix → Verify pattern:" \
        "Find the cause of the 500 errors, fix the issue, then verify it works"
    
    command_example "Analyze → Optimize pattern:" \
        "Analyze performance bottlenecks in the proxy service, then optimize them"
fi

# Show batch operation examples
if [ "$1" == "batch" ] || [ "$1" == "all" ]; then
    section "Batch Operation Examples"
    
    command_example "Batch file reading:" \
        "Read all the API route definitions across the project"
    
    command_example "Multi-file edits:" \
        "Update all uses of HttpClient to include the new timeout parameter"
    
    command_example "Coordinated changes:" \
        "Add the new authentication system across all relevant files"
    
    command_example "Related component updates:" \
        "Refactor both the model registry and orchestrator to use the new interface"
    
    command_example "Feature implementation:" \
        "Implement metrics collection across all services in one coordinated change"
fi

echo -e "\n${GREEN}Tip:${NC} Use these commands as templates, adapting them to your specific needs"
echo -e "${GREEN}Tip:${NC} Be specific about file paths and components to reduce token usage"
echo -e "${GREEN}Tip:${NC} Batch related operations together for better efficiency"
echo -e "${GREEN}Tip:${NC} Follow up complex commands with verification questions"