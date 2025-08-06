"""
Aurite Studio module for integrated development experience.

This module provides the `aurite studio` command that starts both the API server
and React frontend concurrently with unified logging and graceful shutdown.
"""

from .studio import start_studio

__all__ = ["start_studio"]
