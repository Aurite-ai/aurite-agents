"""
Provides a file-based cache for execution results with in-memory caching.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

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
        # Store QA test results cache
        self._qa_result_cache: Dict[str, Dict[str, Any]] = {}
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
            The execution result dict (AgentRunResult or LinearWorkflowExecutionResult), or None if not found.
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
            execution_result: The complete execution result (AgentRunResult or LinearWorkflowExecutionResult as dict).
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

    def save_qa_case_result(self, cache_key: str, cache_data: Dict[str, Any]):
        """
        Save a QA case result to cache.

        Args:
            cache_key: The cache key to store under
            cache_data: The cache data containing result and metadata
        """
        logger.debug(f"CacheManager.save_qa_case_result called for cache_key: {cache_key}")

        # Store in memory cache
        if not hasattr(self, "_qa_case_cache"):
            self._qa_case_cache = {}
        self._qa_case_cache[cache_key] = cache_data

        # Save to disk
        cache_file = self._cache_dir / f"{cache_key}.json"
        logger.debug(f"Attempting to save QA case result to file: {cache_file.absolute()}")
        try:
            with open(cache_file, "w") as f:
                json.dump(cache_data, f, indent=2, default=str)
            logger.debug(f"Successfully saved QA case result {cache_key} to disk at {cache_file.absolute()}")
        except Exception as e:
            logger.error(f"Failed to save QA case result {cache_key} to disk: {e}", exc_info=True)

    def get_qa_case_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a QA case result from cache.

        Args:
            cache_key: The cache key to look up

        Returns:
            Cache data if found, None otherwise
        """
        # Check memory cache first
        if hasattr(self, "_qa_case_cache") and cache_key in self._qa_case_cache:
            return self._qa_case_cache[cache_key]

        # Try to load from disk if not in memory
        cache_file = self._cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                # Store in memory cache for future access
                if not hasattr(self, "_qa_case_cache"):
                    self._qa_case_cache = {}
                self._qa_case_cache[cache_key] = data
                return data
            except Exception as e:
                logger.error(f"Failed to load QA case result {cache_key} from disk: {e}")

        return None

    def clear_cache(self):
        """
        Clears all execution results from memory cache only.
        Files on disk are preserved.
        """
        self._result_cache.clear()
        # Also clear QA case cache if it exists
        if hasattr(self, "_qa_case_cache"):
            self._qa_case_cache.clear()
        self._qa_result_cache.clear()

    # --- QA Result Caching Methods ---

    def _get_qa_result_file(self, result_id: str) -> Path:
        """Get the file path for a QA result."""
        # Sanitize result_id to prevent directory traversal
        safe_result_id = "".join(c for c in result_id if c.isalnum() or c in "-_")
        return self._cache_dir / f"qa_{safe_result_id}.json"

    def get_qa_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a QA test result from cache.

        Args:
            result_id: The unique identifier for the QA result.

        Returns:
            The QA result dict, or None if not found.
        """
        # Check memory cache first
        if result_id in self._qa_result_cache:
            return self._qa_result_cache[result_id]

        # Try to load from disk if not in memory
        result_file = self._get_qa_result_file(result_id)
        if result_file.exists():
            try:
                with open(result_file, "r") as f:
                    data = json.load(f)
                self._qa_result_cache[result_id] = data
                return data
            except Exception as e:
                logger.error(f"Failed to load QA result {result_id} from disk: {e}")

        return None

    def save_qa_result(self, result_id: str, result_data: Dict[str, Any]):
        """
        Saves a QA test result to cache.

        Args:
            result_id: The unique identifier for the QA result.
            result_data: The complete QA result data.
        """
        logger.debug(f"CacheManager.save_qa_result called for result_id: {result_id}")

        # Update memory cache
        self._qa_result_cache[result_id] = result_data

        # Save to disk
        result_file = self._get_qa_result_file(result_id)
        logger.debug(f"Attempting to save QA result to file: {result_file.absolute()}")
        try:
            with open(result_file, "w") as f:
                json.dump(result_data, f, indent=2, default=str)
            logger.debug(f"Successfully saved QA result {result_id} to disk at {result_file.absolute()}")
        except Exception as e:
            logger.error(f"Failed to save QA result {result_id} to disk: {e}", exc_info=True)

    def delete_qa_result(self, result_id: str) -> bool:
        """
        Delete a QA result from cache and disk.

        Args:
            result_id: The QA result to delete.

        Returns:
            True if deleted successfully, False if result not found.
        """
        # Remove from memory
        result_exists_in_mem = self._qa_result_cache.pop(result_id, None) is not None

        # Remove from disk
        result_file = self._get_qa_result_file(result_id)
        try:
            result_exists_on_disk = result_file.exists()
            if result_exists_on_disk:
                result_file.unlink()
            return result_exists_in_mem or result_exists_on_disk
        except Exception as e:
            logger.error(f"Failed to delete QA result {result_id}: {e}")
            return False

    # --- QA Evaluation Result Caching Methods ---

    def _get_qa_evaluation_file(self, cache_key: str) -> Path:
        """Get the file path for a QA evaluation result."""
        # Sanitize cache_key to prevent directory traversal
        safe_cache_key = "".join(c for c in cache_key if c.isalnum() or c in "-_")
        return self._cache_dir / f"{safe_cache_key}.json"

    def save_qa_evaluation_result(self, cache_key: str, cache_data: Dict[str, Any]):
        """
        Save a QA evaluation result to cache.

        Args:
            cache_key: The cache key to store under
            cache_data: The cache data containing result and metadata
        """
        logger.debug(f"CacheManager.save_qa_evaluation_result called for cache_key: {cache_key}")

        # Store in memory cache
        if not hasattr(self, "_qa_evaluation_cache"):
            self._qa_evaluation_cache = {}
        self._qa_evaluation_cache[cache_key] = cache_data

        # Save to disk
        cache_file = self._get_qa_evaluation_file(cache_key)
        logger.debug(f"Attempting to save QA evaluation result to file: {cache_file.absolute()}")
        try:
            with open(cache_file, "w") as f:
                json.dump(cache_data, f, indent=2, default=str)
            logger.debug(f"Successfully saved QA evaluation result {cache_key} to disk at {cache_file.absolute()}")
        except Exception as e:
            logger.error(f"Failed to save QA evaluation result {cache_key} to disk: {e}", exc_info=True)

    def get_qa_evaluation_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a QA evaluation result from cache.

        Args:
            cache_key: The cache key to look up

        Returns:
            Cache data if found, None otherwise
        """
        # Check memory cache first
        if hasattr(self, "_qa_evaluation_cache") and cache_key in self._qa_evaluation_cache:
            return self._qa_evaluation_cache[cache_key]

        # Try to load from disk if not in memory
        cache_file = self._get_qa_evaluation_file(cache_key)
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                # Store in memory cache for future access
                if not hasattr(self, "_qa_evaluation_cache"):
                    self._qa_evaluation_cache = {}
                self._qa_evaluation_cache[cache_key] = data
                return data
            except Exception as e:
                logger.error(f"Failed to load QA evaluation result {cache_key} from disk: {e}")

        return None
