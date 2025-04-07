from __future__ import annotations

import logging
import os
import secrets  # For safe comparison
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, Callable, Optional  # Added Any

from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError  # Added BaseModel
import uvicorn

from src.host.host import MCPHost

# Import Agent for type hinting if needed later, and AgentConfig
from src.agents.agent import Agent
from src.config import (  # Import the new ServerConfig and the loading utility
    ServerConfig,
    load_host_config_from_json,
)

# Removed CustomWorkflowConfig import from here
from src.workflows.manager import CustomWorkflowManager  # Import the manager

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)


# --- Configuration Dependency ---
@lru_cache()
def get_server_config() -> ServerConfig:
    """
    Loads server configuration using pydantic-settings.
    Uses lru_cache to load only once.
    """
    try:
        config = ServerConfig()
        logger.info("Server configuration loaded successfully.")
        # Update logging level based on config
        logging.getLogger().setLevel(config.LOG_LEVEL.upper())
        return config
    except ValidationError as e:
        logger.error(f"!!! Failed to load server configuration: {e}")
        # In a real app, you might want to exit or raise a more specific startup error
        raise RuntimeError(f"Server configuration error: {e}") from e


# --- Security Dependency (API Key) ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(
    server_config: ServerConfig = Depends(get_server_config),
    api_key_header_value: Optional[str] = Security(api_key_header),
) -> str:
    """
    Dependency to verify the API key provided in the request header.
    Uses secrets.compare_digest for timing attack resistance.
    """
    if not api_key_header_value:
        logger.warning("API key missing from request header.")
        raise HTTPException(
            status_code=401,  # Unauthorized
            detail="API key required in X-API-Key header",
        )

    expected_api_key = server_config.API_KEY
    if not secrets.compare_digest(api_key_header_value, expected_api_key):
        logger.warning("Invalid API key received.")
        raise HTTPException(
            status_code=403,  # Forbidden
            detail="Invalid API Key",
        )
    return api_key_header_value  # Return the valid key (though not strictly needed by callers)


# --- MCPHost Dependency ---
async def get_mcp_host(request: Request) -> MCPHost:
    """
    Dependency function to get the initialized MCPHost instance.
    Relies on the host being initialized during the application lifespan
    and stored in app.state.
    """
    host: Optional[MCPHost] = getattr(request.app.state, "mcp_host", None)
    if not host:
        logger.error("MCPHost not initialized or not found in app state.")
        raise HTTPException(
            status_code=503,  # Service Unavailable
            detail="MCPHost is not available or not initialized.",
        )
    logger.debug(f"get_mcp_host: Retrieved host instance from app.state: {host}")
    logger.debug(f"get_mcp_host: Retrieved host instance from app.state: {host}")
    return host


# --- CustomWorkflowManager Dependency ---
async def get_workflow_manager(request: Request) -> CustomWorkflowManager:
    """
    Dependency function to get the initialized CustomWorkflowManager instance.
    Relies on the manager being initialized during the application lifespan
    and stored in app.state.
    """
    manager: Optional[CustomWorkflowManager] = getattr(
        request.app.state, "workflow_manager", None
    )
    if not manager:
        logger.error("CustomWorkflowManager not initialized or not found in app state.")
        raise HTTPException(status_code=503, detail="WorkflowManager is not available.")
    logger.debug(
        f"get_workflow_manager: Retrieved manager instance from app.state: {manager}"
    )
    return manager


# --- FastAPI Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle FastAPI lifecycle events: initialize MCPHost on startup, shutdown on exit."""
    host_instance: Optional[MCPHost] = None
    try:
        logger.info("Starting FastAPI server and initializing MCPHost...")
        # Load server config
        server_config = get_server_config()

        # Load host, agent, and workflow configs using the utility function from src.config
        # The utility handles path resolution and validation
        (
            host_pydantic_config,
            agent_configs_dict,
            workflow_configs_dict,
            custom_workflow_configs_dict,  # Receive custom workflow configs
        ) = load_host_config_from_json(server_config.HOST_CONFIG_PATH)

        # Initialize MCPHost, passing all loaded configurations
        host_instance = MCPHost(
            config=host_pydantic_config,
            agent_configs=agent_configs_dict,
            workflow_configs=workflow_configs_dict,
            # Removed custom_workflow_configs from MCPHost constructor
            encryption_key=server_config.ENCRYPTION_KEY,
        )
        # Instantiate the manager
        manager = CustomWorkflowManager(custom_workflow_configs_dict)

        await (
            host_instance.initialize()
        )  # This should handle workflow registration based on config now
        logger.info("MCPHost initialized successfully.")

        # Store host instance and all configs in app state
        # Store host instance and workflow manager in app state
        app.state.mcp_host = host_instance
        app.state.workflow_manager = manager  # Store the manager instance
        # No longer need to store individual configs directly if accessed via host/manager
        # app.state.agent_configs = agent_configs_dict
        # app.state.workflow_configs = workflow_configs_dict
        # app.state.custom_workflow_configs = custom_workflow_configs_dict

        yield  # Server runs here

    except Exception as e:
        logger.error(f"Error during MCPHost initialization or server startup: {e}")
        # Ensure host is cleaned up if initialization partially succeeded
        if host_instance:
            try:
                await host_instance.shutdown()
            except Exception as shutdown_e:
                logger.error(
                    f"Error during host shutdown after startup failure: {shutdown_e}"
                )
        raise  # Re-raise the original exception to prevent server from starting improperly
    finally:
        # Shutdown MCPHost on application exit
        # No changes needed here, host shutdown remains the same
        final_host_instance = getattr(app.state, "mcp_host", None)
        if final_host_instance:
            logger.info("Shutting down MCPHost...")
            try:
                await final_host_instance.shutdown()
                logger.info("MCPHost shutdown complete.")
            except Exception as e:
                logger.error(f"Error during MCPHost shutdown: {e}")
        else:
            logger.info("MCPHost was not initialized or already shut down.")
        # Clear all configs from state as well
        # Clear host and manager from state
        # if hasattr(app.state, "agent_configs"):
        #     del app.state.agent_configs
        # if hasattr(app.state, "workflow_configs"):
        #     del app.state.workflow_configs
        if hasattr(app.state, "workflow_manager"):
            del app.state.workflow_manager  # Clear manager
        logger.info("FastAPI server shutdown sequence complete.")


# Create FastAPI app
app = FastAPI(
    title="Aurite MCP",
    description="API for managing MCPHost and workflows",
    version="1.0.0",
    lifespan=lifespan,
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable):
    """Log all HTTP requests."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)

    logger.info(
        f"[{request.method}] {request.url.path} - Status: {response.status_code} - "
        f"Duration: {duration:.3f}s - Client: {client_ip} - "
        f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
    )

    return response


# Add CORS middleware
# Origins are loaded from ServerConfig
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_server_config().ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---
class ExecuteAgentRequest(BaseModel):
    """Request body for executing a named agent."""

    user_message: str


class ExecuteWorkflowRequest(BaseModel):
    """Request body for executing a named workflow."""

    initial_user_message: str


class ExecuteWorkflowResponse(BaseModel):
    """Response body for workflow execution."""

    workflow_name: str
    status: str  # e.g., "completed", "failed"
    final_message: Optional[str] = None
    error: Optional[str] = None
    # Optional: Add intermediate_steps: List[Dict] = [] if needed


class ExecuteCustomWorkflowRequest(BaseModel):
    initial_input: Any  # Allow flexible input


class ExecuteCustomWorkflowResponse(BaseModel):
    workflow_name: str
    status: str  # e.g., "completed", "failed"
    result: Optional[Any] = None  # Allow flexible output
    error: Optional[str] = None


# --- Health Check Endpoint ---
@app.get("/health", status_code=200)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


# --- Application Endpoints ---
@app.get("/status")
async def get_status(
    api_key: str = Depends(get_api_key), host: MCPHost = Depends(get_mcp_host)
):
    """Endpoint to check the status of the MCPHost."""
    # The get_mcp_host dependency ensures the host is initialized if we reach here
    return {"status": "initialized"}


# Removed /prepare_prompt endpoint
# Removed /execute_prompt endpoint
# Removed /execute_workflow endpoint


@app.post("/agents/{agent_name}/execute")
async def execute_agent_endpoint(
    agent_name: str,
    request_body: ExecuteAgentRequest,
    api_key: str = Depends(get_api_key),
    host: MCPHost = Depends(get_mcp_host),
):
    """
    Executes a configured agent by name with the provided user message.
    """
    logger.info(f"Received request to execute agent: {agent_name}")
    try:
        # 1. Retrieve AgentConfig from host (using method added in Phase 2)
        agent_config = host.get_agent_config(agent_name)
        logger.debug(f"Found AgentConfig for '{agent_name}'")

        # 2. Instantiate the Agent
        agent = Agent(config=agent_config)
        logger.debug(f"Instantiated Agent '{agent_name}'")

        # 3. Extract client_ids for filtering
        filter_ids = agent_config.client_ids
        logger.debug(f"Applying client filter for '{agent_name}': {filter_ids}")

        # 4. Execute the agent
        result = await agent.execute_agent(
            user_message=request_body.user_message,
            host_instance=host,
            filter_client_ids=filter_ids,  # Pass the filter list
        )
        logger.info(f"Agent '{agent_name}' execution finished successfully.")
        return result

    except KeyError:
        logger.warning(f"Agent configuration not found for name: {agent_name}")
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    except Exception as e:
        logger.error(f"Error during agent '{agent_name}' execution: {e}", exc_info=True)
        # Consider more specific error handling based on potential exceptions
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during agent execution: {str(e)}",
        )


@app.post("/workflows/{workflow_name}/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow_endpoint(
    workflow_name: str,
    request_body: ExecuteWorkflowRequest,
    api_key: str = Depends(get_api_key),
    host: MCPHost = Depends(get_mcp_host),
):
    """
    Executes a configured workflow by name with the provided initial user message.
    """
    logger.info(f"Received request to execute workflow: {workflow_name}")
    current_message = request_body.initial_user_message
    final_status = "failed"  # Default status
    error_message = None

    try:
        # 1. Retrieve WorkflowConfig
        workflow_config = host.get_workflow_config(workflow_name)
        logger.debug(
            f"Found WorkflowConfig for '{workflow_name}' with steps: {workflow_config.steps}"
        )

        if not workflow_config.steps:
            logger.warning(f"Workflow '{workflow_name}' has no steps to execute.")
            return ExecuteWorkflowResponse(
                workflow_name=workflow_name,
                status="completed_empty",
                final_message=current_message,  # Return initial message if no steps
            )

        # 2. Loop through steps
        for i, agent_name in enumerate(workflow_config.steps):
            step_num = i + 1
            logger.info(
                f"Executing workflow '{workflow_name}' step {step_num}: Agent '{agent_name}'"
            )
            try:
                # 2a. Get AgentConfig for the current step
                agent_config = host.get_agent_config(agent_name)
                logger.debug(f"Step {step_num}: Found AgentConfig for '{agent_name}'")

                # 2b. Instantiate Agent
                agent = Agent(config=agent_config)
                logger.debug(f"Step {step_num}: Instantiated Agent '{agent_name}'")

                # 2c. Extract client_ids for filtering
                filter_ids = agent_config.client_ids
                logger.debug(f"Step {step_num}: Applying client filter: {filter_ids}")

                # 2d. Execute Agent with current message and filter
                result = await agent.execute_agent(
                    user_message=current_message,
                    host_instance=host,
                    filter_client_ids=filter_ids,
                )

                # 2e. Error Handling for Agent Execution
                if result.get("error"):
                    error_message = f"Agent '{agent_name}' (step {step_num}) failed: {result['error']}"
                    logger.error(error_message)
                    break  # Stop workflow execution

                if (
                    not result.get("final_response")
                    or not result["final_response"].content
                ):
                    error_message = f"Agent '{agent_name}' (step {step_num}) did not return a final response."
                    logger.error(error_message)
                    break  # Stop workflow execution

                # 2f. Output Extraction (Basic: first text block)
                try:
                    # Find the first text block in the content list
                    text_content = next(
                        (
                            block.text
                            for block in result["final_response"].content
                            if block.type == "text"
                        ),
                        None,
                    )
                    if text_content is None:
                        error_message = f"Agent '{agent_name}' (step {step_num}) response content has no text block."
                        logger.error(error_message)
                        break  # Stop workflow execution
                    current_message = text_content  # Update message for the next step
                    logger.debug(
                        f"Step {step_num}: Output message: '{current_message[:100]}...'"
                    )
                except (AttributeError, IndexError, TypeError) as e:
                    error_message = f"Error extracting text from agent '{agent_name}' (step {step_num}) response: {e}"
                    logger.error(error_message, exc_info=True)
                    break  # Stop workflow execution

            except KeyError:
                # This should ideally be caught by config validation, but handle defensively
                error_message = f"Configuration error: Agent '{agent_name}' (step {step_num}) not found in host config."
                logger.error(error_message)
                raise HTTPException(
                    status_code=500, detail=error_message
                )  # Internal error
            except Exception as agent_exec_e:
                error_message = f"Unexpected error during agent '{agent_name}' (step {step_num}) execution: {agent_exec_e}"
                logger.error(error_message, exc_info=True)
                break  # Stop workflow execution

        # 3. Determine final status
        if error_message is None:
            final_status = "completed"
            logger.info(f"Workflow '{workflow_name}' completed successfully.")

    except KeyError:
        logger.warning(f"Workflow configuration not found for name: {workflow_name}")
        raise HTTPException(
            status_code=404, detail=f"Workflow '{workflow_name}' not found"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during workflow '{workflow_name}' execution: {e}",
            exc_info=True,
        )
        # Use the generic error message if no specific step error occurred
        error_message = (
            error_message
            or f"Internal server error during workflow execution: {str(e)}"
        )
        # Return 500 but include details in the response body
        return ExecuteWorkflowResponse(
            workflow_name=workflow_name,
            status=final_status,  # Will be 'failed'
            final_message=current_message,  # Return last successful message or initial
            error=error_message,
        )

    # 4. Return final response
    return ExecuteWorkflowResponse(
        workflow_name=workflow_name,
        status=final_status,
        final_message=current_message if final_status == "completed" else None,
        error=error_message,
    )


@app.post(
    "/custom_workflows/{workflow_name}/execute",
    response_model=ExecuteCustomWorkflowResponse,
)
async def execute_custom_workflow_endpoint(
    workflow_name: str,
    request_body: ExecuteCustomWorkflowRequest,
    api_key: str = Depends(get_api_key),  # Reuse security dependency
    host: MCPHost = Depends(get_mcp_host),  # Get host instance
    manager: CustomWorkflowManager = Depends(
        get_workflow_manager
    ),  # Get manager instance
):
    """Executes a configured custom Python workflow by name."""
    logger.info(f"Received request to execute custom workflow: {workflow_name}")
    try:
        # Use the manager to execute the workflow, passing the host instance
        result = await manager.execute_custom_workflow(
            workflow_name=workflow_name,
            initial_input=request_body.initial_input,
            host_instance=host,  # Pass the host instance
        )
        # Add detailed logging immediately after the call
        logger.info(
            f"RAW Result received from manager: {result!r}"
        )  # Use !r for detailed repr
        logger.info(f"Custom workflow '{workflow_name}' executed successfully via API.")
        # Existing debug log
        logger.debug(
            f"Result from manager.execute_custom_workflow: type={type(result)}, value={result}"
        )
        return ExecuteCustomWorkflowResponse(
            workflow_name=workflow_name, status="completed", result=result
        )
    except (KeyError, FileNotFoundError):  # Config or file not found
        logger.warning(
            f"Custom workflow '{workflow_name}' not found or module file missing."
        )
        raise HTTPException(
            status_code=404,
            detail=f"Custom workflow '{workflow_name}' not found or its file is missing.",
        )
    except (
        AttributeError,
        ImportError,
        PermissionError,
        TypeError,
    ) as import_exec_err:  # Errors during import/setup
        logger.error(
            f"Error setting up custom workflow '{workflow_name}': {import_exec_err}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error setting up custom workflow '{workflow_name}': {str(import_exec_err)}",
        )
    except (
        RuntimeError
    ) as exec_err:  # Errors during the workflow's own execution or host execution logic
        logger.error(
            f"Error during custom workflow '{workflow_name}' execution: {exec_err}",
            exc_info=True,
        )
        # Return 200 OK but indicate failure in the response body
        return ExecuteCustomWorkflowResponse(
            workflow_name=workflow_name, status="failed", error=str(exec_err)
        )
    except Exception as e:  # Catch-all for unexpected errors
        logger.error(
            f"Unexpected error during custom workflow '{workflow_name}' API call: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during custom workflow execution.",
        )


def start():
    """Start the FastAPI application with uvicorn, using loaded configuration."""
    # Load config to get server settings
    # Note: This runs get_server_config() again, but @lru_cache makes it fast
    config = get_server_config()

    logger.info(
        f"Starting Uvicorn server on {config.HOST}:{config.PORT} with {config.WORKERS} worker(s)..."
    )

    uvicorn.run(
        "src.main:app",
        host=config.HOST,
        port=config.PORT,
        workers=config.WORKERS,
        log_level=config.LOG_LEVEL.lower(),  # Uvicorn expects lowercase log level
        reload=False,  # Typically False for production/running directly
    )


if __name__ == "__main__":
    start()
