"""
Extension system for Aurite API.

Allows users to create custom API endpoints that integrate with Aurite.
Inspired by txtai's extension architecture.
"""

from . import application
from .extension import Extension
from .factory import ExtensionFactory

__all__ = [
    "Extension",
    "ExtensionFactory",
    "application",
]
