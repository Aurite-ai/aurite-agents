"""
Extension system for Aurite API.

Allows users to create custom API endpoints that integrate with Aurite.
Inspired by txtai's extension architecture.
"""

from . import application
from .discovery import ENTRY_POINT_GROUP, discover_entry_point_extensions, list_available_extensions
from .extension import Extension
from .factory import ExtensionFactory

__all__ = [
    "Extension",
    "ExtensionFactory",
    "application",
    "discover_entry_point_extensions",
    "list_available_extensions",
    "ENTRY_POINT_GROUP",
]
