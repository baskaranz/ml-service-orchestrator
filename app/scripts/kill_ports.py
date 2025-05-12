#!/usr/bin/env python3
"""Script to kill processes using specific ports."""

import os
import signal
import subprocess
from typing import List

def get_pid_using_port(port: int) -> List[int]:
    """Get PIDs of processes using the specified port."""
    try:
        # For macOS
        cmd = f"lsof -i :{port} -t"
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        if output:
            return [int(pid) for pid in output.split('\n') if pid]
    except subprocess.CalledProcessError:
        pass
    return []

def kill_processes(ports: List[int]) -> None:
    """Kill processes using the specified ports."""
    for port in ports:
        pids = get_pid_using_port(port)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Killed process {pid} using port {port}")
            except ProcessLookupError:
                print(f"Process {pid} already terminated")
            except PermissionError:
                print(f"Permission denied to kill process {pid}")

if __name__ == "__main__":
    # Ports used by the application
    ports = [8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010, 9090]
    kill_processes(ports) 