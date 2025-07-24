from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ....errors import (
    AgentExecutionError,
    ConfigurationError,
    WorkflowExecutionError,
)
from ....execution.facade import ExecutionFacade
from ...dependencies import get_api_key, get_execution_facade

# Configure logging
logger = logging.getLogger(__name__)


def clean_error_message(error: Exception) -> str:
    """Extract a clean error message from an exception chain."""
    if hasattr(error, "__cause__") and error.__cause__:
        return str(error.__cause__)
    return str(error)


def simplify_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Anthropic format to simplified format"""
    simplified_content = ""

    if isinstance(message.get("content"), list):
        for block in message["content"]:
            if block.get("type") == "text":
                simplified_content += block.get("text", "")
            elif block.get("type") == "tool_use":
                simplified_content += f"\n[Tool: {block.get('name')}]\n"
            elif block.get("type") == "tool_result":
                simplified_content += "\n[Tool Result]\n"
    else:
        simplified_content = str(message.get("content", ""))

    return {
        "role": message.get("role"),
        "content": simplified_content.strip(),
        "timestamp": message.get("timestamp"),  # If available
    }


router = APIRouter()


class AgentRunRequest(BaseModel):
    user_message: str
    system_prompt: Optional[str] = None
    session_id: Optional[str] = None


class WorkflowRunRequest(BaseModel):
    initial_input: Any
    session_id: Optional[str] = None


# History-related models
class SessionMetadata(BaseModel):
    session_id: str
    agent_name: Optional[str] = None
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
    message_count: int
    workflow_name: Optional[str] = None
    agents_involved: Optional[List[str]] = None


class SessionListResponse(BaseModel):
    sessions: List[SessionMetadata]
    total: int
    offset: int
    limit: int


class ConversationMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]
    timestamp: Optional[str] = None


class SessionHistoryResponse(BaseModel):
    session_id: str
    agent_name: Optional[str] = None
    messages: List[ConversationMessage]
    metadata: SessionMetadata


@router.get("/status")
async def get_facade_status(
    _api_key: str = Security(get_api_key),
    _facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Get the status of the ExecutionFacade.
    """
    # We can add more detailed status checks later
    return {"status": "active"}


@router.post("/agents/{agent_name}/run")
async def run_agent(
    agent_name: str,
    request: AgentRunRequest,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Execute an agent by name.
    """
    try:
        result = await facade.run_agent(
            agent_name=agent_name,
            user_message=request.user_message,
            system_prompt=request.system_prompt,
            session_id=request.session_id,
        )
        return result.model_dump()
    except ConfigurationError as e:
        logger.error(f"Configuration error for agent '{agent_name}': {e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except AgentExecutionError as e:
        logger.error(f"Agent execution error for '{agent_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {clean_error_message(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error running agent '{agent_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during agent execution") from e


@router.post("/agents/{agent_name}/test")
async def test_agent(
    agent_name: str,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Test an agent's configuration and dependencies.
    """
    try:
        # This can be expanded to a more thorough test
        await facade.run_agent(agent_name, "test message", system_prompt="test")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/agents/{agent_name}/stream")
async def stream_agent(
    agent_name: str,
    request: AgentRunRequest,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Execute an agent by name and stream the response.
    """
    try:

        async def event_generator():
            async for event in facade.stream_agent_run(
                agent_name=agent_name,
                user_message=request.user_message,
                system_prompt=request.system_prompt,
                session_id=request.session_id,
            ):
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error streaming agent '{agent_name}': {e}", exc_info=True)
        # Cannot raise HTTPException for a streaming response.
        # The error will be logged, and the client will see a dropped connection.
        # A more robust solution could involve yielding a final error event.
        return StreamingResponse(
            iter(
                [
                    f"data: {json.dumps({'type': 'error', 'data': {'message': 'An internal error occurred during agent execution'}})}\n\n"
                ]
            ),
            media_type="text/event-stream",
            status_code=500,
        )


@router.post("/workflows/simple/{workflow_name}/run")
async def run_simple_workflow(
    workflow_name: str,
    request: WorkflowRunRequest,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Execute a simple workflow by name.
    """
    try:
        result = await facade.run_simple_workflow(
            workflow_name=workflow_name,
            initial_input=request.initial_input,
            session_id=request.session_id,
        )
        return result.model_dump()
    except ConfigurationError as e:
        logger.error(f"Configuration error for workflow '{workflow_name}': {e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except WorkflowExecutionError as e:
        logger.error(f"Workflow execution error for '{workflow_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {clean_error_message(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error running simple workflow '{workflow_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during workflow execution") from e


@router.post("/workflows/simple/{workflow_name}/test")
async def test_simple_workflow(
    workflow_name: str,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Test a simple workflow.
    """
    try:
        # This can be expanded to a more thorough test
        await facade.run_simple_workflow(workflow_name, "test")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/workflows/custom/{workflow_name}/run")
async def run_custom_workflow(
    workflow_name: str,
    request: WorkflowRunRequest,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Execute a custom workflow by name.
    """
    try:
        result = await facade.run_custom_workflow(
            workflow_name=workflow_name,
            initial_input=request.initial_input,
            session_id=request.session_id,
        )
        return result
    except ConfigurationError as e:
        logger.error(f"Configuration error for workflow '{workflow_name}': {e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except WorkflowExecutionError as e:
        logger.error(f"Workflow execution error for '{workflow_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {clean_error_message(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error running custom workflow '{workflow_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during workflow execution") from e

@router.post("/workflows/custom/{workflow_name}/test")
async def test_custom_workflow(
    workflow_name: str,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Test a custom workflow.
    """
    try:
        # This can be expanded to a more thorough test
        await facade.run_custom_workflow(workflow_name, "test")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/workflows/custom/{workflow_name}/validate")
async def validate_custom_workflow(
    workflow_name: str,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Validate a custom workflow.
    """
    try:
        # This can be expanded to a more thorough test
        await facade.run_custom_workflow(workflow_name, "test")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- History Endpoints ---


@router.get("/history", response_model=SessionListResponse)
async def list_execution_history(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    workflow_name: Optional[str] = Query(None, description="Filter by workflow name"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    List execution history sessions with optional filtering by agent or workflow.
    When filtering by workflow, returns only parent workflow sessions (not individual agent sessions).
    Supports pagination with offset/limit.
    """
    try:
        # Apply retention policy on retrieval
        facade.cleanup_old_sessions()

        # If filtering by workflow, we need to get more sessions and filter
        if workflow_name:
            # Get more sessions to ensure we have enough after filtering
            result = facade.get_sessions_list(
                agent_name=agent_name, 
                workflow_name=workflow_name, 
                limit=(limit + offset) * 10,  # Get more to account for filtering
                offset=0
            )
            
            # Filter to only include parent workflow sessions (those without agent_name)
            filtered_sessions = []
            for session_data in result["sessions"]:
                # Only include sessions where agent_name is None (parent workflow sessions)
                if session_data.get("agent_name") is None:
                    filtered_sessions.append(session_data)
            
            # Apply pagination to filtered results
            total_filtered = len(filtered_sessions)
            paginated_sessions = filtered_sessions[offset:offset + limit]
            
            # Convert to response model
            sessions = [SessionMetadata(**session_data) for session_data in paginated_sessions]
            
            return SessionListResponse(
                sessions=sessions, 
                total=total_filtered, 
                offset=offset, 
                limit=limit
            )
        else:
            # Normal behavior for agent filtering or no filtering
            result = facade.get_sessions_list(
                agent_name=agent_name, 
                workflow_name=workflow_name, 
                limit=limit, 
                offset=offset
            )

            # Convert to response model
            sessions = []
            for session_data in result["sessions"]:
                sessions.append(SessionMetadata(**session_data))

            return SessionListResponse(
                sessions=sessions, total=result["total"], offset=result["offset"], limit=result["limit"]
            )
    except Exception as e:
        logger.error(f"Error listing execution history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve execution history") from e


@router.get("/history/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    raw_format: bool = Query(False, description="Return raw Anthropic format instead of simplified view"),
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Get the full conversation history for a specific session.
    For workflow sessions, returns the combined history from all agents.
    By default returns a simplified view, but can return raw format with raw_format=true.
    Supports partial session ID matching for workflow sessions (e.g., just the suffix like '826c63d4').
    """
    try:
        # First try to get metadata with the exact session_id
        metadata = facade.get_session_metadata(session_id)
        
        # If not found and it looks like a short ID (8-12 hex chars), search for matching sessions
        if metadata is None and len(session_id) >= 8 and len(session_id) <= 12 and all(c in '0123456789abcdefABCDEF-' for c in session_id):
            # Search for sessions ending with this ID
            all_sessions = facade.get_sessions_list(limit=1000, offset=0)
            matching_sessions = []
            
            for session_data in all_sessions["sessions"]:
                if session_data["session_id"].endswith(session_id):
                    matching_sessions.append(session_data["session_id"])
            
            if len(matching_sessions) == 1:
                # Found exactly one match, use it
                session_id = matching_sessions[0]
                metadata = facade.get_session_metadata(session_id)
                logger.info(f"Found matching session for partial ID: {session_id}")
            elif len(matching_sessions) > 1:
                # Multiple matches, return error with suggestions
                raise HTTPException(
                    status_code=400, 
                    detail=f"Multiple sessions found ending with '{session_id}': {matching_sessions[:5]}{'...' if len(matching_sessions) > 5 else ''}"
                )
            # If no matches, continue with normal flow (will result in 404)
        
        # Check if this is a workflow session BEFORE modifying metadata
        is_workflow = metadata and metadata.get("workflow_name") and not metadata.get("agent_name")
        
        if is_workflow:
            # For workflows, get the full combined history
            history = facade.get_full_workflow_history(session_id)
            if not history:
                # Workflow exists but has no agent executions yet
                history = []
        else:
            # For regular agent sessions, get the normal history
            history = facade.get_session_history(session_id)
            if history is None:
                raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

        if metadata is None:
            # Create minimal metadata if not available
            metadata = {"agent_name": "unknown", "message_count": len(history)}
        else:
            # Make a copy of metadata to avoid modifying the original
            metadata = dict(metadata)

        # Add the session_id to the metadata dict before validation
        metadata["session_id"] = session_id
        
        # Fix the agent_name field for workflows
        if is_workflow:
            # For workflows, set agent_name to None since it's not an agent session
            metadata["agent_name"] = None
            
            # Ensure agents_involved is populated
            if not metadata.get("agents_involved"):
                # Extract unique agent session IDs from the full history
                agents_involved = []
                if facade._cache_manager and facade._cache_manager._cache_dir:
                    safe_base_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
                    try:
                        for session_file in facade._cache_manager._cache_dir.glob(f"{safe_base_id}-*-*.json"):
                            # Extract the session ID from the filename
                            agent_session_id = session_file.stem
                            agents_involved.append(agent_session_id)
                    except Exception as e:
                        logger.warning(f"Could not extract agents_involved: {e}")
                metadata["agents_involved"] = agents_involved
        
        # Update message count to reflect actual messages
        metadata["message_count"] = len(history)

        # Format messages based on raw_format flag
        messages = []
        for msg in history:
            if raw_format:
                messages.append(ConversationMessage(**msg))
            else:
                simplified = simplify_message(msg)
                messages.append(ConversationMessage(**simplified))

        # For the top-level response, use None for agent_name if it's a workflow
        response_agent_name = None if is_workflow else metadata.get("agent_name")

        return SessionHistoryResponse(
            session_id=metadata.get("session_id"),
            agent_name=response_agent_name,
            messages=messages,
            metadata=SessionMetadata(**metadata),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session history for '{session_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve session history") from e

@router.delete("/history/{session_id}", status_code=204)
async def delete_session_history(
    session_id: str,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Delete a specific session's history.
    Returns 204 No Content on success, 404 if session not found.
    """
    if session_id == "null":
        raise HTTPException(status_code=404, detail="Session 'null' not found")
    try:
        deleted = facade.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        # Return 204 No Content on successful deletion
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session '{session_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete session") from e


@router.post("/history/cleanup", status_code=200)
async def cleanup_history(
    days: int = Query(30, ge=0, le=365, description="Delete sessions older than this many days"),
    max_sessions: int = Query(50, ge=0, le=1000, description="Maximum number of sessions to keep"),
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Clean up old sessions based on retention policy.
    Deletes sessions older than specified days and keeps only the most recent max_sessions.
    Set days=0 to delete all sessions older than today.
    """
    try:
        facade.cleanup_old_sessions(days=days, max_sessions=max_sessions)
        return {
            "message": f"Cleanup completed. Removed sessions older than {days} days, keeping maximum {max_sessions} sessions."
        }
    except Exception as e:
        logger.error(f"Error during history cleanup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clean up history") from e
