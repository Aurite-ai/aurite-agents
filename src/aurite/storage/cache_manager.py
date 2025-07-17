"""
Provides a file-based cache for conversation history with in-memory caching.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """
    A file-based cache for storing conversation history with in-memory caching.
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
        self._history_cache: Dict[str, List[Dict[str, Any]]] = {}
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
                            self._history_cache[session_id] = data.get("conversation", [])
                            self._metadata_cache[session_id] = {
                                "created_at": data.get("created_at"),
                                "last_updated": data.get("last_updated"),
                                "agent_name": data.get("agent_name"),
                                "workflow_name": data.get("workflow_name"),
                                "agents_involved": data.get("agents_involved", []),
                                "message_count": len(data.get("conversation", [])),
                            }
                except Exception as e:
                    logger.warning(f"Failed to load session file {session_file}: {e}")
        except Exception as e:
            logger.error(f"Failed to load cache directory: {e}")

    def get_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves the conversation history for a given session ID.
        Also ensures metadata is loaded into the cache if a file is read.

        Args:
            session_id: The unique identifier for the session. Can be sanitized or not.

        Returns:
            A list of message dictionaries, or None if no history is found.
        """
        # Check memory cache first for the provided session_id
        if session_id in self._history_cache:
            return self._history_cache[session_id]

        # Try to load from disk if not in memory
        session_file = self._get_session_file(session_id)
        if session_file.exists():
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                
                # The real session_id is the one inside the file
                real_session_id = data.get("session_id")
                if not real_session_id:
                    logger.warning(f"Session file {session_file} is missing 'session_id' key.")
                    return None

                conversation = data.get("conversation", [])
                
                # Use the real_session_id to populate the caches
                self._history_cache[real_session_id] = conversation
                self._metadata_cache[real_session_id] = {
                    "created_at": data.get("created_at"),
                    "last_updated": data.get("last_updated"),
                    "agent_name": data.get("agent_name"),
                    "workflow_name": data.get("workflow_name"),
                    "agents_involved": data.get("agents_involved", []),
                    "message_count": len(conversation),
                }
                
                return conversation
            except Exception as e:
                logger.error(f"Failed to load session {session_id} from disk: {e}")

        return None

    def save_history(self, session_id: str, conversation: List[Dict[str, Any]], agent_name: Optional[str] = None, workflow_name: Optional[str] = None):
        """
        Saves or updates the conversation history for a given session ID.

        Args:
            session_id: The unique identifier for the session.
            conversation: The full list of message dictionaries to save.
            agent_name: Optional name of the agent for this session.
            workflow_name: Optional name of the workflow this session belongs to.
        """
        logger.info(
            f"CacheManager.save_history called for session_id: {session_id}, agent_name: {agent_name}, workflow_name: {workflow_name}, conversation_length: {len(conversation)}"
        )

        # Update memory cache
        self._history_cache[session_id] = conversation

        # Prepare metadata
        now = datetime.utcnow().isoformat()
        if session_id not in self._metadata_cache:
            self._metadata_cache[session_id] = {
                "created_at": now, 
                "agent_name": agent_name,
                "workflow_name": workflow_name,
                "agents_involved": []
            }
        
        # Update metadata
        self._metadata_cache[session_id]["last_updated"] = now
        self._metadata_cache[session_id]["message_count"] = len(conversation)
        
        # Track workflow information
        if workflow_name:
            self._metadata_cache[session_id]["workflow_name"] = workflow_name
        
        # Track agents involved
        if agent_name and agent_name not in self._metadata_cache[session_id].get("agents_involved", []):
            if "agents_involved" not in self._metadata_cache[session_id]:
                self._metadata_cache[session_id]["agents_involved"] = []
            self._metadata_cache[session_id]["agents_involved"].append(agent_name)

        # Save to disk
        session_file = self._get_session_file(session_id)
        logger.info(f"Attempting to save to file: {session_file.absolute()}")
        try:
            data = {
                "session_id": session_id,
                "conversation": conversation,
                "created_at": self._metadata_cache[session_id].get("created_at"),
                "last_updated": now,
                "agent_name": agent_name or self._metadata_cache[session_id].get("agent_name"),
                "workflow_name": self._metadata_cache[session_id].get("workflow_name"),
                "agents_involved": self._metadata_cache[session_id].get("agents_involved", []),
                "message_count": len(conversation),
            }
            with open(session_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully saved session {session_id} to disk at {session_file.absolute()}")
        except Exception as e:
            logger.error(f"Failed to save session {session_id} to disk: {e}", exc_info=True)

    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a session.

        Args:
            session_id: The session identifier. Can be sanitized or not.

        Returns:
            Metadata dict with created_at, last_updated, agent_name, message_count
        """
        # Check memory cache first for the provided session_id
        if session_id in self._metadata_cache:
            return self._metadata_cache[session_id]

        # If not in cache, calling get_history will load it from disk.
        # This populates the cache with the *real* session_id from the file.
        if self.get_history(session_id) is not None:
            # The cache is now populated, but maybe under a different key (the real one with spaces).
            # We need to find the real session_id to look up the metadata correctly.
            session_file = self._get_session_file(session_id)
            if session_file.exists():
                try:
                    with open(session_file, "r") as f:
                        data = json.load(f)
                    real_session_id = data.get("session_id")
                    # Now, look up the metadata in the cache using the correct key
                    return self._metadata_cache.get(real_session_id)
                except Exception as e:
                    logger.error(f"Failed to re-read session file for metadata {session_id}: {e}")

        return None

    def get_sessions_by_agent(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all sessions for a specific agent.

        Args:
            agent_name: Name of the agent.
            limit: Maximum number of sessions to return.

        Returns:
            List of session metadata dictionaries.
        """
        sessions = []
        for session_id, metadata in self._metadata_cache.items():
            # Check if agent is the primary agent OR in agents_involved list
            if (metadata.get("agent_name") == agent_name or 
                agent_name in metadata.get("agents_involved", [])):
                sessions.append({"session_id": session_id, **metadata})

        # Sort by last_updated descending
        sessions.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        return sessions[:limit]

    def get_sessions_by_workflow(self, workflow_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all sessions for a specific workflow.

        Args:
            workflow_name: Name of the workflow.
            limit: Maximum number of sessions to return.

        Returns:
            List of session metadata dictionaries.
        """
        sessions = []
        for session_id, metadata in self._metadata_cache.items():
            if metadata.get("workflow_name") == workflow_name:
                sessions.append({"session_id": session_id, **metadata})

        # Sort by last_updated descending
        sessions.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        return sessions[:limit]

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from cache and disk.

        Args:
            session_id: The session to delete.

        Returns:
            True if deleted successfully, False otherwise.
        """
        # Remove from memory
        self._history_cache.pop(session_id, None)
        self._metadata_cache.pop(session_id, None)

        # Remove from disk
        session_file = self._get_session_file(session_id)
        try:
            if session_file.exists():
                session_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def clear_cache(self):
        """
        Clears all conversation histories from memory cache only.
        Files on disk are preserved.
        """
        self._history_cache.clear()
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
