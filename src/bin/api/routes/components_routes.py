import logging
from typing import Any, Optional
import json  # Added json import

from fastapi import APIRouter, Depends, HTTPException  # Added HTTPException
from fastapi.responses import StreamingResponse  # Added StreamingResponse
from pydantic import BaseModel

# Import shared dependencies (relative to parent of routes)
from ...dependencies import get_api_key, get_host_manager
from ....host_manager import HostManager
from ....config.config_models import (
    ClientConfig,
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    LLMConfig,  # Added LLMConfig for the new endpoint
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


@router.get("/agents/{agent_name}/execute-stream")  # Changed to GET for EventSource
async def stream_agent_endpoint(
    agent_name: str,
    # user_message and system_prompt will be query parameters, matching ExecuteAgentRequest fields
    user_message: str,  # Made individual query params
    system_prompt: Optional[str] = None,  # Made individual query params
    manager: HostManager = Depends(get_host_manager),
):
    """
    Executes a configured agent by name using the HostManager and streams events via GET.
    """
    logger.info(
        f"Received request to STREAM agent (GET): {agent_name} with message: '{user_message}'"
    )
    if not manager.execution:  # Check if facade is available
        logger.error("ExecutionFacade not available on HostManager for streaming.")
        raise HTTPException(
            status_code=503, detail="Execution subsystem not available."
        )

    async def event_generator():
        try:
            # Use the query parameters directly
            async for event in manager.stream_agent_run_via_facade(
                agent_name=agent_name,
                user_message=user_message,
                system_prompt=system_prompt,
            ):
                event_type = event.get(
                    "event_type", "message"
                )  # Default to "message" if no specific type
                event_data_json = json.dumps(event.get("data", {}))
                # SSE format:
                # event: event_name\n
                # data: json_payload\n
                # id: optional_id\n
                # retry: optional_retry_timeout\n
                # \n (extra newline to terminate)
                sse_formatted_event = (
                    f"event: {event_type}\ndata: {event_data_json}\n\n"
                )
                logger.debug(
                    f"SSE Event Yielding: {repr(sse_formatted_event)}"
                )  # Log the exact SSE string
                yield sse_formatted_event
        except Exception as e:
            logger.error(
                f"Error during agent streaming for '{agent_name}': {e}", exc_info=True
            )
            # Yield a final error event to the client if the generator itself fails
            error_event_data = json.dumps({"type": "critical_error", "message": str(e)})
            yield f"event: error\ndata: {error_event_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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


@router.post("/llm-configs/register", status_code=201)
async def register_llm_config_endpoint(
    llm_config: LLMConfig,  # Use LLMConfig model for request body
    manager: HostManager = Depends(get_host_manager),
):
    """Dynamically registers a new LLM configuration."""
    logger.info(f"Received request to register LLM config: {llm_config.llm_id}")
    await manager.register_llm_config(llm_config)
    return {"status": "success", "llm_id": llm_config.llm_id}

@router.post("/custom_workflows/register", status_code=201)
async def register_custom_workflow_endpoint(
    custom_workflow_config: CustomWorkflowConfig,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: HostManager = Depends(get_host_manager),
):
    """Dynamically registers a new custom workflow configuration."""
    logger.info(f"Received request to register custom workflow: {custom_workflow_config.name}")
    await manager.register_custom_workflow(custom_workflow_config)
    return {"status": "success", "workflow_name": custom_workflow_config.name}


# --- Listing Endpoints for Registered Components ---


@router.get("/components/agents", response_model=List[str])
async def list_registered_agents(manager: HostManager = Depends(get_host_manager)):
    """Lists the names of all currently registered agents from the active project."""
    active_project = manager.project_manager.get_active_project_config()
    if (
        not active_project or not active_project.agents
    ):  # Changed agent_configs to agents
        return []
    return list(active_project.agents.keys())  # Changed agent_configs to agents


@router.get("/components/workflows", response_model=List[str])
async def list_registered_simple_workflows(
    manager: HostManager = Depends(get_host_manager),
):
    """Lists the names of all currently registered simple workflows from the active project."""
    active_project = manager.project_manager.get_active_project_config()
    if (
        not active_project or not active_project.simple_workflows
    ):  # Changed simple_workflow_configs to simple_workflows
        return []
    return list(
        active_project.simple_workflows.keys()
    )  # Changed simple_workflow_configs to simple_workflows


@router.get("/components/custom_workflows", response_model=List[str])
async def list_registered_custom_workflows(
    manager: HostManager = Depends(get_host_manager),
):
    """Lists the names of all currently registered custom workflows from the active project."""
    active_project = manager.project_manager.get_active_project_config()
    if (
        not active_project or not active_project.custom_workflows
    ):  # Changed custom_workflow_configs to custom_workflows
        return []
    return list(
        active_project.custom_workflows.keys()
    )  # Changed custom_workflow_configs to custom_workflows


@router.get("/components/clients", response_model=List[str])
async def list_registered_clients(manager: HostManager = Depends(get_host_manager)):
    """Lists the client_ids of all currently registered clients from the active project."""
    active_project = manager.project_manager.get_active_project_config()
    if not active_project or not active_project.clients:
        return []
    # Client IDs are stored directly in the list if string, or as client_id attribute if ClientConfig object
    client_ids = []
    for client_entry in active_project.clients:
        if isinstance(client_entry, str):
            client_ids.append(client_entry)
        elif hasattr(client_entry, 'client_id'): # Check if it's a ClientConfig model
            client_ids.append(client_entry.client_id)
    return client_ids


@router.get("/components/llm-configs", response_model=List[str])
async def list_registered_llm_configs(
    manager: HostManager = Depends(get_host_manager),
):
    """Lists the llm_ids of all currently registered LLM configurations from the active project."""
    # LLM configs are managed by the ComponentManager, accessed via ProjectManager
    if (
        not manager.project_manager
        or not manager.project_manager.component_manager
        or not manager.project_manager.component_manager.llm_configs
    ):
        return []
    return list(manager.project_manager.component_manager.llm_configs.keys())
