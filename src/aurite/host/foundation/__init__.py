"""
Foundation layer for the Aurite MCP Host.
Provides security and resource boundary management.
"""

from .roots import RootConfig, RootManager
from .routing import MessageRouter
from .security import SecurityManager

__all__ = [
    "SecurityManager",
    "RootManager",
    "RootConfig",
    "MessageRouter",
]
