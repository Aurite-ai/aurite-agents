"""
Extension discovery system for Aurite API.

Discovers extensions from:
1. Poetry entry points (installed packages)
2. Environment variables (manual/local)
"""

import logging
from importlib.metadata import entry_points
from typing import Dict, List, Type

from .extension import Extension

logger = logging.getLogger(__name__)

# Entry point group name for Aurite API extensions
ENTRY_POINT_GROUP = "aurite.api.extension"


def discover_entry_point_extensions() -> Dict[str, Type[Extension]]:
    """
    Discover extensions registered via Poetry entry points.

    Extensions should be registered in pyproject.toml like:
    ```toml
    [project.entry-points."aurite.api.extension"]
    my-extension = "my_package.extensions:MyExtension"
    ```

    Returns:
        Dictionary mapping extension names to Extension classes
    """
    discovered: Dict[str, Type[Extension]] = {}

    try:
        # Get all entry points in the aurite.api.extension group
        # Handle both old and new importlib.metadata APIs
        try:
            # Python 3.10+ API: entry_points(group=...) returns filtered EntryPoints
            extension_eps = entry_points(group=ENTRY_POINT_GROUP)
        except TypeError:
            # Python 3.9 and earlier: entry_points() returns SelectableGroups (dict-like)
            all_eps = entry_points()
            # Access as dictionary
            extension_eps = all_eps[ENTRY_POINT_GROUP] if ENTRY_POINT_GROUP in all_eps else []

        # Iterate through discovered entry points
        for ep in extension_eps:
            try:
                # Ensure we have an EntryPoint object (handle different API versions)
                if not hasattr(ep, "load"):
                    logger.warning(f"Invalid entry point object: {ep}")
                    continue

                # Get entry point name
                ep_name = getattr(ep, "name", str(ep))

                # Load the extension class
                extension_class = ep.load()  # type: ignore[attr-defined]

                # Verify it's an Extension subclass
                if not isinstance(extension_class, type) or not issubclass(extension_class, Extension):
                    logger.warning(f"Entry point '{ep_name}' does not point to an Extension subclass, skipping")
                    continue

                discovered[ep_name] = extension_class
                logger.debug(f"Discovered extension '{ep_name}' from entry point")

            except Exception as e:
                ep_name = getattr(ep, "name", str(ep))
                logger.error(f"Failed to load extension from entry point '{ep_name}': {e}", exc_info=True)
                continue

        if discovered:
            logger.info(f"Discovered {len(discovered)} extension(s) from entry points: {list(discovered.keys())}")
        else:
            logger.debug(f"No extensions found in entry point group '{ENTRY_POINT_GROUP}'")

    except Exception as e:
        logger.error(f"Error discovering entry point extensions: {e}", exc_info=True)

    return discovered


def list_available_extensions() -> List[str]:
    """
    List all available extensions (from entry points).

    Returns:
        List of extension names
    """
    extensions = discover_entry_point_extensions()
    return sorted(extensions.keys())


__all__ = [
    "discover_entry_point_extensions",
    "list_available_extensions",
    "ENTRY_POINT_GROUP",
]
