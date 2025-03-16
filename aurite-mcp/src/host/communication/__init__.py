"""
Communication layer for the Aurite MCP Host.
Manages transport channels and message routing.
"""

from .transport import TransportManager
from .routing import MessageRouter

__all__ = ["TransportManager", "MessageRouter"]
