#!/usr/bin/env python
"""
ML Orchestrator Development CLI

A command-line utility for common development tasks.

Usage:
    python scripts/dev_cli.py <command> [options]

Commands:
    run              Run the application
    test             Run tests
    coverage         Run tests with coverage
    lint             Run linting tools
    format           Format code
    clean            Clean up build artifacts
    gen-model        Generate a new model configuration
    gen-test         Generate test file skeleton
    check-deps       Check for outdated dependencies
    docker           Build and run with Docker
"""

import argparse
import os
import subprocess
import sys
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# ANSI colors for terminal output
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

# Project path
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = PROJECT_ROOT / "app"
TESTS_DIR = PROJECT_ROOT / "tests"
CONFIG_DIR = PROJECT_ROOT / "config"


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> int:
    """Run a command and return the exit code."""
    try:
        return subprocess.run(cmd, cwd=cwd).returncode
    except Exception as e:
        print(f"{RED}Error running command: {e}{RESET}")
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Run the application."""
    print(f"{BLUE}Running ML Orchestrator...{RESET}")
    cmd = [
        "uvicorn",
        "app.main:app",
        "--reload",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--log-level",
        args.log_level,
    ]
    
    if args.debug:
        print(f"{YELLOW}Debug mode enabled{RESET}")
        os.environ["DEBUG"] = "True"
    
    return run_command(cmd)


def cmd_test(args: argparse.Namespace) -> int:
    """Run tests."""
    print(f"{BLUE}Running tests...{RESET}")
    cmd = ["pytest"]
    
    if args.verbose:
        cmd.append("-v")
    
    if args.watch:
        cmd = ["ptw", "--", *cmd]
    
    if args.module:
        module_path = args.module.replace(".", "/")
        if os.path.exists(f"{TESTS_DIR}/test_{module_path}.py"):
            cmd.append(f"{TESTS_DIR}/test_{module_path}.py")
        else:
            cmd.append(f"{TESTS_DIR}/test_{os.path.dirname(module_path)}/test_{os.path.basename(module_path)}.py")
    
    if args.pattern:
        cmd.extend(["-k", args.pattern])
    
    return run_command(cmd)


def cmd_coverage(args: argparse.Namespace) -> int:
    """Run tests with coverage."""
    print(f"{BLUE}Running tests with coverage...{RESET}")
    cmd = ["pytest", "--cov=app"]
    
    if args.report:
        cmd.append(f"--cov-report={args.report}")
    else:
        cmd.append("--cov-report=term-missing")
    
    if args.fail_under:
        cmd.append(f"--cov-fail-under={args.fail_under}")
    
    if args.module:
        if "." in args.module:
            module_parts = args.module.split(".")
            cmd.extend([f"--cov=app.{args.module}", f"tests/test_{module_parts[0]}/test_{module_parts[-1]}.py"])
        else:
            cmd.extend([f"--cov=app.{args.module}", f"tests/test_{args.module}"])
    
    return run_command(cmd)


def cmd_lint(args: argparse.Namespace) -> int:
    """Run linting tools."""
    print(f"{BLUE}Running linters...{RESET}")
    
    paths = ["app", "tests"]
    if args.path:
        paths = [args.path]
    
    if args.tool == "ruff" or args.tool == "all":
        print(f"{CYAN}Running ruff...{RESET}")
        if run_command(["ruff", "check", *paths]) != 0:
            return 1
    
    if args.tool == "black" or args.tool == "all":
        print(f"{CYAN}Running black...{RESET}")
        if run_command(["black", "--check", *paths]) != 0:
            return 1
    
    if args.tool == "mypy" or args.tool == "all":
        print(f"{CYAN}Running mypy...{RESET}")
        if run_command(["mypy", "app"]) != 0:
            return 1
    
    return 0


def cmd_format(args: argparse.Namespace) -> int:
    """Format code."""
    print(f"{BLUE}Formatting code...{RESET}")
    
    paths = ["app", "tests"]
    if args.path:
        paths = [args.path]
    
    if run_command(["black", *paths]) != 0:
        return 1
    
    if run_command(["ruff", "check", "--fix", *paths]) != 0:
        return 1
    
    print(f"{GREEN}Code formatting complete!{RESET}")
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    """Clean up build artifacts."""
    print(f"{BLUE}Cleaning up build artifacts...{RESET}")
    
    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        ".pytest_cache",
        "htmlcov",
        ".coverage",
        "build",
        "dist",
        "*.egg-info",
    ]
    
    for pattern in patterns:
        for path in PROJECT_ROOT.glob(pattern):
            if path.is_dir():
                print(f"Removing directory: {path}")
                run_command(["rm", "-rf", str(path)])
            else:
                print(f"Removing file: {path}")
                path.unlink()
    
    print(f"{GREEN}Cleanup complete!{RESET}")
    return 0


def cmd_gen_model(args: argparse.Namespace) -> int:
    """Generate a new model configuration."""
    print(f"{BLUE}Generating model configuration for {args.model_id}...{RESET}")
    
    models_dir = CONFIG_DIR / "models"
    models_dir.mkdir(exist_ok=True, parents=True)
    
    model_file = models_dir / f"{args.model_id}.yaml"
    
    if model_file.exists() and not args.force:
        print(f"{RED}Model configuration already exists. Use --force to overwrite.{RESET}")
        return 1
    
    model_config = {
        "id": args.model_id,
        "name": args.name or f"{args.model_id.replace('_', ' ').title()}",
        "description": args.description or f"Configuration for {args.model_id}",
        "endpoint_url": args.endpoint or f"http://localhost:8888/{args.model_id}",
        "version": "1.0.0",
        "timeout": args.timeout,
        "max_retries": args.retries,
        "circuit_breaker": {
            "failure_threshold": args.threshold,
            "reset_timeout": args.reset_timeout,
        },
        "auth": {
            "type": args.auth_type,
            "key_name": "X-API-Key" if args.auth_type == "api_key" else None,
            "key_value": args.auth_key,
            "location": "header" if args.auth_type == "api_key" else None,
        },
        "cache": {
            "enabled": args.cache,
            "ttl": args.cache_ttl,
            "max_size": args.cache_size,
        },
        "headers": {"X-Source": "ml-orchestrator"},
        "active": True,
    }
    
    # Remove None values
    model_config = {k: v for k, v in model_config.items() if v is not None}
    model_config["auth"] = {k: v for k, v in model_config["auth"].items() if v is not None}
    
    with open(model_file, "w") as f:
        yaml.dump(model_config, f, default_flow_style=False)
    
    # Update models registry
    registry_file = CONFIG_DIR / "models_registry.yaml"
    if registry_file.exists():
        with open(registry_file, "r") as f:
            registry = yaml.safe_load(f) or {}
    else:
        registry = {"version": "1.0", "models": []}
    
    # Check if model already exists in registry
    model_exists = False
    for model in registry.get("models", []):
        if model.get("id") == args.model_id:
            model_exists = True
            model["file"] = f"models/{args.model_id}.yaml"
    
    if not model_exists:
        registry.setdefault("models", []).append(
            {"id": args.model_id, "file": f"models/{args.model_id}.yaml"}
        )
    
    with open(registry_file, "w") as f:
        yaml.dump(registry, f, default_flow_style=False)
    
    print(f"{GREEN}Model configuration created: {model_file}{RESET}")
    print(f"{GREEN}Registry updated: {registry_file}{RESET}")
    return 0


def cmd_gen_test(args: argparse.Namespace) -> int:
    """Generate a test file skeleton."""
    print(f"{BLUE}Generating test file skeleton for {args.module}...{RESET}")
    
    # Determine module path and file
    module_parts = args.module.split(".")
    module_path = "/".join(module_parts)
    
    if len(module_parts) == 1:
        # Top-level module
        src_file = APP_DIR / f"{module_parts[0]}.py"
        test_dir = TESTS_DIR
        test_file = test_dir / f"test_{module_parts[0]}.py"
    else:
        # Sub-module
        src_file = APP_DIR / f"{module_path}.py"
        test_dir = TESTS_DIR / f"test_{module_parts[0]}"
        test_file = test_dir / f"test_{module_parts[-1]}.py"
    
    # Create test directory if needed
    test_dir.mkdir(exist_ok=True, parents=True)
    
    if test_file.exists() and not args.force:
        print(f"{RED}Test file already exists. Use --force to overwrite.{RESET}")
        return 1
    
    # Create basic test file content
    test_content = f'''"""
Tests for the {args.module} module.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.{module_path} import *

'''
    
    # Add async fixture if needed
    if args.async_test:
        test_content += '''
@pytest.fixture
async def async_fixture():
    """Async fixture for testing."""
    # Setup code
    yield "test_value"
    # Teardown code

'''
    
    # Add basic test function
    if args.async_test:
        test_content += '''
@pytest.mark.asyncio
async def test_example_async():
    """Test example async function."""
    # Setup
    expected = "expected_value"
    
    # Execute
    result = await example_async_function()
    
    # Assert
    assert result == expected
'''
    else:
        test_content += '''
def test_example():
    """Test example function."""
    # Setup
    expected = "expected_value"
    
    # Execute
    result = example_function()
    
    # Assert
    assert result == expected
'''
    
    # Create a class test if needed
    if args.class_test:
        class_name = "".join(word.capitalize() for word in args.class_test.split("_"))
        test_content += f'''

class Test{class_name}:
    """Tests for the {args.class_test} class."""
    
    @pytest.fixture
    def {args.class_test}(self):
        """Create a {args.class_test} instance for testing."""
        return {class_name}()
    
    def test_init(self, {args.class_test}):
        """Test initialization."""
        assert {args.class_test} is not None
    
    def test_method(self, {args.class_test}):
        """Test a method of the class."""
        expected = "expected_value"
        result = {args.class_test}.method()
        assert result == expected
'''
    
    # Write the test file
    with open(test_file, "w") as f:
        f.write(test_content)
    
    print(f"{GREEN}Test file created: {test_file}{RESET}")
    return 0


def cmd_check_deps(args: argparse.Namespace) -> int:
    """Check for outdated dependencies."""
    print(f"{BLUE}Checking for outdated dependencies...{RESET}")
    return run_command(["pip", "list", "--outdated"])


def cmd_docker(args: argparse.Namespace) -> int:
    """Build and run with Docker."""
    if args.action == "build":
        print(f"{BLUE}Building Docker image...{RESET}")
        return run_command(["docker", "build", "-t", "ml-orchestrator:latest", "."])
    elif args.action == "run":
        print(f"{BLUE}Running Docker container...{RESET}")
        return run_command([
            "docker", "run", 
            "-p", f"{args.port}:8000", 
            "--name", args.name,
            "-d" if args.detach else "-it",
            "ml-orchestrator:latest"
        ])
    elif args.action == "stop":
        print(f"{BLUE}Stopping Docker container...{RESET}")
        return run_command(["docker", "stop", args.name])
    elif args.action == "logs":
        print(f"{BLUE}Showing Docker container logs...{RESET}")
        return run_command(["docker", "logs", "-f", args.name])
    else:
        print(f"{RED}Unknown Docker action: {args.action}{RESET}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="ML Orchestrator Development CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the application")
    run_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    run_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    run_parser.add_argument("--log-level", default="info", help="Log level")
    run_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    test_parser.add_argument("-w", "--watch", action="store_true", help="Watch for changes")
    test_parser.add_argument("-m", "--module", help="Test specific module")
    test_parser.add_argument("-k", "--pattern", help="Only run tests matching pattern")
    
    # Coverage command
    coverage_parser = subparsers.add_parser("coverage", help="Run tests with coverage")
    coverage_parser.add_argument("--report", choices=["term", "term-missing", "html", "xml"], help="Coverage report type")
    coverage_parser.add_argument("--fail-under", type=int, help="Fail if coverage is under threshold")
    coverage_parser.add_argument("-m", "--module", help="Test specific module")
    
    # Lint command
    lint_parser = subparsers.add_parser("lint", help="Run linting tools")
    lint_parser.add_argument("--tool", choices=["ruff", "black", "mypy", "all"], default="all", help="Linting tool to run")
    lint_parser.add_argument("--path", help="Path to lint")
    
    # Format command
    format_parser = subparsers.add_parser("format", help="Format code")
    format_parser.add_argument("--path", help="Path to format")
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean up build artifacts")
    
    # Generate model command
    gen_model_parser = subparsers.add_parser("gen-model", help="Generate a new model configuration")
    gen_model_parser.add_argument("model_id", help="Model ID (e.g., gpt_4)")
    gen_model_parser.add_argument("--name", help="Model name")
    gen_model_parser.add_argument("--description", help="Model description")
    gen_model_parser.add_argument("--endpoint", help="Model endpoint URL")
    gen_model_parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout")
    gen_model_parser.add_argument("--retries", type=int, default=3, help="Maximum retries")
    gen_model_parser.add_argument("--threshold", type=int, default=5, help="Circuit breaker failure threshold")
    gen_model_parser.add_argument("--reset-timeout", type=float, default=30.0, help="Circuit breaker reset timeout")
    gen_model_parser.add_argument("--auth-type", choices=["api_key", "bearer_token", "none"], default="api_key", help="Authentication type")
    gen_model_parser.add_argument("--auth-key", default="dev_model_key", help="Authentication key")
    gen_model_parser.add_argument("--cache", action="store_true", help="Enable response caching")
    gen_model_parser.add_argument("--cache-ttl", type=int, default=300, help="Cache TTL in seconds")
    gen_model_parser.add_argument("--cache-size", type=int, default=100, help="Cache max size")
    gen_model_parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing model configuration")
    
    # Generate test command
    gen_test_parser = subparsers.add_parser("gen-test", help="Generate test file skeleton")
    gen_test_parser.add_argument("module", help="Module to test (e.g., core.models)")
    gen_test_parser.add_argument("--async-test", action="store_true", help="Generate async test")
    gen_test_parser.add_argument("--class-test", help="Add test class for a specific class")
    gen_test_parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing test file")
    
    # Check dependencies command
    check_deps_parser = subparsers.add_parser("check-deps", help="Check for outdated dependencies")
    
    # Docker command
    docker_parser = subparsers.add_parser("docker", help="Build and run with Docker")
    docker_parser.add_argument("action", choices=["build", "run", "stop", "logs"], help="Docker action")
    docker_parser.add_argument("--name", default="ml-orchestrator", help="Container name")
    docker_parser.add_argument("--port", type=int, default=8000, help="Host port to bind to")
    docker_parser.add_argument("-d", "--detach", action="store_true", help="Run container in detached mode")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Call the appropriate command function
    cmd_func = globals().get(f"cmd_{args.command.replace('-', '_')}")
    if cmd_func:
        return cmd_func(args)
    else:
        print(f"{RED}Unknown command: {args.command}{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())