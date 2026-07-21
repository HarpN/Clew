"""
agent.py - Root entry point forwarding to agent/agent.py
"""

import os
import sys

# Ensure agent directory is in path and execute agent/agent.py
from agent.agent import WorkerOptions, entrypoint
from livekit.agents import cli

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
