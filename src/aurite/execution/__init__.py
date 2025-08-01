# src/execution/__init__.py
"""
Execution layer responsible for running agents and workflows via a unified engine.
"""

from .aurite_engine import AuriteEngine
from .mcp_host import MCPHost

__all__ = ["AuriteEngine", "MCPHost"]  # Explicitly define what 'from aurite.execution import *' imports
