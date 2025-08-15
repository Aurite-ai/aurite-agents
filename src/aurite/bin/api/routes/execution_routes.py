from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.responses import JSONResponse, StreamingResponse

from ....execution.aurite_engine import AuriteEngine
from ....lib.components.evaluation.evaluator import evaluate_agent
from ....lib.components.llm.litellm_client import LiteLLMClient
from ....lib.config.config_manager import ConfigManager
from ....lib.models import (
    AgentConfig,
    AgentRunRequest,
    EvaluationRequest,
    ExecutionHistoryResponse,
    LLMConfig,
    SessionListResponse,
    WorkflowRunRequest,
)
from ....lib.storage.sessions.session_manager import SessionManager
from ....utils.errors import ConfigurationError, MaxIterationsReachedError, WorkflowExecutionError
from ...dependencies import (
    get_api_key,
    get_config_manager,
    get_execution_facade,
    get_session_manager,
)

# Configure logging
logger = logging.getLogger(__name__)


def clean_error_message(error: Exception) -> str:
    """Extract a clean error message from an exception chain."""
    if hasattr(error, "__cause__") and error.__cause__:
        return str(error.__cause__)
    return str(error)


router = APIRouter(prefix="/execution", tags=["Execution Facade"])


@router.get("/status")
async def get_facade_status(
    _api_key: str = Security(get_api_key),
    _facade: AuriteEngine = Depends(get_execution_facade),
):
    """
    Get the status of the AuriteEngine.
    """
    # We can add more detailed status checks later
    return {"status": "active"}


@router.post("/agents/{agent_name}/run")
async def run_agent(
    agent_name: str,
    request: AgentRunRequest,
    api_key: str = Security(get_api_key),
    engine: AuriteEngine = Depends(get_execution_facade),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Execute an agent by name.
    """
    try:
        result = await engine.run_agent(
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

        elif result.status == "max_iterations_reached":
            raise MaxIterationsReachedError(result.error_message)

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
    engine: AuriteEngine = Depends(get_execution_facade),
):
    """
    Test an agent's configuration and dependencies.
    """
    try:
        # This can be expanded to a more thorough test
        await engine.run_agent(agent_name, "test message", system_prompt="test")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/evaluate")
async def evaluate_agent_endpoint(
    request: EvaluationRequest,
    api_key: str = Security(get_api_key),
    engine: AuriteEngine = Depends(get_execution_facade),
):
    try:
        eval_result = await evaluate_agent(request, engine)
        return eval_result
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
    engine: AuriteEngine = Depends(get_execution_facade),
    config_manager: ConfigManager = Depends(get_config_manager),
):
    """
    Execute an agent by name and stream the response.
    """
    try:
        # first, validate the agent
        _validate_agent(agent_name, config_manager)

        logger.info(f"Starting stream for agent '{agent_name}' - User message length: {len(request.user_message)}")

        async def event_generator():
            async for event in engine.stream_agent_run(
                agent_name=agent_name,
                user_message=request.user_message,
                system_prompt=request.system_prompt,
                session_id=request.session_id,
            ):
                yield f"data: {json.dumps(event)}\n\n"

        # Add streaming-specific headers to ensure compatibility across environments
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Expose-Headers": "Content-Type",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }

        return StreamingResponse(
            event_generator(), 
            media_type="text/event-stream",
            headers=headers
        )
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


@router.post("/workflows/linear/{workflow_name}/run")
async def run_linear_workflow(
    workflow_name: str,
    request: WorkflowRunRequest,
    api_key: str = Security(get_api_key),
    engine: AuriteEngine = Depends(get_execution_facade),
):
    """
    Execute a linear workflow by name.
    """
    try:
        result = await engine.run_linear_workflow(
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
        logger.error(f"Unexpected error running linear workflow '{workflow_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during workflow execution") from e


@router.post("/workflows/linear/{workflow_name}/test")
async def test_linear_workflow(
    workflow_name: str,
    api_key: str = Security(get_api_key),
    engine: AuriteEngine = Depends(get_execution_facade),
):
    """
    Test a linear workflow.
    """
    try:
        # This can be expanded to a more thorough test
        await engine.run_linear_workflow(workflow_name, "test")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/workflows/custom/{workflow_name}/run")
async def run_custom_workflow(
    workflow_name: str,
    request: WorkflowRunRequest,
    api_key: str = Security(get_api_key),
    engine: AuriteEngine = Depends(get_execution_facade),
):
    """
    Execute a custom workflow by name.
    """
    try:
        result = await engine.run_custom_workflow(
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
    engine: AuriteEngine = Depends(get_execution_facade),
):
    """
    Test a custom workflow.
    """
    try:
        # This can be expanded to a more thorough test
        await engine.run_custom_workflow(workflow_name, "test")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/workflows/custom/{workflow_name}/validate")
async def validate_custom_workflow(
    workflow_name: str,
    api_key: str = Security(get_api_key),
    engine: AuriteEngine = Depends(get_execution_facade),
):
    """
    Validate a custom workflow.
    """
    try:
        # This can be expanded to a more thorough test
        await engine.run_custom_workflow(workflow_name, "test")
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
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    List execution history sessions with optional filtering by agent or workflow.
    When filtering by workflow, returns only parent workflow sessions (not individual agent sessions).
    Supports pagination with offset/limit.
    """
    try:
        # Apply retention policy on retrieval
        session_manager.cleanup_old_sessions()

        result = session_manager.get_sessions_list(
            agent_name=agent_name, workflow_name=workflow_name, limit=limit, offset=offset
        )

        return SessionListResponse(
            sessions=result["sessions"],
            total=result["total"],
            offset=result["offset"],
            limit=result["limit"],
        )
    except Exception as e:
        logger.error(f"Error listing execution history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve execution history") from e


@router.get("/history/{session_id}", response_model=ExecutionHistoryResponse)
async def get_session_history(
    session_id: str,
    api_key: str = Security(get_api_key),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Get the complete execution result for a specific session.
    Returns the same format as the original execution endpoint.
    Supports partial session ID matching (e.g., just the suffix like '826c63d4').
    """
    try:
        # The session manager now handles partial ID matching
        execution_result, metadata_model = session_manager.get_full_session_details(session_id)

        if execution_result is None or metadata_model is None:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

        result_type = "workflow" if metadata_model.is_workflow else "agent"
        return ExecutionHistoryResponse(
            result_type=result_type,
            execution_result=execution_result,
            metadata=metadata_model,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session history for '{session_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve session history") from e


@router.delete("/history/{session_id}")
async def delete_session_history(
    session_id: str,
    api_key: str = Security(get_api_key),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Delete a specific session's history.
    Returns 204 No Content on success, 404 if session not found.
    """
    if session_id == "null":
        raise HTTPException(status_code=404, detail="Session 'null' not found")
    try:
        deleted = session_manager.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        # Return 204 No Content on successful deletion
        from fastapi import Response

        return Response(status_code=204)
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
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Clean up old sessions based on retention policy.
    Deletes sessions older than specified days and keeps only the most recent max_sessions.
    Set days=0 to delete all sessions older than today.
    """
    try:
        session_manager.cleanup_old_sessions(days=days, max_sessions=max_sessions)
        return {
            "message": f"Cleanup completed. Removed sessions older than {days} days, keeping maximum {max_sessions} sessions."
        }
    except Exception as e:
        logger.error(f"Error during history cleanup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clean up history") from e
        raise HTTPException(status_code=500, detail="Failed to clean up history") from e
