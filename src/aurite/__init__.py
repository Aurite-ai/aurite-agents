"""
Aurite Framework
================

This is the main package for the Aurite framework.
It exposes the core classes and functions for users to build and run AI agents.
"""

# Core classes for users
from .aurite import Aurite
from .bin.api.extension import Extension  # For convenience
from .execution.aurite_engine import AuriteEngine

# Import the models module as 'types' for convenient access
from .lib import models as types

# Import all models for backward compatibility
from .lib.models import *

__all__ = [
    "Extension",
    "Aurite",
    "AuriteEngine",
    "types",
    # All model classes are automatically available via the import above
]

__version__ = "0.2.0"  # Keep in sync with pyproject.toml
