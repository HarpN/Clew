"""
agent.py - Root entry point forwarding to agent/agent.py
"""

import os
import sys

# Ensure agent directory is in path and execute agent/agent.py
from agent.agent import JobProcess, WorkerOptions, entrypoint

if __name__ == "__main__":
    JobProcess.run(WorkerOptions(entrypoint_fnc=entrypoint))
