"""
Provides a file-based cache for execution results with in-memory caching.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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
                            self._result_cache[session_id] = data.get("execution_result", data)
                            
                            # Extract metadata
                            result_type = data.get("result_type", "unknown")
                            
                            # Calculate message count from execution result
                            message_count = 0
                            exec_result = data.get("execution_result", {})
                            workflow_name = None
                            agent_name = None
                            agents_involved = []
                            
                            if "conversation_history" in exec_result:
                                message_count = len(exec_result.get("conversation_history", []))
                                # For agent results, get agent name if available
                                agent_name = exec_result.get("agent_name")
                            elif "step_results" in exec_result:
                                # For workflows, count messages from all steps and collect agent session IDs
                                for step in exec_result.get("step_results", []):
                                    if isinstance(step, dict) and "result" in step:
                                        step_result = step["result"]
                                        if isinstance(step_result, dict):
                                            if "conversation_history" in step_result:
                                                message_count += len(step_result.get("conversation_history", []))
                                            # Collect agent session IDs
                                            if "session_id" in step_result:
                                                agents_involved.append(step_result["session_id"])
                                # For workflow results, get workflow name
                                workflow_name = exec_result.get("workflow_name")
                            
                            self._metadata_cache[session_id] = {
                                "created_at": data.get("created_at"),
                                "last_updated": data.get("last_updated"),
                                "result_type": result_type,
                                "session_id": session_id,
                                "message_count": message_count,
                                "workflow_name": workflow_name,
                                "agent_name": agent_name,
                                "agents_involved": agents_involved if agents_involved else None,
                            }
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
                
                real_session_id = data.get("session_id")
                if not real_session_id:
                    logger.warning(f"Session file {session_file} is missing 'session_id' key.")
                    return None

                # Get the execution result
                execution_result = data.get("execution_result", data)
                
                # Calculate message count and extract names from execution result
                message_count = 0
                workflow_name = None
                agent_name = None
                agents_involved = []
                
                if "conversation_history" in execution_result:
                    message_count = len(execution_result.get("conversation_history", []))
                    # For agent results, get agent name if available
                    agent_name = execution_result.get("agent_name")
                elif "step_results" in execution_result:
                    # For workflows, count messages from all steps and collect agent session IDs
                    for step in execution_result.get("step_results", []):
                        if isinstance(step, dict) and "result" in step:
                            step_result = step["result"]
                            if isinstance(step_result, dict):
                                if "conversation_history" in step_result:
                                    message_count += len(step_result.get("conversation_history", []))
                                # Collect agent session IDs
                                if "session_id" in step_result:
                                    agents_involved.append(step_result["session_id"])
                    # For workflow results, get workflow name
                    workflow_name = execution_result.get("workflow_name")
                
                # Update caches
                self._result_cache[real_session_id] = execution_result
                self._metadata_cache[real_session_id] = {
                    "created_at": data.get("created_at"),
                    "last_updated": data.get("last_updated"),
                    "result_type": data.get("result_type", "unknown"),
                    "session_id": real_session_id,
                    "message_count": message_count,
                    "workflow_name": workflow_name,
                    "agent_name": agent_name,
                    "agents_involved": agents_involved if agents_involved else None,
                }
                
                return execution_result
            except Exception as e:
                logger.error(f"Failed to load session {session_id} from disk: {e}")

        return None
    
    def get_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Legacy method for backward compatibility. Extracts conversation history from execution result.
        
        Args:
            session_id: The unique identifier for the session.
            
        Returns:
            A list of message dictionaries, or None if no history is found.
        """
        result = self.get_result(session_id)
        if result:
            # Extract conversation history from the result
            if "conversation_history" in result:
                return result["conversation_history"]
            elif "step_results" in result:
                # For workflows, combine all conversations
                all_messages = []
                for step in result.get("step_results", []):
                    if isinstance(step, dict) and "result" in step:
                        step_result = step["result"]
                        if isinstance(step_result, dict) and "conversation_history" in step_result:
                            all_messages.extend(step_result["conversation_history"])
                return all_messages if all_messages else None
        return None

    def save_result(self, session_id: str, execution_result: Dict[str, Any], result_type: str = "unknown"):
        """
        Saves the complete execution result for a session.

        Args:
            session_id: The unique identifier for the session.
            execution_result: The complete execution result (AgentRunResult or SimpleWorkflowExecutionResult as dict).
            result_type: Type of result ("agent" or "workflow").
        """
        logger.info(f"CacheManager.save_result called for session_id: {session_id}, result_type: {result_type}")

        # Update memory cache
        self._result_cache[session_id] = execution_result

        # Prepare metadata
        now = datetime.utcnow().isoformat()
        
        # Calculate message count and extract names from execution result
        message_count = 0
        workflow_name = None
        agent_name = None
        agents_involved = []
        
        if "conversation_history" in execution_result:
            message_count = len(execution_result.get("conversation_history", []))
            # For agent results, get agent name if available
            agent_name = execution_result.get("agent_name")
        elif "step_results" in execution_result:
            # For workflows, count messages from all steps and collect agent session IDs
            for step in execution_result.get("step_results", []):
                if isinstance(step, dict) and "result" in step:
                    step_result = step["result"]
                    if isinstance(step_result, dict):
                        if "conversation_history" in step_result:
                            message_count += len(step_result.get("conversation_history", []))
                        # Collect agent session IDs
                        if "session_id" in step_result:
                            agents_involved.append(step_result["session_id"])
            # For workflow results, get workflow name
            workflow_name = execution_result.get("workflow_name")
        
        self._metadata_cache[session_id] = {
            "created_at": self._metadata_cache.get(session_id, {}).get("created_at", now),
            "last_updated": now,
            "result_type": result_type,
            "session_id": session_id,
            "message_count": message_count,
            "workflow_name": workflow_name,
            "agent_name": agent_name,
            "agents_involved": agents_involved if agents_involved else None,
        }

        # Save to disk
        session_file = self._get_session_file(session_id)
        logger.info(f"Attempting to save to file: {session_file.absolute()}")
        try:
            data = {
                "session_id": session_id,
                "execution_result": execution_result,
                "result_type": result_type,
                "created_at": self._metadata_cache[session_id]["created_at"],
                "last_updated": now,
            }
            with open(session_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully saved session {session_id} to disk at {session_file.absolute()}")
        except Exception as e:
            logger.error(f"Failed to save session {session_id} to disk: {e}", exc_info=True)

    def save_history(self, session_id: str, conversation: List[Dict[str, Any]], agent_name: Optional[str] = None, 
                    workflow_name: Optional[str] = None, workflow_session_id: Optional[str] = None):
        """
        Legacy method for backward compatibility. Converts conversation to a result format and saves it.
        """
        # Create a minimal result format
        execution_result = {
            "conversation_history": conversation,
            "agent_name": agent_name,
            "workflow_name": workflow_name,
        }
        result_type = "workflow" if workflow_name else "agent"
        self.save_result(session_id, execution_result, result_type)

    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a session.

        Args:
            session_id: The session identifier.

        Returns:
            Metadata dict with created_at, last_updated, result_type, session_id
        """
        # Check memory cache first
        if session_id in self._metadata_cache:
            return self._metadata_cache[session_id]

        # If not in memory, try to load the result which will populate metadata
        result = self.get_result(session_id)
        if result and session_id in self._metadata_cache:
            return self._metadata_cache[session_id]
            
        return None

    def get_sessions_by_agent(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all sessions for a specific agent.
        For now, this returns all agent sessions since we don't track agent names in metadata.
        
        Args:
            agent_name: Name of the agent (currently unused).
            limit: Maximum number of sessions to return.

        Returns:
            List of session metadata dictionaries.
        """
        sessions = []
        for session_id, metadata in self._metadata_cache.items():
            if metadata.get("result_type") == "agent":
                sessions.append({"session_id": session_id, **metadata})

        # Sort by last_updated descending
        sessions.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        return sessions[:limit]

    def get_sessions_by_workflow(self, workflow_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all sessions for a specific workflow.
        For now, this returns all workflow sessions since we don't track workflow names in metadata.

        Args:
            workflow_name: Name of the workflow (currently unused).
            limit: Maximum number of sessions to return.

        Returns:
            List of session metadata dictionaries.
        """
        sessions = []
        for session_id, metadata in self._metadata_cache.items():
            if metadata.get("result_type") == "workflow":
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
        self._result_cache.pop(session_id, None)
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
