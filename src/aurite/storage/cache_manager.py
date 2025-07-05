"""
Provides a simple in-memory cache for conversation history.
"""

from typing import Any, Dict, List, Optional


class CacheManager:
    """
    A simple in-memory cache for storing conversation history for different sessions.
    This is used as a fallback when a persistent database is not enabled.
    """

    def __init__(self):
        self._history_cache: Dict[str, List[Dict[str, Any]]] = {}

    def get_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves the conversation history for a given session ID.

        Args:
            session_id: The unique identifier for the session.

        Returns:
            A list of message dictionaries, or None if no history is found.
        """
        return self._history_cache.get(session_id)

    def save_history(self, session_id: str, conversation: List[Dict[str, Any]]):
        """
        Saves or updates the conversation history for a given session ID.

        Args:
            session_id: The unique identifier for the session.
            conversation: The full list of message dictionaries to save.
        """
        self._history_cache[session_id] = conversation

    def clear_cache(self):
        """
        Clears all conversation histories from the cache.
        """
        self._history_cache.clear()
