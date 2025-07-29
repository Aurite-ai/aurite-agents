"""
Manages the lifecycle and persistence of execution sessions.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationError

from ..components.agents.agent_models import AgentRunResult
from ..components.workflows.workflow_models import SimpleWorkflowExecutionResult
from .cache_manager import CacheManager
from .session_models import SessionMetadata

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Handles the creation, loading, saving, and querying of execution sessions.
    This class acts as a high-level interface over a low-level storage
    mechanism, like the CacheManager.
    """

    def __init__(self, cache_manager: "CacheManager"):
        """
        Initialize the SessionManager.

        Args:
            cache_manager: The low-level cache handler for file I/O.
        """
        self._cache = cache_manager

    def get_session_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the complete execution result for a specific session.
        """
        session_data = self._cache.get_result(session_id)
        if session_data:
            # First, ensure the session data has the latest metadata format
            if "message_count" not in session_data:
                metadata = self._extract_metadata(session_data.get("execution_result", {}))
                session_data.update(metadata)
            return session_data.get("execution_result")
        return None

    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get conversation history for a specific session.
        Extracts conversation from the execution result.
        """
        result = self.get_session_result(session_id)
        if result:
            if "conversation_history" in result:
                return result["conversation_history"]
            elif "step_results" in result:
                all_messages = []
                for step in result.get("step_results", []):
                    if isinstance(step, dict) and "result" in step:
                        step_result = step["result"]
                        if isinstance(step_result, dict) and "conversation_history" in step_result:
                            all_messages.extend(step_result["conversation_history"])
                return all_messages if all_messages else None
        return None

    def add_message_to_history(self, session_id: str, message: Dict[str, Any], agent_name: str):
        """
        Adds a single message to a session's history.
        Used to capture user input immediately in streaming scenarios.
        """
        existing_history = self.get_session_history(session_id) or []
        updated_history = existing_history + [message]
        self.save_conversation_history(session_id, updated_history, agent_name)

    def save_conversation_history(
        self,
        session_id: str,
        conversation: List[Dict[str, Any]],
        agent_name: Optional[str] = None,
        workflow_name: Optional[str] = None,
    ):
        """
        Saves a conversation history, creating a minimal result format.
        """
        execution_result = {
            "conversation_history": conversation,
            "agent_name": agent_name,
            "workflow_name": workflow_name,
        }
        result_type = "workflow" if workflow_name else "agent"
        self._save_result(session_id, execution_result, result_type)

    def save_agent_result(self, session_id: str, agent_result: AgentRunResult):
        """
        Saves the complete result of an agent execution.
        """
        self._save_result(session_id, agent_result.model_dump(), "agent")

    def save_workflow_result(self, session_id: str, workflow_result: SimpleWorkflowExecutionResult):
        """
        Saves the complete result of a workflow execution.
        """
        self._save_result(session_id, workflow_result.model_dump(), "workflow")

    def _save_result(self, session_id: str, execution_result: Dict[str, Any], result_type: str):
        """
        Internal method to save a result to the cache with metadata.
        """
        now = datetime.utcnow().isoformat()
        existing_data = self._cache.get_result(session_id) or {}

        metadata = self._extract_metadata(execution_result)
        session_data = {
            "session_id": session_id,
            "execution_result": execution_result,
            "result_type": result_type,
            "created_at": existing_data.get("created_at", now),
            "last_updated": now,
            **metadata,
        }
        self._cache.save_result(session_id, session_data)

    def get_sessions_list(
        self, agent_name: Optional[str] = None, workflow_name: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get list of sessions with optional filtering, returning validated Pydantic models.
        """
        all_sessions_raw = self._cache.get_all_sessions()
        all_validated_sessions: List[SessionMetadata] = []

        # First, validate all raw session data into Pydantic models
        for session_data in all_sessions_raw:
            # Backwards compatibility: ensure message_count is present for older records
            if "message_count" not in session_data:
                metadata = self._extract_metadata(session_data.get("execution_result", {}))
                session_data.update(metadata)
            try:
                model = self._validate_and_transform_metadata(session_data)
                all_validated_sessions.append(model)
            except ValidationError as e:
                session_id = session_data.get("session_id", "unknown")
                logger.warning(f"Skipping session '{session_id}' due to validation error: {e}")
                continue

        # Now, perform filtering on the validated Pydantic models
        filtered_sessions: List[SessionMetadata] = []
        if workflow_name:
            filtered_sessions = [s for s in all_validated_sessions if s.is_workflow and s.name == workflow_name]
        elif agent_name:
            # This will find agents that were run as part of a workflow.
            # The UI may need to decide how to display this.
            # For now, we return any session where the agent was the primary actor.
            filtered_sessions = [s for s in all_validated_sessions if not s.is_workflow and s.name == agent_name]
        else:
            filtered_sessions = all_validated_sessions

        # Sort by last_updated descending
        filtered_sessions.sort(key=lambda x: x.last_updated or "", reverse=True)

        total = len(filtered_sessions)
        paginated_sessions = filtered_sessions[offset : offset + limit]

        return {"sessions": paginated_sessions, "total": total, "offset": offset, "limit": limit}

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session.
        """
        return self._cache.delete_session(session_id)

    def get_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """
        Get validated Pydantic metadata model for a specific session.
        """
        session_data = self._cache.get_result(session_id)
        if not session_data:
            return None

        # Ensure the session data has the latest metadata format
        if "message_count" not in session_data:
            metadata = self._extract_metadata(session_data.get("execution_result", {}))
            session_data.update(metadata)

        try:
            return self._validate_and_transform_metadata(session_data)
        except ValidationError as e:
            logger.error(f"Validation failed for session '{session_id}': {e}")
            return None

    def cleanup_old_sessions(self, days: int = 30, max_sessions: int = 50):
        """
        Clean up old sessions.
        """
        self._cache.cleanup_old_sessions(days=days, max_sessions=max_sessions)

    def _validate_and_transform_metadata(self, session_data: Dict[str, Any]) -> SessionMetadata:
        """
        Transforms raw session data into a validated Pydantic model.
        """
        session_id = session_data.get("session_id", "N/A")
        result_type = session_data.get("result_type")
        is_workflow = result_type == "workflow"

        name = session_data.get("workflow_name") if is_workflow else session_data.get("agent_name")
        if not name:
            type_str = "Workflow" if is_workflow else "Agent"
            logger.warning(f"{type_str} session '{session_id}' is missing a name. Using placeholder.")
            name = f"Untitled {type_str} ({session_id[:8]})"

        return SessionMetadata(
            session_id=session_id,
            name=name,
            created_at=session_data.get("created_at"),
            last_updated=session_data.get("last_updated"),
            message_count=session_data.get("message_count"),
            is_workflow=is_workflow,
            agents_involved=session_data.get("agents_involved"),
        )

    def _extract_metadata(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts metadata from a raw execution result dictionary.
        """
        message_count = 0
        workflow_name = None
        agent_name = None
        agents_involved = []

        if "conversation_history" in execution_result:
            message_count = len(execution_result.get("conversation_history", []))
            agent_name = execution_result.get("agent_name")
        elif "step_results" in execution_result:
            for step in execution_result.get("step_results", []):
                if isinstance(step, dict) and "result" in step:
                    step_result = step["result"]
                    if isinstance(step_result, dict):
                        if "conversation_history" in step_result:
                            message_count += len(step_result.get("conversation_history", []))
                        if "session_id" in step_result:
                            agents_involved.append(step_result["session_id"])
            workflow_name = execution_result.get("workflow_name")

        return {
            "message_count": message_count,
            "workflow_name": workflow_name,
            "agent_name": agent_name,
            "agents_involved": agents_involved if agents_involved else None,
        }
