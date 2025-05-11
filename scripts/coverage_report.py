#!/usr/bin/env python
"""
Script to analyze and report test coverage for the ML Orchestrator Service.

Usage:
    python coverage_report.py [--html] [--module <module_path>] [--threshold <percentage>]

Options:
    --html          Generate HTML coverage report
    --module        Analyze specific module (e.g., app.core.orchestrator)
    --threshold     Set coverage threshold percentage (default: 80)
    --missing       Show only modules below threshold
    --sort          Sort by coverage (asc or desc, default: asc)
"""

import os
import sys
import argparse
import subprocess
import json
import re
from typing import Dict, List, Tuple, Optional

# ANSI color codes for terminal output
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test coverage reporting tool")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage report")
    parser.add_argument("--module", type=str, help="Analyze specific module (e.g., app.core.orchestrator)")
    parser.add_argument("--threshold", type=int, default=80, help="Set coverage threshold percentage")
    parser.add_argument("--missing", action="store_true", help="Show only modules below threshold")
    parser.add_argument("--sort", type=str, choices=["asc", "desc"], default="asc", 
                        help="Sort by coverage (asc or desc)")
    return parser.parse_args()


def run_coverage(module: Optional[str] = None, html: bool = False) -> str:
    """Run pytest with coverage and return the output."""
    cmd = ["python", "-m", "pytest"]
    
    # Add module path if specified
    if module:
        module_path = module.replace(".", "/")
        module_parts = module.split(".")
        test_path = f"tests/test_{'s/' if len(module_parts) > 2 else ''}test_{module_parts[-1]}.py"
        
        if os.path.exists(test_path):
            cmd.append(test_path)
        else:
            print(f"{YELLOW}Warning: Test file {test_path} not found.{RESET}")
            print(f"{YELLOW}Running coverage on module without specific test file.{RESET}")
    
    # Add coverage options
    if module:
        cmd.extend(["--cov=" + module])
    else:
        cmd.extend(["--cov=app"])
    
    cmd.append("--cov-report=term-missing")
    
    if html:
        cmd.append("--cov-report=html")
    
    # Run the command
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout + result.stderr
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error running coverage: {e}{RESET}")
        sys.exit(1)


def parse_coverage_output(output: str) -> List[Tuple[str, float, str]]:
    """Parse the coverage output and return a list of tuples (module, coverage, missing)."""
    module_data = []
    
    # Find the coverage section in the output
    match = re.search(r"={10,}\s+coverage\s+={10,}(.*?)={10,}", output, re.DOTALL)
    if not match:
        print(f"{RED}Error: Could not find coverage section in output.{RESET}")
        return []
    
    coverage_section = match.group(1)
    
    # Parse each line
    for line in coverage_section.split("\n"):
        line = line.strip()
        if not line or "TOTAL" in line or "platform" in line or "coverage:" in line:
            continue
        
        # Expected format: Name                             Stmts   Miss  Cover   Missing
        parts = re.split(r'\s+', line, 3)
        if len(parts) >= 3:
            module_name = parts[0]
            try:
                stmts = int(parts[1])
                miss = int(parts[2])
                
                # Calculate coverage percentage
                coverage = 0 if stmts == 0 else round(100 * (stmts - miss) / stmts, 2)
                
                # Get missing lines if available
                missing = parts[3] if len(parts) > 3 else ""
                
                module_data.append((module_name, coverage, missing))
            except (ValueError, IndexError):
                continue
    
    return module_data


def print_coverage_report(module_data: List[Tuple[str, float, str]], 
                          threshold: int, 
                          missing_only: bool,
                          sort_order: str):
    """Print a formatted coverage report."""
    # Sort data
    if sort_order == "asc":
        module_data.sort(key=lambda x: x[1])
    else:
        module_data.sort(key=lambda x: x[1], reverse=True)
    
    # Calculate overall stats
    total_modules = len(module_data)
    modules_below_threshold = sum(1 for _, cov, _ in module_data if cov < threshold)
    perfect_modules = sum(1 for _, cov, _ in module_data if cov == 100)
    
    # Print header
    print(f"\n{CYAN}{'=' * 60}{RESET}")
    print(f"{CYAN}ML Orchestrator Service - Coverage Report{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}")
    
    # Print summary
    print(f"\n{BLUE}Summary:{RESET}")
    print(f"  Total modules analyzed: {total_modules}")
    print(f"  Modules below {threshold}% threshold: {modules_below_threshold}")
    print(f"  Modules with 100% coverage: {perfect_modules}")
    print(f"  Overall status: {GREEN if modules_below_threshold == 0 else YELLOW}{'PASS' if modules_below_threshold == 0 else 'NEEDS IMPROVEMENT'}{RESET}")
    
    # Print module details
    print(f"\n{BLUE}Module Coverage Details:{RESET}")
    print(f"  {'Module':<40} {'Coverage':<10} {'Status':<10}")
    print(f"  {'-' * 40} {'-' * 10} {'-' * 10}")
    
    for module, coverage, missing in module_data:
        if missing_only and coverage >= threshold:
            continue
            
        status_color = GREEN if coverage >= threshold else (YELLOW if coverage >= threshold * 0.8 else RED)
        status = "PASS" if coverage >= threshold else "NEEDS WORK"
        
        print(f"  {module:<40} {status_color}{coverage:>6.2f}%{RESET}  {status_color}{status}{RESET}")
    
    # Print modules that need most attention
    if modules_below_threshold > 0:
        print(f"\n{BLUE}Top Modules Needing Attention:{RESET}")
        for module, coverage, missing in sorted(module_data, key=lambda x: x[1])[:3]:
            if coverage < threshold:
                print(f"  {RED}{module:<40} {coverage:>6.2f}%{RESET}")
                if missing and "Missing" not in missing:
                    missing_lines = missing.split(',')
                    if len(missing_lines) > 5:
                        missing_display = ', '.join(missing_lines[:5]) + f"... ({len(missing_lines) - 5} more)"
                    else:
                        missing_display = missing
                    print(f"    Missing lines: {missing_display}")
    
    print(f"\n{CYAN}{'=' * 60}{RESET}")


def main():
    """Main function."""
    args = parse_args()
    
    print(f"{BLUE}Running test coverage analysis...{RESET}")
    output = run_coverage(args.module, args.html)
    
    module_data = parse_coverage_output(output)
    
    if not module_data:
        print(f"{RED}No coverage data found. Make sure tests are running correctly.{RESET}")
        sys.exit(1)
    
    print_coverage_report(module_data, args.threshold, args.missing, args.sort)
    
    if args.html:
        print(f"\n{GREEN}HTML coverage report generated in htmlcov/ directory.{RESET}")
        print(f"{GREEN}Open htmlcov/index.html in your browser to view the report.{RESET}")


if __name__ == "__main__":
    main()