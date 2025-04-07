"""
Communication layer for the Aurite MCP Host.
Manages message routing.
"""

# Removed TransportManager import
from .routing import MessageRouter

__all__ = ["MessageRouter"]
