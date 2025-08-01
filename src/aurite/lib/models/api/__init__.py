"""
API Models

Simple approach: Import everything from submodules and let Python handle the rest.
"""

# Import all models from submodules
from .requests import *
from .responses import *
from .server import *

# Python will automatically populate __all__ from the imported modules
