import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException  # Added HTTPException
from pydantic import BaseModel

# Import shared dependencies (relative to parent of routes)
from ...dependencies import get_api_key, get_host_manager
from ....host_manager import HostManager
from ....host.models import (
    ClientConfig,
    AgentConfig,
    WorkflowConfig,  # Added for consistency, though not directly used in new endpoints
)
from typing import List  # Added for response model

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Component Management"],  # Tag for OpenAPI docs
    dependencies=[Depends(get_api_key)],  # Apply auth to all routes in this router
)


# --- Request/Response Models (Moved from api.py) ---
class ExecuteAgentRequest(BaseModel):
    """Request body for executing a named agent."""

    user_message: str
    system_prompt: Optional[str] = None


class ExecuteWorkflowRequest(BaseModel):
    """Request body for executing a named workflow."""

    initial_user_message: str


class ExecuteWorkflowResponse(BaseModel):
    """Response body for workflow execution."""

    workflow_name: str
    status: str  # e.g., "completed", "failed"
    final_message: Optional[str] = None
    error: Optional[str] = None


class ExecuteCustomWorkflowRequest(BaseModel):
    initial_input: Any  # Allow flexible input


class ExecuteCustomWorkflowResponse(BaseModel):
    workflow_name: str
    status: str  # e.g., "completed", "failed"
    result: Optional[Any] = None  # Allow flexible output
    error: Optional[str] = None


# --- Execution Endpoints (Moved from api.py) ---


@router.post("/agents/{agent_name}/execute")
async def execute_agent_endpoint(
    agent_name: str,
    request_body: ExecuteAgentRequest,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: HostManager = Depends(get_host_manager),
):
    """
    Executes a configured agent by name using the HostManager.
    """
    logger.info(f"Received request to execute agent: {agent_name}")
    if not manager.execution:
        logger.error("ExecutionFacade not available on HostManager.")
        raise HTTPException(
            status_code=503, detail="Execution subsystem not available."
        )
    # Use the ExecutionFacade via the manager
    result = await manager.execution.run_agent(
        agent_name=agent_name,
        user_message=request_body.user_message,
        system_prompt=request_body.system_prompt,
    )
    logger.info(f"Agent '{agent_name}' execution finished successfully via manager.")
    return result


@router.post(
    "/workflows/{workflow_name}/execute", response_model=ExecuteWorkflowResponse
)
async def execute_workflow_endpoint(
    workflow_name: str,
    request_body: ExecuteWorkflowRequest,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: HostManager = Depends(get_host_manager),
):
    """
    Executes a configured simple workflow by name using the HostManager.
    """
    logger.info(f"Received request to execute workflow: {workflow_name}")
    if not manager.execution:
        logger.error("ExecutionFacade not available on HostManager.")
        raise HTTPException(
            status_code=503, detail="Execution subsystem not available."
        )
    result = await manager.execution.run_simple_workflow(
        workflow_name=workflow_name,
        initial_input=request_body.initial_user_message,
    )
    logger.info(f"Workflow '{workflow_name}' execution finished via manager.")
    if isinstance(result, dict) and result.get("status") == "failed":
        logger.error(
            f"Simple workflow '{workflow_name}' failed (reported by facade): {result.get('error')}"
        )
        # Return the structure directly, matching the response model
        return ExecuteWorkflowResponse(**result)
    else:
        return ExecuteWorkflowResponse(**result)


@router.post(
    "/custom_workflows/{workflow_name}/execute",
    response_model=ExecuteCustomWorkflowResponse,
)
async def execute_custom_workflow_endpoint(
    workflow_name: str,
    request_body: ExecuteCustomWorkflowRequest,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: HostManager = Depends(get_host_manager),
):
    """Executes a configured custom Python workflow by name using the HostManager."""
    logger.info(f"Received request to execute custom workflow: {workflow_name}")
    if not manager.execution:
        logger.error("ExecutionFacade not available on HostManager.")
        raise HTTPException(
            status_code=503, detail="Execution subsystem not available."
        )
    result = await manager.execution.run_custom_workflow(
        workflow_name=workflow_name,
        initial_input=request_body.initial_input,
    )
    logger.info(f"Custom workflow '{workflow_name}' executed successfully via manager.")
    if isinstance(result, dict) and result.get("status") == "failed":
        logger.error(
            f"Custom workflow '{workflow_name}' execution failed (reported by facade): {result.get('error')}"
        )
        return ExecuteCustomWorkflowResponse(
            workflow_name=workflow_name,
            status="failed",
            error=result.get("error", "Unknown execution error"),
        )
    else:
        return ExecuteCustomWorkflowResponse(
            workflow_name=workflow_name, status="completed", result=result
        )


# --- Registration Endpoints (Moved from api.py) ---


@router.post("/clients/register", status_code=201)
async def register_client_endpoint(
    client_config: ClientConfig,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: HostManager = Depends(get_host_manager),
):
    """Dynamically registers a new MCP client."""
    logger.info(f"Received request to register client: {client_config.client_id}")
    await manager.register_client(client_config)
    return {"status": "success", "client_id": client_config.client_id}


@router.post("/agents/register", status_code=201)
async def register_agent_endpoint(
    agent_config: AgentConfig,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: HostManager = Depends(get_host_manager),
):
    """Dynamically registers a new agent configuration."""
    logger.info(f"Received request to register agent: {agent_config.name}")
    await manager.register_agent(agent_config)
    return {"status": "success", "agent_name": agent_config.name}


@router.post("/workflows/register", status_code=201)
async def register_workflow_endpoint(
    workflow_config: WorkflowConfig,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: HostManager = Depends(get_host_manager),
):
    """Dynamically registers a new simple workflow configuration."""
    logger.info(f"Received request to register workflow: {workflow_config.name}")
    await manager.register_workflow(workflow_config)
    return {"status": "success", "workflow_name": workflow_config.name}


# --- Listing Endpoints for Registered Components ---


@router.get("/components/agents", response_model=List[str])
async def list_registered_agents(manager: HostManager = Depends(get_host_manager)):
    """Lists the names of all currently registered agents."""
    if not manager or not manager.agent_configs:
        return []
    return list(manager.agent_configs.keys())


@router.get("/components/workflows", response_model=List[str])
async def list_registered_simple_workflows(
    manager: HostManager = Depends(get_host_manager),
):
    """Lists the names of all currently registered simple workflows."""
    if not manager or not manager.workflow_configs:
        return []
    return list(manager.workflow_configs.keys())


@router.get("/components/custom_workflows", response_model=List[str])
async def list_registered_custom_workflows(
    manager: HostManager = Depends(get_host_manager),
):
    """Lists the names of all currently registered custom workflows."""
    if not manager or not manager.custom_workflow_configs:
        return []
    return list(manager.custom_workflow_configs.keys())
