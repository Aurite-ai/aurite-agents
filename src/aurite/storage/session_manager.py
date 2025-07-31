"""
Manages the lifecycle and persistence of execution sessions.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
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

    def save_agent_result(self, session_id: str, agent_result: AgentRunResult, base_session_id: Optional[str] = None):
        """
        Saves the complete result of an agent execution.
        """
        self._save_result(session_id, agent_result.model_dump(), "agent", base_session_id)

    def save_workflow_result(
        self, session_id: str, workflow_result: SimpleWorkflowExecutionResult, base_session_id: Optional[str] = None
    ):
        """
        Saves the complete result of a workflow execution.
        """
        self._save_result(session_id, workflow_result.model_dump(), "workflow", base_session_id)

    def _save_result(
        self, session_id: str, execution_result: Dict[str, Any], result_type: str, base_session_id: Optional[str] = None
    ):
        """
        Internal method to save a result to the cache with metadata.
        """
        now = datetime.utcnow().isoformat()
        existing_data = self._cache.get_result(session_id) or {}

        metadata = self._extract_metadata(execution_result)
        session_data = {
            "session_id": session_id,
            "base_session_id": base_session_id,
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
        This method now iterates through the cache directory directly.
        """
        all_validated_sessions: List[SessionMetadata] = []
        cache_dir = self._cache.get_cache_dir()

        for session_file in cache_dir.glob("*.json"):
            try:
                with open(session_file, "r") as f:
                    session_data = json.load(f)

                # Backwards compatibility: ensure message_count is present for older records
                if "message_count" not in session_data:
                    metadata = self._extract_metadata(session_data.get("execution_result", {}))
                    session_data.update(metadata)

                model = self._validate_and_transform_metadata(session_data)
                all_validated_sessions.append(model)
            except json.JSONDecodeError:
                logger.warning(f"Skipping non-JSON file in cache: {session_file}")
            except ValidationError as e:
                session_id = session_data.get("session_id", "unknown")
                logger.warning(
                    f"Skipping session '{session_id}' from file '{session_file}' due to validation error: {e}"
                )
            except Exception as e:
                logger.error(f"Unexpected error processing session file {session_file}: {e}", exc_info=True)

        # Now, perform filtering on the validated Pydantic models
        filtered_sessions: List[SessionMetadata] = []
        if workflow_name:
            filtered_sessions = [s for s in all_validated_sessions if s.is_workflow and s.name == workflow_name]
        elif agent_name:
            # When filtering by agent name, only return direct agent runs.
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
        Delete a specific session. If the session is a workflow, also delete all
        of its child agent sessions. If it's a child agent session, remove it
        from the parent's 'agents_involved' list.
        """
        session_to_delete = self.get_session_metadata(session_id)
        if not session_to_delete:
            return self._cache.delete_session(session_id)  # Let cache handle non-existent case

        # Case 1: The deleted session is a workflow.
        if session_to_delete.is_workflow:
            # Find all child agent sessions that belong to this workflow.
            all_sessions = self.get_sessions_list(limit=10000)["sessions"]
            child_agent_sessions = [
                s
                for s in all_sessions
                if not s.is_workflow
                and s.base_session_id == session_to_delete.base_session_id
                and s.session_id != session_to_delete.session_id
            ]
            for child in child_agent_sessions:
                self._cache.delete_session(child.session_id)
                logger.info(
                    f"Cascading delete: removed child agent session '{child.session_id}' for workflow '{session_id}'."
                )

        # Case 2: The deleted session is a child agent of a workflow.
        elif session_to_delete.base_session_id and session_to_delete.base_session_id != session_id:
            all_sessions = self.get_sessions_list(limit=10000)["sessions"]
            parent_workflows = [
                s for s in all_sessions if s.is_workflow and s.base_session_id == session_to_delete.base_session_id
            ]
            for parent in parent_workflows:
                parent_data = self._cache.get_result(parent.session_id)
                if parent_data and parent_data.get("agents_involved") and session_id in parent_data["agents_involved"]:
                    del parent_data["agents_involved"][session_id]
                    self._cache.save_result(parent.session_id, parent_data)
                    logger.info(f"Removed deleted session '{session_id}' from parent workflow '{parent.session_id}'.")

        # Finally, delete the main session file.
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

    def get_full_session_details(self, session_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[SessionMetadata]]:
        """
        Get both the execution result and metadata for a session, handling partial IDs.
        """
        # Step 1: Attempt a direct lookup first. This is the most efficient path.
        execution_result = self.get_session_result(session_id)
        metadata_model = self.get_session_metadata(session_id)

        # Step 2: If direct lookup fails, search by base_session_id.
        if execution_result is None:
            all_sessions_result = self.get_sessions_list(limit=10000, offset=0)  # Get all sessions
            matching_sessions = [
                s for s in all_sessions_result["sessions"] if s.base_session_id and s.base_session_id == session_id
            ]

            # Step 3: Handle the results of the base_session_id search
            if len(matching_sessions) == 1:
                matched_session_id = matching_sessions[0].session_id
                logger.info(f"Found matching session for base_session_id '{session_id}': {matched_session_id}")
                execution_result = self.get_session_result(matched_session_id)
                metadata_model = self.get_session_metadata(matched_session_id)
            elif len(matching_sessions) > 1:
                # If multiple sessions share the same base ID (e.g., a workflow and its agents),
                # we need to find the primary one (the one without a suffix like -0, -1).
                primary_match = [
                    s for s in matching_sessions if not (s.session_id[-2] == "-" and s.session_id[-1].isdigit())
                ]
                if len(primary_match) == 1:
                    matched_session_id = primary_match[0].session_id
                    logger.info(
                        f"Found primary matching session for base_session_id '{session_id}': {matched_session_id}"
                    )
                    execution_result = self.get_session_result(matched_session_id)
                    metadata_model = self.get_session_metadata(matched_session_id)
                else:
                    # This case is ambiguous, return a 400 error.
                    session_ids = [s.session_id for s in matching_sessions]
                    raise HTTPException(
                        status_code=400,
                        detail=f"Ambiguous partial ID '{session_id}'. Multiple sessions found: {session_ids[:5]}",
                    )

        return execution_result, metadata_model

    def cleanup_old_sessions(self, days: int = 30, max_sessions: int = 50):
        """
        Clean up old sessions based on retention policy.
        Deletes sessions older than specified days and keeps only the most recent max_sessions.
        """
        logger.debug(f"Cleaning up sessions older than {days} days, keeping max {max_sessions}")
        try:
            # Get all sessions sorted by last_updated
            all_sessions_result = self.get_sessions_list(limit=10000, offset=0)  # Get all sessions
            all_sessions = all_sessions_result.get("sessions", [])

            # Sort ascending to find the oldest ones first
            all_sessions.sort(key=lambda x: x.last_updated or "")

            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Identify sessions to delete
            sessions_to_delete = set()
            sessions_kept = []

            for session in all_sessions:
                try:
                    last_updated_str = session.last_updated
                    if last_updated_str:
                        # Ensure timezone-aware comparison
                        last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00")).replace(
                            tzinfo=None
                        )
                        if last_updated < cutoff_date:
                            sessions_to_delete.add(session.session_id)
                        else:
                            sessions_kept.append(session)
                    else:
                        # If no last_updated, consider it for deletion
                        sessions_to_delete.add(session.session_id)
                except Exception as e:
                    logger.warning(f"Failed to parse date for session {session.session_id}: {e}")
                    sessions_to_delete.add(session.session_id)

            # Identify excess sessions from the ones that were kept
            excess_count = len(sessions_kept) - max_sessions
            if excess_count > 0:
                # The list is already sorted oldest to newest, so take the first `excess_count`
                for i in range(excess_count):
                    sessions_to_delete.add(sessions_kept[i].session_id)

            # Perform deletion
            deleted_count = 0
            for session_id in sessions_to_delete:
                if self.delete_session(session_id):
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} sessions based on retention policy.")

        except Exception as e:
            logger.error(f"An error occurred during session cleanup: {e}", exc_info=True)

    def _validate_and_transform_metadata(self, session_data: Dict[str, Any]) -> SessionMetadata:
        """
        Transforms raw session data into a validated Pydantic model.
        """
        session_id = session_data.get("session_id", "N/A")
        result_type = session_data.get("result_type")
        is_workflow = result_type == "workflow"

        # The 'name' is now extracted in _extract_metadata
        name = session_data.get("name")
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
            base_session_id=session_data.get("base_session_id"),
        )

    def _extract_metadata(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts metadata from a raw execution result dictionary.
        """
        message_count = 0
        name = None
        agents_involved: Dict[str, str] = {}
        is_workflow = "step_results" in execution_result

        if is_workflow:
            name = execution_result.get("workflow_name")
            for step in execution_result.get("step_results", []):
                if isinstance(step, dict) and "result" in step:
                    step_result = step["result"]
                    if isinstance(step_result, dict):
                        if "conversation_history" in step_result:
                            message_count += len(step_result.get("conversation_history", []))

                        # We now look for both session_id and agent_name in the step result.
                        agent_session_id = step_result.get("session_id")
                        agent_name_in_step = step_result.get("agent_name")
                        if agent_session_id and agent_name_in_step:
                            agents_involved[agent_session_id] = agent_name_in_step
        else:  # It's an agent result
            name = execution_result.get("agent_name")
            message_count = len(execution_result.get("conversation_history", []))

        return {
            "name": name,
            "message_count": message_count,
            "agents_involved": agents_involved if agents_involved else None,
        }
