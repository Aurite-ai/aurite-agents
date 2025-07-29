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
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

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
                            # Metadata is now handled by SessionManager
                            self._metadata_cache[session_id] = data
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
                self._metadata_cache[session_id] = data
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
        self._metadata_cache[session_id] = session_data

        # Save to disk
        session_file = self._get_session_file(session_id)
        logger.info(f"Attempting to save to file: {session_file.absolute()}")
        try:
            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)
            logger.info(f"Successfully saved session {session_id} to disk at {session_file.absolute()}")
        except Exception as e:
            logger.error(f"Failed to save session {session_id} to disk: {e}", exc_info=True)

    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a session.

        Args:
            session_id: The session identifier.

        Returns:
            Metadata dict with created_at, last_updated, result_type, session_id
        """
        return self.get_result(session_id)

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all sessions from the cache.
        """
        return list(self._metadata_cache.values())

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from cache and disk.

        Args:
            session_id: The session to delete.

        Returns:
            True if deleted successfully, False if session not found.
        """
        # Check if session exists
        session_exists = session_id in self._metadata_cache

        # Remove from memory
        self._result_cache.pop(session_id, None)
        self._metadata_cache.pop(session_id, None)

        # Remove from disk
        session_file = self._get_session_file(session_id)
        try:
            if session_file.exists():
                session_file.unlink()
                return True
            # If not in memory and not on disk, session doesn't exist
            return session_exists
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def clear_cache(self):
        """
        Clears all execution results from memory cache only.
        Files on disk are preserved.
        """
        self._result_cache.clear()
        self._metadata_cache.clear()

    def cleanup_old_sessions(self, days: int = 30, max_sessions: int = 50):
        """
        Clean up old sessions based on retention policy.
        Deletes sessions older than specified days and keeps only the most recent max_sessions.
        """
        logger.debug(f"Cleaning up sessions older than {days} days, keeping max {max_sessions}")

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all sessions sorted by last_updated
        all_sessions = []
        for session_id, metadata in self._metadata_cache.items():
            try:
                last_updated_str = metadata.get("last_updated", "")
                if last_updated_str:
                    last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
                    all_sessions.append((session_id, last_updated))
            except Exception as e:
                logger.warning(f"Failed to parse date for session {session_id}: {e}")

        all_sessions.sort(key=lambda x: x[1])

        # Delete old sessions
        deleted_count = 0
        for session_id, last_updated in all_sessions:
            if last_updated < cutoff_date:
                if self.delete_session(session_id):
                    deleted_count += 1

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} sessions older than {days} days")

        # Delete excess sessions
        remaining = [s for s in all_sessions if s[0] in self._metadata_cache]
        excess_count = len(remaining) - max_sessions
        if excess_count > 0:
            for i in range(excess_count):
                session_id = remaining[i][0]
                if self.delete_session(session_id):
                    logger.info(f"Deleted session {session_id} to maintain {max_sessions} session limit")
