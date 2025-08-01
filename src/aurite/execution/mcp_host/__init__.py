"""
Initialization for the MCP Host package.
Exposes key classes for easier import.
"""

from .aurite_engine import AuriteEngine
from .mcp_host import MCPHost

__all__ = ["MCPHost", "AuriteEngine"]  # Explicitly define what 'from aurite.execution.mcp_host import *' imports
