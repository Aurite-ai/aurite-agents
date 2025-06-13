import json  # Added json import
import logging
from typing import List  # Added for response model
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException  # Added HTTPException
from fastapi.responses import StreamingResponse  # Added StreamingResponse
from pydantic import BaseModel

from ....config.config_models import LLMConfig  # Added LLMConfig for the new endpoint
from ....components.workflows.workflow_models import SimpleWorkflowExecutionResult
from ....config.config_models import (
    AgentConfig,
    ClientConfig,
    CustomWorkflowConfig,
    WorkflowConfig,
)
from ....host_manager import Aurite, DuplicateClientIdError

# Import shared dependencies (relative to parent of routes)
from ...dependencies import get_api_key, get_host_manager

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
    manager: Aurite = Depends(get_host_manager),
):
    """
    Executes a configured agent by name using the Aurite.
    """
    logger.info(f"Received request to execute agent: {agent_name}")
    if not manager.execution:
        logger.error("ExecutionFacade not available on Aurite.")
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
    manager: Aurite = Depends(get_host_manager),
):
    """
    Executes a configured agent by name using the Aurite and streams events via GET.
    """
    logger.info(
        f"Received request to STREAM agent (GET): {agent_name} with message: '{user_message}'"
    )
    if not manager.execution:  # Check if facade is available
        logger.error("ExecutionFacade not available on Aurite for streaming.")
        raise HTTPException(
            status_code=503, detail="Execution subsystem not available."
        )

    async def event_generator():
        # logger.info(f"COMPONENTS_ROUTES: event_generator FUNCTION CALLED for agent {agent_name}") # Original log
        # logger.info(
        #     f"COMPONENTS_ROUTES: event_generator started for agent {agent_name}"
        # )
        try:
            # logger.info(
            #     f"COMPONENTS_ROUTES: event_generator TRY block entered for agent {agent_name}. About to call manager.stream_agent_run_via_facade."
            # )
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
                # logger.debug(
                #     f"SSE Event Yielding: {repr(sse_formatted_event)}"
                # )  # Log the exact SSE string
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
    manager: Aurite = Depends(get_host_manager),
):
    """
    Executes a configured simple workflow by name using the Aurite.
    """
    logger.info(f"Received request to execute workflow: {workflow_name}")
    if not manager.execution:
        logger.error("ExecutionFacade not available on Aurite.")
        raise HTTPException(
            status_code=503, detail="Execution subsystem not available."
        )

    # The result is a SimpleWorkflowExecutionResult object
    result: SimpleWorkflowExecutionResult = await manager.execution.run_simple_workflow(
        workflow_name=workflow_name,
        initial_input=request_body.initial_user_message,
    )
    logger.info(f"Workflow '{workflow_name}' execution finished via manager.")

    if result.status == "failed":
        logger.error(f"Simple workflow '{workflow_name}' failed: {result.error}")

    # Construct the API response from the result object
    return ExecuteWorkflowResponse(
        workflow_name=result.workflow_name,
        status=result.status,
        final_message=result.final_message,  # Accesses the @property
        error=result.error,
    )


@router.post(
    "/custom_workflows/{workflow_name}/execute",
    response_model=ExecuteCustomWorkflowResponse,
)
async def execute_custom_workflow_endpoint(
    workflow_name: str,
    request_body: ExecuteCustomWorkflowRequest,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: Aurite = Depends(get_host_manager),
):
    """Executes a configured custom Python workflow by name using the Aurite."""
    logger.info(f"Received request to execute custom workflow: {workflow_name}")
    if not manager.execution:
        logger.error("ExecutionFacade not available on Aurite.")
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
    manager: Aurite = Depends(get_host_manager),
):
    """Dynamically registers a new MCP client."""
    logger.info(f"Received request to register client: {client_config.name}")
    # Aurite.register_client handles upsert logic and potential errors
    try:
        await manager.register_client(client_config)
        return {"status": "success", "name": client_config.name}
    except DuplicateClientIdError as e:  # Specific catch for 409
        logger.error(
            f"Duplicate client ID error registering client {client_config.name}: {e}"
        )
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        logger.error(f"Permission error registering client {client_config.name}: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:  # General ValueErrors still 400
        logger.error(f"Value error registering client {client_config.name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error registering client {client_config.name}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Internal server error during client registration."
        )


@router.post("/agents/register", status_code=201)
async def register_agent_endpoint(
    agent_config: AgentConfig,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: Aurite = Depends(get_host_manager),
):
    """Dynamically registers a new agent configuration."""
    logger.info(f"Received request to register agent: {agent_config.name}")
    try:
        await manager.register_agent(agent_config)
        return {"status": "success", "agent_name": agent_config.name}
    except PermissionError as e:
        logger.error(f"Permission error registering agent {agent_config.name}: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(f"Value error registering agent {agent_config.name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error registering agent {agent_config.name}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Internal server error during agent registration."
        )


@router.post("/workflows/register", status_code=201)
async def register_workflow_endpoint(
    workflow_config: WorkflowConfig,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: Aurite = Depends(get_host_manager),
):
    """Dynamically registers a new simple workflow configuration."""
    logger.info(f"Received request to register workflow: {workflow_config.name}")
    try:
        await manager.register_workflow(workflow_config)
        return {"status": "success", "workflow_name": workflow_config.name}
    except PermissionError as e:
        logger.error(
            f"Permission error registering workflow {workflow_config.name}: {e}"
        )
        raise HTTPException(status_code=403, detail=str(e))
    except (
        ValueError
    ) as e:  # This will catch agent not found errors from manager.register_workflow
        logger.error(f"Value error registering workflow {workflow_config.name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error registering workflow {workflow_config.name}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during workflow registration.",
        )


@router.post("/llms/register", status_code=201)
async def register_llm_endpoint(
    llm_config: LLMConfig,  # Use LLMConfig model for request body
    manager: Aurite = Depends(get_host_manager),
):
    """Dynamically registers a new LLM configuration."""
    logger.info(f"Received request to register LLM config: {llm_config.llm_id}")
    try:
        await manager.register_llm_config(llm_config)
        return {"status": "success", "llm_id": llm_config.llm_id}
    except PermissionError as e:
        logger.error(
            f"Permission error registering LLM config {llm_config.llm_id}: {e}"
        )
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(f"Value error registering LLM config {llm_config.llm_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error registering LLM config {llm_config.llm_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during LLM config registration.",
        )


@router.post("/custom_workflows/register", status_code=201)
async def register_custom_workflow_endpoint(
    custom_workflow_config: CustomWorkflowConfig,
    # api_key: str = Depends(get_api_key), # Dependency moved to router level
    manager: Aurite = Depends(get_host_manager),
):
    """Dynamically registers a new custom workflow configuration."""
    logger.info(
        f"Received request to register custom workflow: {custom_workflow_config.name}"
    )
    try:
        await manager.register_custom_workflow(custom_workflow_config)
        return {"status": "success", "workflow_name": custom_workflow_config.name}
    except PermissionError as e:
        logger.error(
            f"Permission error registering custom workflow {custom_workflow_config.name}: {e}"
        )
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(
            f"Value error registering custom workflow {custom_workflow_config.name}: {e}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error registering custom workflow {custom_workflow_config.name}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during custom workflow registration.",
        )


# --- Listing Endpoints for Registered Components ---


@router.get("/components/agents", response_model=List[str])
async def list_registered_agents(manager: Aurite = Depends(get_host_manager)):
    """Lists the names of all currently registered agents from the active project."""
    active_project = manager.project_manager.get_active_project_config()
    if (
        not active_project or not active_project.agents
    ):  # Changed agent_configs to agents
        return []
    return list(active_project.agents.keys())  # Changed agent_configs to agents


@router.get("/components/workflows", response_model=List[str])
async def list_registered_simple_workflows(
    manager: Aurite = Depends(get_host_manager),
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
    manager: Aurite = Depends(get_host_manager),
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
async def list_registered_clients(manager: Aurite = Depends(get_host_manager)):
    """Lists the names of all currently registered clients from the active project."""
    active_project = manager.project_manager.get_active_project_config()
    if not active_project or not active_project.mcp_servers:
        return []
    # Client IDs are stored directly in the list if string, or as name attribute if ClientConfig object
    names = []
    for client_entry in active_project.mcp_servers:
        if isinstance(client_entry, str):
            names.append(client_entry)
        elif hasattr(client_entry, "name"):  # Check if it's a ClientConfig model
            names.append(client_entry.name)
    return names


@router.get("/components/llms", response_model=List[str])
async def list_registered_llms(
    manager: Aurite = Depends(get_host_manager),
):
    """Lists the llm_ids of all currently registered LLM configurations from the active project."""
    # LLM configs are managed by the ComponentManager, accessed via ProjectManager
    if (
        not manager.project_manager
        or not manager.project_manager.component_manager
        or not manager.project_manager.component_manager.llms
    ):
        return []
    return list(manager.project_manager.component_manager.llms.keys())


@router.get("/host/clients/active", response_model=List[str], tags=["Host Status"])
async def list_active_host_clients(manager: Aurite = Depends(get_host_manager)):
    """Lists the names of all clients currently active and running on the MCPHost instance."""
    if not manager.host or not manager.host.client_manager:
        logger.warning(
            "Host or ClientManager not available for listing active clients."
        )
        return []
    # Ensure active_clients is accessible and is a dictionary
    if not hasattr(manager.host.client_manager, "active_clients") or not isinstance(
        manager.host.client_manager.active_clients, dict
    ):
        logger.error("ClientManager.active_clients is not available or not a dict.")
        return []
    return list(manager.host.client_manager.active_clients.keys())
