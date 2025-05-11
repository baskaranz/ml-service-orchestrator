#!/usr/bin/env python3
"""
ML Orchestrator Dummy Model API Starter

This script starts all dummy model APIs defined in the config/models directory.
It reads each model's configuration and starts them as subprocesses.
"""

import os
import signal
import subprocess
import sys
import yaml
from pathlib import Path
from typing import List, Optional
import time

PROCESSES = []

def load_model_configs() -> dict:
    """Load all model configurations from the config/models directory."""
    models_dir = Path("config/models")
    if not models_dir.exists():
        print("Error: Models directory not found at", models_dir)
        sys.exit(1)
    
    models = {}
    for config_file in models_dir.glob("*.yaml"):
        with open(config_file) as f:
            config = yaml.safe_load(f)
            model_id = config.get("id")
            if model_id:
                models[model_id] = config
    
    return models

def start_models() -> List[subprocess.Popen]:
    """Start all models defined in the config/models directory."""
    models = load_model_configs()
    
    if not models:
        print("No models found in config/models directory")
        return []
    
    processes = []
    for i, (model_id, config) in enumerate(models.items()):
        if not config.get("enabled", True):
            print(f"Skipping disabled model: {model_id}")
            continue
        
        # Start the model as a subprocess
        port = 8000 + i + 1
        proc = subprocess.Popen([
            sys.executable, '-m', 'uvicorn',
            'app.dummy_models:create_model_api',
            '--host', 'localhost',
            '--port', str(port),
            '--factory',
            '--app-dir', '.'
        ])
        processes.append(proc)
        print(f"Started dummy model {i+1} on port {port} (PID: {proc.pid})")
    
    return processes

def cleanup(*_):
    print("\nStopping all dummy model servers...")
    for proc in PROCESSES:
        proc.terminate()
    for proc in PROCESSES:
        proc.wait()
    print("All dummy model servers stopped.")

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    """Main entry point."""
    print("Starting dummy model APIs...")
    processes = start_models()
    
    if not processes:
        print("No models were started")
        return
    
    print("\nAll models started. Press Ctrl+C to stop all models.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main() 