from ...lib.models.api.server import ServerConfig
from .api import app, start

# For backwards compatibility and convenience, also export Extension at top level
# However, users should prefer importing from .extension to avoid circular imports
from .extension import (
    Extension,
    ExtensionFactory,
    application,
    discover_entry_point_extensions,
    list_available_extensions,
)

__all__ = [
    "app",
    "start",
    "ServerConfig",
    "Extension",
    "ExtensionFactory",
    "application",
    "discover_entry_point_extensions",
    "list_available_extensions",
]
