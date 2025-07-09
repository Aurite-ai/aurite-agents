from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Security
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
            iter([f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"]),
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
