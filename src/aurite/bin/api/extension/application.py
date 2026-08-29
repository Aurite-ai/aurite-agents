"""
Application state management for accessing Aurite instance from extensions.
"""

from typing import Optional

from ....aurite import Aurite

# Global application state
_aurite_instance: Optional[Aurite] = None


def set(aurite: Aurite) -> None:
    """
    Set the global Aurite instance.

    Called by the FastAPI lifespan to make Aurite accessible to extensions.

    Args:
        aurite: The initialized Aurite instance
    """
    global _aurite_instance
    _aurite_instance = aurite


def get() -> Aurite:
    """
    Get the global Aurite instance.

    Returns:
        The initialized Aurite instance

    Raises:
        RuntimeError: If called before Aurite is initialized
    """
    if _aurite_instance is None:
        raise RuntimeError(
            "Aurite instance not initialized. This function should only be called after the API has started."
        )
    return _aurite_instance


__all__ = ["get", "set"]
