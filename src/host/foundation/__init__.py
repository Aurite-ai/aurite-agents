"""
Foundation layer for the Aurite MCP Host.
Provides security and resource boundary management.
"""

from .security import SecurityManager
from .roots import RootManager, RootConfig

__all__ = ["SecurityManager", "RootManager", "RootConfig"]
