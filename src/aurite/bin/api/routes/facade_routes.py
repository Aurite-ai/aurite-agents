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


class ExecutionHistoryResponse(BaseModel):
    """Unified response model for both agent and workflow execution history"""
    result_type: str  # "agent" or "workflow"
    execution_result: Dict[str, Any]  # The complete AgentRunResult or SimpleWorkflowExecutionResult
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


@router.get("/history/{session_id}", response_model=ExecutionHistoryResponse)
async def get_session_history(
    session_id: str,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Get the complete execution result for a specific session.
    Returns the same format as the original execution endpoint.
    Supports partial session ID matching (e.g., just the suffix like '826c63d4').
    """
    try:
        # First try to get the execution result with the exact session_id
        execution_result = facade.get_session_result(session_id)
        metadata = facade.get_session_metadata(session_id)
        
        # If not found and it looks like a short ID (8-12 hex chars), search for matching sessions
        if execution_result is None and len(session_id) >= 8 and len(session_id) <= 12 and all(c in '0123456789abcdefABCDEF-' for c in session_id):
            # Search for sessions ending with this ID
            all_sessions = facade.get_sessions_list(limit=1000, offset=0)
            matching_sessions = []
            
            for session_data in all_sessions["sessions"]:
                if session_data["session_id"].endswith(session_id):
                    matching_sessions.append(session_data["session_id"])
            
            if len(matching_sessions) == 1:
                # Found exactly one match, use it
                session_id = matching_sessions[0]
                execution_result = facade.get_session_result(session_id)
                metadata = facade.get_session_metadata(session_id)
                logger.info(f"Found matching session for partial ID: {session_id}")
            elif len(matching_sessions) > 1:
                # Multiple matches, return error with suggestions
                raise HTTPException(
                    status_code=400, 
                    detail=f"Multiple sessions found ending with '{session_id}': {matching_sessions[:5]}{'...' if len(matching_sessions) > 5 else ''}"
                )
        
        if execution_result is None:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        
        if metadata is None:
            # Create minimal metadata if not available
            metadata = {
                "session_id": session_id,
                "result_type": "unknown",
                "created_at": None,
                "last_updated": None,
                "message_count": 0,
            }
        
        # Ensure all required fields are present in metadata
        metadata["session_id"] = session_id
        if "message_count" not in metadata:
            # Count messages from the execution result
            if "conversation_history" in execution_result:
                metadata["message_count"] = len(execution_result["conversation_history"])
            elif "step_results" in execution_result:
                count = 0
                for step in execution_result.get("step_results", []):
                    if isinstance(step, dict) and "result" in step:
                        step_result = step["result"]
                        if isinstance(step_result, dict) and "conversation_history" in step_result:
                            count += len(step_result["conversation_history"])
                metadata["message_count"] = count
            else:
                metadata["message_count"] = 0
        
        # Set default values for optional fields
        metadata.setdefault("agent_name", None)
        metadata.setdefault("workflow_name", None)
        metadata.setdefault("agents_involved", None)
        
        return ExecutionHistoryResponse(
            result_type=metadata.get("result_type", "unknown"),
            execution_result=execution_result,
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
