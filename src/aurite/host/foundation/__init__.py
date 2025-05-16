"""
Foundation layer for the Aurite MCP Host.
Provides security and resource boundary management.
"""

from .security import SecurityManager
from .roots import RootManager, RootConfig
from .routing import MessageRouter
from .clients import ClientManager  # Added import

__all__ = [
    "SecurityManager",
    "RootManager",
    "RootConfig",
    "MessageRouter",
    "ClientManager",
]  # Added ClientManager
