"""
AI Coding Agent

A terminal-based AI coding agent that implements the Perceive → Reason → Act → Learn loop
for intelligent code interaction and development assistance.
"""

__version__ = "1.0.0"
__author__ = "AI Agent Developer"

from .core.agent import AICodeAgent
from .interface.terminal import TerminalInterface

__all__ = ["AICodeAgent", "TerminalInterface"]