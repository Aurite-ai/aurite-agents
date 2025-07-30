from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from ....components.llm.providers.litellm_client import LiteLLMClient
from ....config.config_manager import ConfigManager
from ....config.config_models import AgentConfig, LLMConfig
from ....errors import (
    ConfigurationError,
    WorkflowExecutionError,
)
from ....execution.facade import ExecutionFacade
from ...dependencies import get_api_key, get_config_manager, get_execution_facade

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
    agent_name: str
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
    message_count: int


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
    agent_name: str
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
    config_manager: ConfigManager = Depends(get_config_manager),
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
        if result.status == "success":
            agent_config = AgentConfig(**config_manager.get_config("agent", agent_name))

            if agent_config.llm_config_id and not agent_config.llm:
                config_manager.validate_llm(agent_config.llm_config_id)

            return result.model_dump()

        if result.exception:
            raise result.exception

        raise HTTPException(status_code=500, detail=result.error_message)
    except Exception as e:
        status_code = 500
        if type(e) is ConfigurationError:
            status_code = 404
        elif type(e).__name__ == "AuthenticationError":
            status_code = 401
        logger.error(f"Error running agent '{agent_name}': {e}")

        error_response = {
            "error": {
                "message": str(e),
                "error_type": type(e).__name__,
                "details": {
                    "agent_name": agent_name,
                    "user_message": request.user_message,
                    "system_prompt": request.system_prompt,
                    "session_id": request.session_id,
                },
            }
        }

        return JSONResponse(
            status_code=status_code,
            content=error_response,
        )


@router.post("/llms/{llm_config_id}/test")
async def test_llm(
    llm_config_id: str,
    api_key: str = Security(get_api_key),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Test an LLM configuration by running a simple 10 token call
    This allows you to quickly test LLM configurations without creating a full agent.
    """
    try:
        # Check if the LLM configuration exists
        llm_config = config_manager.get_config("llm", llm_config_id)
        if not llm_config:
            raise HTTPException(status_code=404, detail=f"LLM configuration '{llm_config_id}' not found.")

        resolved_config = LLMConfig(**llm_config).model_copy(deep=True)

        llm = LiteLLMClient(config=resolved_config)

        llm.validate()

        config_manager.validate_llm(llm_config_id)

        return {
            "status": "success",
            "llm_config_id": llm_config_id,
            "metadata": {
                "provider": resolved_config.provider,
                "model": resolved_config.model,
                "temperature": resolved_config.temperature,
                "max_tokens": resolved_config.max_tokens,
            },
        }
    except Exception as e:
        logger.error(f"Error testing llm '{llm_config_id}': {e}")

        error_response = {
            "status": "error",
            "llm_config_id": llm_config_id,
            "error": {
                "message": str(e),
                "error_type": type(e).__name__,
            },
        }

        if type(e) is HTTPException:
            status_code = e.status_code
        else:
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content=error_response,
        )


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


def _validate_agent(agent_name: str, config_manager: ConfigManager):
    agent_config = config_manager.get_config("agent", agent_name)

    if not agent_config:
        raise ConfigurationError(f"Agent Config for {agent_name} not found")

    agent_config: AgentConfig = AgentConfig(**agent_config)

    llm_config = None
    if agent_config.llm_config_id:
        llm_config = config_manager.get_config("llm", agent_config.llm_config_id)
    else:
        raise ConfigurationError(f"llm_config_id is undefined for agent {agent_name}")

    if not llm_config:
        raise ConfigurationError(
            f"llm_config_id {agent_config.llm_config_id} was not found while running agent {agent_name}"
        )

    resolved_config = LLMConfig(**llm_config).model_copy(deep=True)

    if agent_config.llm:
        overrides = agent_config.llm.model_dump(exclude_unset=True)
        resolved_config = resolved_config.model_copy(update=overrides)

    if agent_config.system_prompt:
        resolved_config.default_system_prompt = agent_config.system_prompt

    llm = LiteLLMClient(config=resolved_config)

    result = llm.validate()

    if result and agent_config.llm_config_id and not agent_config.llm:
        # if llm is valid and no parameters were overriden
        config_manager.validate_llm(agent_config.llm_config_id)


@router.post("/agents/{agent_name}/stream")
async def stream_agent(
    agent_name: str,
    request: AgentRunRequest,
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Execute an agent by name and stream the response.
    """
    try:
        # first, validate the agent
        _validate_agent(agent_name, config_manager)

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
        status_code = 500
        if type(e) is ConfigurationError:
            status_code = 404
        elif type(e).__name__ == "AuthenticationError":
            status_code = 401

        logger.error(f"Error streaming agent '{agent_name}': {e}")

        error_response = {
            "error": {
                "message": str(e),
                "error_type": type(e).__name__,
                "details": {
                    "agent_name": agent_name,
                    "user_message": request.user_message,
                    "system_prompt": request.system_prompt,
                    "session_id": request.session_id,
                },
            }
        }

        return JSONResponse(
            status_code=status_code,
            content=error_response,
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


# --- History Endpoints ---


@router.get("/history", response_model=SessionListResponse)
async def list_execution_history(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    List execution history sessions with optional filtering by agent.
    Supports pagination with offset/limit.
    """
    try:
        # Apply retention policy on retrieval
        facade.cleanup_old_sessions()

        # Get sessions from facade
        result = facade.get_sessions_list(agent_name=agent_name, limit=limit, offset=offset)

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
    By default returns a simplified view, but can return raw format with raw_format=true.
    """
    try:
        # Get history from facade
        history = facade.get_session_history(session_id)
        if history is None:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

        # Get metadata
        metadata = facade.get_session_metadata(session_id)
        if metadata is None:
            # Create minimal metadata if not available
            metadata = {"session_id": session_id, "agent_name": "unknown", "message_count": len(history)}

        # Format messages based on raw_format flag
        messages = []
        for msg in history:
            if raw_format:
                messages.append(ConversationMessage(**msg))
            else:
                simplified = simplify_message(msg)
                messages.append(ConversationMessage(**simplified))

        return SessionHistoryResponse(
            session_id=session_id,
            agent_name=metadata.get("agent_name", "unknown"),
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


@router.get("/agents/{agent_name}/history", response_model=SessionListResponse)
async def get_agent_history(
    agent_name: str,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Get all sessions for a specific agent.
    Returns the most recent sessions up to the limit.
    """
    try:
        # Apply retention policy on retrieval
        facade.cleanup_old_sessions()

        # Get sessions for specific agent (no offset for agent-specific queries)
        result = facade.get_sessions_list(agent_name=agent_name, limit=limit, offset=0)

        # Convert to response model
        sessions = []
        for session_data in result["sessions"]:
            if session_data["agent_name"] == agent_name:
                sessions.append(SessionMetadata(**session_data))

        return SessionListResponse(sessions=sessions, total=len(sessions), offset=0, limit=limit)
    except Exception as e:
        logger.error(f"Error getting history for agent '{agent_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history for agent '{agent_name}'") from e


@router.get("/workflows/{workflow_name}/history", response_model=SessionListResponse)
async def get_workflow_history(
    workflow_name: str,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Get all sessions for a specific workflow.
    Returns the most recent sessions up to the limit.
    """
    try:
        # Apply retention policy on retrieval
        facade.cleanup_old_sessions()

        # Get sessions for specific workflow (no offset for workflow-specific queries)
        result = facade.get_sessions_list(agent_name=workflow_name, limit=limit, offset=0)

        # Convert to response model
        sessions = []
        for session_data in result["sessions"]:
            if session_data["agent_name"] == workflow_name:
                sessions.append(SessionMetadata(**session_data))

        return SessionListResponse(sessions=sessions, total=len(sessions), offset=0, limit=limit)
    except Exception as e:
        logger.error(f"Error getting history for workflow '{workflow_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history for workflow '{workflow_name}'") from e


@router.post("/history/cleanup", status_code=200)
async def cleanup_history(
    days: int = Query(30, ge=1, le=365, description="Delete sessions older than this many days"),
    max_sessions: int = Query(50, ge=1, le=1000, description="Maximum number of sessions to keep"),
    api_key: str = Security(get_api_key),
    facade: ExecutionFacade = Depends(get_execution_facade),
):
    """
    Clean up old sessions based on retention policy.
    Deletes sessions older than specified days and keeps only the most recent max_sessions.
    """
    try:
        facade.cleanup_old_sessions(days=days, max_sessions=max_sessions)
        return {
            "message": f"Cleanup completed. Removed sessions older than {days} days, keeping maximum {max_sessions} sessions."
        }
    except Exception as e:
        logger.error(f"Error during history cleanup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clean up history") from e
