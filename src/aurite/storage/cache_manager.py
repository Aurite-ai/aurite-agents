"""
Provides a file-based cache for execution results with in-memory caching.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """
    A file-based cache for storing execution results with in-memory caching.
    This provides persistence across restarts while maintaining fast access.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the cache manager with optional cache directory.

        Args:
            cache_dir: Directory to store cache files. Defaults to .aurite_cache
        """
        self._cache_dir = cache_dir or Path(".aurite_cache")
        logger.info(f"CacheManager initializing with cache_dir: {self._cache_dir.absolute()}")
        self._cache_dir.mkdir(exist_ok=True)
        # Store complete execution results instead of just conversations
        self._result_cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    def get_cache_dir(self) -> Path:
        """Get the cache directory path."""
        return self._cache_dir

    def _get_session_file(self, session_id: str) -> Path:
        """Get the file path for a session."""
        # Sanitize session_id to prevent directory traversal
        safe_session_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self._cache_dir / f"{safe_session_id}.json"

    def _load_cache(self):
        """Load all cached sessions from disk into memory."""
        try:
            for session_file in self._cache_dir.glob("*.json"):
                try:
                    with open(session_file, "r") as f:
                        data = json.load(f)
                        session_id = data.get("session_id")
                        if session_id:
                            # Store the complete execution result
                            self._result_cache[session_id] = data
                except Exception as e:
                    logger.warning(f"Failed to load session file {session_file}: {e}")
        except Exception as e:
            logger.error(f"Failed to load cache directory: {e}")

    def get_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the execution result for a given session ID.

        Args:
            session_id: The unique identifier for the session.

        Returns:
            The execution result dict (AgentRunResult or SimpleWorkflowExecutionResult), or None if not found.
        """
        # Check memory cache first
        if session_id in self._result_cache:
            return self._result_cache[session_id]

        # Try to load from disk if not in memory
        session_file = self._get_session_file(session_id)
        if session_file.exists():
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                self._result_cache[session_id] = data
                return data
            except Exception as e:
                logger.error(f"Failed to load session {session_id} from disk: {e}")

        return None

    def save_result(self, session_id: str, session_data: Dict[str, Any]):
        """
        Saves the complete execution result for a session.

        Args:
            session_id: The unique identifier for the session.
            execution_result: The complete execution result (AgentRunResult or SimpleWorkflowExecutionResult as dict).
            result_type: Type of result ("agent" or "workflow").
        """
        logger.info(f"CacheManager.save_result called for session_id: {session_id}")

        # Update memory cache
        self._result_cache[session_id] = session_data

        # Save to disk
        session_file = self._get_session_file(session_id)
        logger.info(f"Attempting to save to file: {session_file.absolute()}")
        try:
            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)
            logger.info(f"Successfully saved session {session_id} to disk at {session_file.absolute()}")
        except Exception as e:
            logger.error(f"Failed to save session {session_id} to disk: {e}", exc_info=True)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from cache and disk.

        Args:
            session_id: The session to delete.

        Returns:
            True if deleted successfully, False if session not found.
        """
        # Remove from memory
        session_exists_in_mem = self._result_cache.pop(session_id, None) is not None

        # Remove from disk
        session_file = self._get_session_file(session_id)
        try:
            session_exists_on_disk = session_file.exists()
            if session_exists_on_disk:
                session_file.unlink()
            return session_exists_in_mem or session_exists_on_disk
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def clear_cache(self):
        """
        Clears all execution results from memory cache only.
        Files on disk are preserved.
        """
        self._result_cache.clear()
