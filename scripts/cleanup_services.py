#!/usr/bin/env python3
"""
Cleanup script for removing Docker services and mock configurations.

This script performs the following cleanup tasks:
1. Stops and removes Docker containers for mock models
2. Removes unused Docker networks
3. Cleans up mock configuration YAML files from config/local
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None, check=False, capture_output=True, text=True
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def cleanup_docker_services() -> bool:
    """Stop and remove Docker containers and networks for mock services."""
    print("\n=== Cleaning up Docker services ===")

    # Stop and remove containers
    success, output = run_command(
        ["docker", "ps", "-a", "--filter", "name=mock-", "--format", "{{.Names}}"]
    )
    if not success:
        print(f"Error finding containers: {output}")
        return False

    containers = [c for c in output.split("\n") if c]

    if not containers:
        print("No mock containers found.")
    else:
        print(f"Found {len(containers)} containers to remove.")
        for container in containers:
            print(f"- Stopping {container}...")
            run_command(["docker", "stop", container])

            print(f"- Removing {container}...")
            run_command(["docker", "rm", container])

    # Remove unused networks
    success, output = run_command(
        ["docker", "network", "ls", "--filter", "name=mock", "--format", "{{.Name}}"]
    )
    if success and output:
        networks = output.split("\n")
        for network in networks:
            if network:
                print(f"- Removing network {network}...")
                run_command(["docker", "network", "rm", network])

    # Stop any running docker-compose services
    compose_files = [
        get_project_root() / "docker-compose.yml",
        get_project_root() / "docker-compose.fixed.yml",
        get_project_root() / "mocks" / "docker-compose.yml",
    ]

    for compose_file in compose_files:
        if compose_file.exists():
            print(f"\nStopping services from {compose_file}...")
            run_command(
                ["docker-compose", "-f", str(compose_file), "down", "--remove-orphans"],
                cwd=compose_file.parent,
            )

    return True


def cleanup_mock_configs() -> bool:
    """Remove mock configuration files."""
    print("\n=== Cleaning up mock configurations ===")
    config_dir = get_project_root() / "config" / "local" / "models"
    config_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    mock_files = list(config_dir.glob("mock-*.yaml"))

    if not mock_files:
        print("No mock configuration files found.")
        return True

    print(f"Found {len(mock_files)} mock configuration files:")
    for file in mock_files:
        print(f"  - {file.relative_to(get_project_root())}")

    success = True
    for file in mock_files:
        try:
            file.unlink()
            print(f"Deleted: {file.relative_to(get_project_root())}")
        except Exception as e:
            print(f"Error deleting {file}: {e}")
            success = False

    return success


def get_yes_no(prompt: str, default: str = "no") -> bool:
    """Prompt for yes/no input."""
    valid = {"yes": True, "y": True, "no": False, "n": False}
    if default is None:
        prompt_suffix = " [y/n] "
    elif default == "yes":
        prompt_suffix = " [Y/n] "
    elif default == "no":
        prompt_suffix = " [y/N] "
    else:
        raise ValueError("Invalid default answer: '%s'" % default)

    while True:
        choice = input(prompt + prompt_suffix).lower().strip()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').")


def main() -> int:
    """Main function to execute the cleanup process."""
    print("=== Service and Configuration Cleanup Tool ===")

    # Check if Docker is running
    print("Checking Docker...")
    docker_running, _ = run_command(["docker", "info"])
    if not docker_running:
        print("Docker is not running or not accessible. Some cleanup steps will be skipped.")

    # Perform cleanup tasks
    success = True

    if docker_running:
        success &= cleanup_docker_services()

    success &= cleanup_mock_configs()

    if success:
        print("\n✅ Cleanup completed successfully!")
    else:
        print("\n⚠️  Cleanup completed with some warnings or errors.", file=sys.stderr)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
