# VIBE Coding with Claude Code

This guide provides strategies for efficient Voice/Verbal Input, Brain, Eyes (VIBE) coding workflow with Claude Code.

## Command Templates

For consistently effective interactions with Claude Code, use these command templates:

### File Navigation

```
Search for files related to [concept]:
"Find all files related to [concept]"
"Show me files that deal with [concept]"
"List python files that implement [concept]"
```

```
Explore a specific file:
"Open and examine [filename]"
"Show me the contents of [filename]"
"Let's look at [filename]"
```

### Understanding Code

```
Code overview:
"Give me a high-level overview of [filename]"
"Explain the main components in [filename]"
"What does the code in [filename] do?"
```

```
Function/class understanding:
"Explain the function [function_name] in [filename]"
"What does the class [class_name] do?"
"Walk me through the implementation of [component]"
```

### Code Modification

```
Create new file/feature:
"Create a new file [filename] with [feature]"
"Implement [feature] in a new file [filename]"
"Add a new [component type] for [feature]"
```

```
Modify existing code:
"Update [filename] to [do something]"
"Modify [function/class] in [filename] to [do something]"
"Change [specific thing] in [filename]"
```

```
Fix issues:
"Fix the error in [filename] where [problem description]"
"Debug the issue in [function] where [problem]"
"Resolve the problem with [component] that causes [symptom]"
```

### Testing

```
Create tests:
"Write tests for [function/class] in [filename]"
"Create a test file for [module]"
"Add test coverage for [functionality]"
```

```
Run tests:
"Run tests for [module]"
"Execute test file [test_filename]"
"Run tests with coverage for [module]"
```

### Code Review

```
Review code:
"Review the implementation of [feature]"
"Check if [filename] follows best practices"
"Evaluate the code quality in [filename]"
```

## Efficiency Strategies

### 1. Context Management

To minimize token usage and maximize efficiency:

- **Start with structure**: Begin with a high-level overview before diving into details
- **Specify file scopes**: Mention specific files rather than asking about general concepts
- **Use batching**: Request multiple related changes in a single prompt
- **Provide clear examples**: When applicable, provide an example of what you want

Example:
```
"Update these files:
1. In app/services/model_registry.py: Add error handling for network timeouts
2. In app/utils/http.py: Increase default timeout to 30 seconds
3. In app/api/routes/health.py: Add a check for model registry connectivity"
```

### 2. Task Definitions

Define tasks with specificity:

- **Scope**: Clearly define the boundaries of the task
- **Input/Output**: Specify expected inputs and outputs
- **Constraints**: Mention any limitations or requirements
- **Success criteria**: Define what "done" looks like

Example:
```
"Implement caching for model responses with these requirements:
- Cache should use an LRU strategy with configurable max size
- Cache key should be based on model ID and request content hash
- Cache TTL should be configurable per model
- Implementation should go in a new file: app/services/cache.py"
```

### 3. Progressive Refinement

Work iteratively for complex tasks:

1. **Start broad**: Begin with a high-level approach
2. **Request planning**: Ask for implementation steps before coding
3. **Chunked work**: Break complex tasks into smaller pieces
4. **Verification**: Check work at each step

Example:
```
"First, outline the approach for implementing the circuit breaker pattern.
Then, show me the steps needed to integrate it.
After that, we'll implement each component one by one."
```

### 4. File Operations Optimization

Minimize reading and writing operations:

- **Browse first**: Use Glob/LS before Read
- **Batch reading**: Read multiple files in one batch operation
- **Targeted edits**: Be specific about what to change in files
- **Avoid redundancy**: Don't re-read files Claude already knows about

Example:
```
"Search for all files that import HttpClient.
Then read those files and identify which ones need to be updated for the new timeout parameter."
```

### 5. Test-Focused Development

Prioritize testing for reliability:

- **Test first**: Ask for test implementation before production code
- **Coverage focus**: Target modules with low coverage
- **Test cases**: Explicitly list the test cases to cover
- **Validation**: Verify tests pass after implementation

Example:
```
"Let's implement tests for the CircuitBreaker class.
We need test cases for:
1. Circuit initially closed
2. Circuit opens after threshold failures
3. Circuit stays open during timeout period
4. Circuit resets after timeout period"
```

## Command Chaining Patterns

Optimize workflows with these command chains:

### Search → Read → Understand → Modify Pattern

```
1. "Find files related to [concept]"
2. "Read [specific_file] identified from search"
3. "Explain how [specific_file] works"
4. "Modify [specific_file] to [do something]"
```

### Plan → Implement → Test → Refine Pattern

```
1. "Plan how to implement [feature]"
2. "Implement [feature] according to the plan"
3. "Write tests for [feature]"
4. "Refine [feature] implementation based on test results"
```

### Diagnose → Fix → Verify Pattern

```
1. "Help diagnose the issue with [symptom]"
2. "Fix the issue in [specific_file]"
3. "Verify the fix works by running tests"
```

## Token-Saving Techniques

- **Use file references**: Refer to line numbers instead of pasting code
- **Focus queries**: Ask about specific sections rather than entire files
- **Use symbolic references**: Refer to components by name rather than implementation details
- **Prioritize batch operations**: Combine related operations in single requests
- **Prefer Glob/Grep over Agent**: Use targeted search tools when possible

## Common Workflows

### New Feature Implementation

```
1. "Let's implement [feature]. First, find related files"
2. "Plan the implementation of [feature]"
3. "Create necessary files for [feature]"
4. "Write tests for [feature]"
5. "Verify [feature] works correctly"
```

### Bug Fixing

```
1. "I'm seeing [error/issue]. Help diagnose the problem"
2. "Look at [error_context] to understand the issue"
3. "Fix the issue in [file]"
4. "Add tests to prevent regression"
5. "Verify the fix resolves the issue"
```

### Code Refactoring

```
1. "Let's refactor [component]. First, examine current implementation"
2. "Plan the refactoring approach"
3. "Implement refactoring in [file]"
4. "Ensure tests pass after refactoring"
5. "Verify refactoring improves [metric]"
```

### Performance Optimization

```
1. "Help identify performance bottlenecks in [module]"
2. "Analyze [specific_file] for performance issues"
3. "Optimize [function/method] for better performance"
4. "Add performance tests for [function/method]"
5. "Verify performance improvements"
```

## Special Scenarios

### Handling Large Files

```
"The file [filename] is large. First, give me a summary structure.
Then, let's focus specifically on [section/component]."
```

### Working Across Multiple Files

```
"We need to update the authentication flow across multiple files.
First, identify all files involved in authentication.
Then, let's make changes one file at a time."
```

### Implementing Complex Algorithms

```
"Let's implement [algorithm] step by step:
1. First, design the data structures needed
2. Next, outline the main algorithm steps
3. Then, implement each step in [filename]
4. Finally, add tests to verify correctness"
```

## Tracking Work Progress

Use these commands to manage ongoing work:

```
"Let's review our progress on [feature/task]"
"What steps remain for completing [feature/task]?"
"Update the todo list with our completed items"
```