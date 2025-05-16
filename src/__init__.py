"""
Initialization for the src package (aurite).
Exposes key public interfaces.
"""

from .host_manager import Aurite
from .agents.agent import Agent

__all__ = ["Aurite", "Agent"]
