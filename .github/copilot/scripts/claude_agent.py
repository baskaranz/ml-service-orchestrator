#!/usr/bin/env python3
"""
Claude Code Agent Interface

This script provides a simplified interface for creating and managing AI-agentic
workflows with Claude. It handles loading task descriptions, generating prompts,
and tracking progress.

Usage:
  python claude_agent.py [--task TASK_FILE] [--type TASK_TYPE] [--interactive]
"""

import argparse
import os
import sys
import yaml
import json
import subprocess
from pathlib import Path
from datetime import datetime

# ANSI colors for terminal output
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

# Project paths
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROMPTS_DIR = PROJECT_ROOT / "prompts"
TASKS_DIR = PROMPTS_DIR / "tasks"
EXAMPLES_DIR = PROMPTS_DIR / "examples"
SESSIONS_DIR = PROJECT_ROOT / ".claude_sessions"

# Ensure directories exist
TASKS_DIR.mkdir(exist_ok=True, parents=True)
SESSIONS_DIR.mkdir(exist_ok=True, parents=True)

# Task types
TASK_TYPES = [
    "feature",
    "bug",
    "refactor",
    "test",
    "analyze",
    "architecture",
    "optimize"
]

def load_task(task_file):
    """Load a task description from a YAML or JSON file."""
    if not os.path.exists(task_file):
        print(f"{RED}Error: Task file {task_file} not found{RESET}")
        return None
    
    try:
        with open(task_file, 'r') as f:
            if task_file.endswith('.yaml') or task_file.endswith('.yml'):
                task = yaml.safe_load(f)
            else:
                task = json.load(f)
        return task
    except Exception as e:
        print(f"{RED}Error loading task file: {e}{RESET}")
        return None

def generate_prompt(task_type, task_data):
    """Generate a prompt for the specified task type and data."""
    # Use the agentic_prompts.py script to generate the prompt
    script_path = PROJECT_ROOT / "scripts" / "agentic_prompts.py"
    
    # Create a temporary file with task data
    temp_file = TASKS_DIR / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    try:
        with open(temp_file, 'w') as f:
            yaml.dump(task_data, f)
        
        # Call the script to generate the prompt
        cmd = [sys.executable, str(script_path), task_type, "--json", str(temp_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"{RED}Error generating prompt:{RESET}")
            print(result.stderr)
            return None
        
        # Extract the prompt from the output
        output = result.stdout
        prompt_start = output.find("-" * 80) + 80
        prompt_end = output.rfind("-" * 80)
        if prompt_start >= 80 and prompt_end > prompt_start:
            prompt = output[prompt_start:prompt_end].strip()
            return prompt
        else:
            print(f"{RED}Error extracting prompt from output{RESET}")
            return None
    finally:
        # Clean up temporary file
        if temp_file.exists():
            temp_file.unlink()

def start_new_session(task_type, task_data):
    """Start a new Claude agent session with the given task."""
    # Generate the prompt
    prompt = generate_prompt(task_type, task_data)
    if not prompt:
        return False
    
    # Create a session directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"{task_type}_{timestamp}"
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    # Save the prompt and task data
    with open(session_dir / "prompt.txt", 'w') as f:
        f.write(prompt)
    
    with open(session_dir / "task.yaml", 'w') as f:
        yaml.dump(task_data, f)
    
    # Create a session info file
    session_info = {
        "id": session_id,
        "type": task_type,
        "created_at": timestamp,
        "status": "created",
        "progress": 0
    }
    
    with open(session_dir / "session.json", 'w') as f:
        json.dump(session_info, f, indent=2)
    
    print(f"{GREEN}Created new session: {session_id}{RESET}")
    print(f"{BLUE}Session directory: {session_dir}{RESET}")
    print(f"{YELLOW}Next steps:{RESET}")
    print(f"1. Use the prompt in {session_dir / 'prompt.txt'} with Claude Code")
    print(f"2. Track progress in {session_dir}")
    
    # Try to copy to clipboard
    try:
        import pyperclip
        pyperclip.copy(prompt)
        print(f"{GREEN}Prompt copied to clipboard!{RESET}")
        
        # Try to open Claude Code directly if on macOS
        if sys.platform == 'darwin':
            try:
                subprocess.run(["open", "-a", "Terminal", "claude-code"], check=False)
                print(f"{GREEN}Launching Claude Code...{RESET}")
            except Exception:
                pass
    except (ImportError, ModuleNotFoundError):
        pass
    
    return True

def list_example_tasks():
    """List available example tasks."""
    examples = []
    for file in EXAMPLES_DIR.glob("*.yaml"):
        task_type = file.stem.split('_')[0]
        task_name = file.stem.split('_', 1)[1] if '_' in file.stem else file.stem
        examples.append((task_type, task_name, file))
    
    if not examples:
        print(f"{YELLOW}No example tasks found in {EXAMPLES_DIR}{RESET}")
        return None
    
    print(f"{BLUE}Available example tasks:{RESET}")
    for i, (task_type, task_name, file) in enumerate(sorted(examples), 1):
        print(f"{i}. {YELLOW}{task_type.title()}{RESET}: {task_name.replace('_', ' ').title()} ({file.name})")
    
    return examples

def list_sessions():
    """List existing Claude agent sessions."""
    sessions = []
    for session_dir in SESSIONS_DIR.glob("*"):
        if not session_dir.is_dir():
            continue
        
        session_file = session_dir / "session.json"
        if not session_file.exists():
            continue
        
        try:
            with open(session_file, 'r') as f:
                session_info = json.load(f)
            sessions.append((session_info, session_dir))
        except Exception:
            continue
    
    if not sessions:
        print(f"{YELLOW}No sessions found{RESET}")
        return None
    
    print(f"{BLUE}Existing sessions:{RESET}")
    for i, (info, path) in enumerate(sorted(sessions, key=lambda x: x[0].get('created_at', ''), reverse=True), 1):
        status = info.get('status', 'unknown')
        progress = info.get('progress', 0)
        created = info.get('created_at', 'unknown')
        task_type = info.get('type', 'unknown')
        
        status_color = GREEN if status == 'completed' else (YELLOW if status == 'in_progress' else CYAN)
        
        print(f"{i}. {YELLOW}{task_type.title()}{RESET} - {status_color}{status.title()}{RESET} ({progress}%) - Created: {created}")
    
    return sessions

def create_task_interactively():
    """Create a task description interactively."""
    print(f"{BLUE}Create a new task description interactively{RESET}")
    
    # Select task type
    print(f"{YELLOW}Available task types:{RESET}")
    for i, task_type in enumerate(TASK_TYPES, 1):
        print(f"{i}. {task_type.title()}")
    
    while True:
        try:
            choice = int(input(f"\n{YELLOW}Select task type (1-{len(TASK_TYPES)}): {RESET}"))
            if 1 <= choice <= len(TASK_TYPES):
                task_type = TASK_TYPES[choice - 1]
                break
            else:
                print(f"{RED}Invalid choice. Please enter a number between 1 and {len(TASK_TYPES)}.{RESET}")
        except ValueError:
            print(f"{RED}Invalid input. Please enter a number.{RESET}")
    
    # Get the required fields from the agentic_prompts.py script
    script_path = PROJECT_ROOT / "scripts" / "agentic_prompts.py"
    cmd = [sys.executable, str(script_path), "--params", task_type]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"{RED}Error getting task parameters:{RESET}")
        print(result.stderr)
        return None, None
    
    # Parse the output to get the parameters
    output = result.stdout
    params_start = output.find("Parameters for")
    if params_start < 0:
        print(f"{RED}Error parsing parameters from output{RESET}")
        return None, None
    
    params = []
    for line in output[params_start:].split('\n'):
        if line.strip() and line.strip().startswith(' '):
            param = line.strip().split()[-1]
            if param != "project_name":  # Skip the auto-filled parameter
                params.append(param)
    
    # Get values for each parameter
    task_data = {}
    for param in params:
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
            task_data[param] = "\n".join(lines)
        else:
            task_data[param] = input(f"{YELLOW}{display_name}:{RESET} ")
    
    # Save the task
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_name = input(f"{YELLOW}Enter a name for this task (no spaces): {RESET}")
    if not task_name:
        task_name = f"{task_type}_{timestamp}"
    else:
        task_name = f"{task_type}_{task_name}"
    
    task_file = TASKS_DIR / f"{task_name}.yaml"
    with open(task_file, 'w') as f:
        yaml.dump(task_data, f)
    
    print(f"{GREEN}Task saved to: {task_file}{RESET}")
    return task_type, task_data

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Claude Code Agent Interface")
    parser.add_argument("--task", help="Path to task definition file (YAML or JSON)")
    parser.add_argument("--type", choices=TASK_TYPES, help="Task type")
    parser.add_argument("--interactive", action="store_true", help="Create task interactively")
    parser.add_argument("--list-examples", action="store_true", help="List example tasks")
    parser.add_argument("--list-sessions", action="store_true", help="List existing sessions")
    parser.add_argument("--example", type=int, help="Use the specified example task")
    
    args = parser.parse_args()
    
    # List examples and exit
    if args.list_examples:
        list_example_tasks()
        return 0
    
    # List sessions and exit
    if args.list_sessions:
        list_sessions()
        return 0
    
    # Use the specified example
    if args.example is not None:
        examples = list_example_tasks()
        if not examples:
            return 1
        
        if 1 <= args.example <= len(examples):
            task_type, _, file = examples[args.example - 1]
            task_data = load_task(file)
            if not task_data:
                return 1
            
            return 0 if start_new_session(task_type, task_data) else 1
        else:
            print(f"{RED}Invalid example number. Please choose between 1 and {len(examples)}.{RESET}")
            return 1
    
    # Interactive task creation
    if args.interactive:
        task_type, task_data = create_task_interactively()
        if not task_type or not task_data:
            return 1
        
        return 0 if start_new_session(task_type, task_data) else 1
    
    # Use the specified task file
    if args.task:
        task_data = load_task(args.task)
        if not task_data:
            return 1
        
        task_type = args.type
        if not task_type:
            # Try to infer from filename
            filename = os.path.basename(args.task)
            for t in TASK_TYPES:
                if filename.startswith(f"{t}_") or t in filename.lower():
                    task_type = t
                    break
            
            if not task_type:
                print(f"{RED}Error: Task type not specified and could not be inferred from filename{RESET}")
                print(f"{YELLOW}Please specify a task type with --type{RESET}")
                return 1
        
        return 0 if start_new_session(task_type, task_data) else 1
    
    # If no action specified, show interactive menu
    print(f"{BLUE}Claude Code Agent Interface{RESET}")
    print(f"{CYAN}{'-'*40}{RESET}")
    print(f"{YELLOW}1. Create a new task interactively{RESET}")
    print(f"{YELLOW}2. Use an example task{RESET}")
    print(f"{YELLOW}3. View existing sessions{RESET}")
    print(f"{YELLOW}4. Exit{RESET}")
    
    try:
        choice = int(input(f"\n{YELLOW}Select an option (1-4): {RESET}"))
        if choice == 1:
            task_type, task_data = create_task_interactively()
            if task_type and task_data:
                start_new_session(task_type, task_data)
        elif choice == 2:
            examples = list_example_tasks()
            if examples:
                example_choice = int(input(f"\n{YELLOW}Select an example (1-{len(examples)}): {RESET}"))
                if 1 <= example_choice <= len(examples):
                    task_type, _, file = examples[example_choice - 1]
                    task_data = load_task(file)
                    if task_data:
                        start_new_session(task_type, task_data)
        elif choice == 3:
            list_sessions()
        elif choice == 4:
            print(f"{GREEN}Goodbye!{RESET}")
            return 0
        else:
            print(f"{RED}Invalid choice{RESET}")
            return 1
    except ValueError:
        print(f"{RED}Invalid input{RESET}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())