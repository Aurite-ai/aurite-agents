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

# Adjust imports for new location (src/bin -> src)
from ..host_manager import HostManager  # Import the new manager
from ..config import (  # Import the new ServerConfig and the loading utility
    ServerConfig,
)
from ..host.models import (  # Added imports for registration
    ClientConfig,
    AgentConfig,
    WorkflowConfig,
)

# Removed CustomWorkflowManager import

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
        # Assuming .env and HOST_CONFIG_PATH are relative to project root, not this file
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


# --- HostManager Dependency ---
async def get_host_manager(request: Request) -> HostManager:
    """
    Dependency function to get the initialized HostManager instance.
    Relies on the manager being initialized during the application lifespan
    and stored in app.state.
    """
    manager: Optional[HostManager] = getattr(request.app.state, "host_manager", None)
    if not manager:
        logger.error("HostManager not initialized or not found in app state.")
        raise HTTPException(
            status_code=503,  # Service Unavailable
            detail="HostManager is not available or not initialized.",
        )
    logger.debug(
        f"get_host_manager: Retrieved manager instance from app.state: {manager}"
    )
    return manager


# --- FastAPI Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle FastAPI lifecycle events: initialize HostManager on startup, shutdown on exit."""
    manager_instance: Optional[HostManager] = None
    try:
        logger.info("Starting FastAPI server and initializing HostManager...")
        # Load server config
        server_config = get_server_config()

        # Instantiate HostManager
        manager_instance = HostManager(config_path=server_config.HOST_CONFIG_PATH)

        # Initialize HostManager (loads configs, initializes MCPHost)
        await manager_instance.initialize()
        logger.info("HostManager initialized successfully.")

        # Store manager instance in app state
        app.state.host_manager = manager_instance

        yield  # Server runs here

    except Exception as e:
        logger.error(
            f"Error during HostManager initialization or server startup: {e}",
            exc_info=True,
        )
        # Ensure manager (and its host) is cleaned up if initialization partially succeeded
        if manager_instance:
            try:
                await manager_instance.shutdown()
            except Exception as shutdown_e:
                logger.error(
                    f"Error during manager shutdown after startup failure: {shutdown_e}"
                )
        raise  # Re-raise the original exception to prevent server from starting improperly
    finally:
        # Shutdown HostManager on application exit
        final_manager_instance = getattr(app.state, "host_manager", None)
        if final_manager_instance:
            logger.info("Shutting down HostManager...")
            try:
                await final_manager_instance.shutdown()
                logger.info("HostManager shutdown complete.")
            except Exception as e:
                logger.error(f"Error during HostManager shutdown: {e}")
        else:
            logger.info("HostManager was not initialized or already shut down.")

        # Clear manager from state
        if hasattr(app.state, "host_manager"):
            del app.state.host_manager
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
    api_key: str = Depends(get_api_key),
    manager: HostManager = Depends(get_host_manager),
):
    """Endpoint to check the status of the HostManager and its underlying MCPHost."""
    # The get_host_manager dependency ensures the manager and host are initialized
    # We can add more detailed status checks later if needed (e.g., check manager.host)
    return {"status": "initialized", "manager_status": "active"}


# Removed /prepare_prompt endpoint
# Removed /execute_prompt endpoint
# Removed /execute_workflow endpoint


@app.post("/agents/{agent_name}/execute")
async def execute_agent_endpoint(
    agent_name: str,
    request_body: ExecuteAgentRequest,
    api_key: str = Depends(get_api_key),
    manager: HostManager = Depends(get_host_manager),  # Use HostManager dependency
):
    """
    Executes a configured agent by name using the HostManager.
    """
    logger.info(f"Received request to execute agent: {agent_name}")
    try:
        # Delegate execution to the HostManager
        result = await manager.execute_agent(
            agent_name=agent_name, user_message=request_body.user_message
        )
        logger.info(
            f"Agent '{agent_name}' execution finished successfully via manager."
        )
        # The result from manager.execute_agent should be directly returnable
        return result
    except KeyError:
        # This exception is raised by manager.execute_agent if agent_name is not found
        logger.warning(f"Agent configuration not found for name: {agent_name}")
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    except ValueError as ve:
        # Catch potential ValueError if manager wasn't initialized (shouldn't happen with lifespan)
        logger.error(f"ValueError during agent execution: {ve}")
        raise HTTPException(status_code=503, detail=str(ve))
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
    manager: HostManager = Depends(get_host_manager),  # Use HostManager dependency
):
    """
    Executes a configured simple workflow by name using the HostManager.
    """
    logger.info(f"Received request to execute workflow: {workflow_name}")
    try:
        # Delegate execution to the HostManager
        result = await manager.execute_workflow(
            workflow_name=workflow_name,
            initial_user_message=request_body.initial_user_message,
        )
        logger.info(f"Workflow '{workflow_name}' execution finished via manager.")
        # manager.execute_workflow returns a dict matching ExecuteWorkflowResponse structure
        return ExecuteWorkflowResponse(**result)

    except KeyError:
        # This exception is raised by manager.execute_workflow if workflow or agent is not found
        logger.warning(
            f"Workflow configuration or agent within workflow '{workflow_name}' not found."
        )
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' or one of its agents not found",
        )
    except ValueError as ve:
        # Catch potential ValueError if manager wasn't initialized
        logger.error(f"ValueError during workflow execution: {ve}")
        raise HTTPException(status_code=503, detail=str(ve))
    except Exception as e:
        # Catch other unexpected errors from manager.execute_workflow
        logger.error(
            f"Unexpected error during workflow '{workflow_name}' execution: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during workflow execution: {str(e)}",
        )


@app.post(
    "/custom_workflows/{workflow_name}/execute",
    response_model=ExecuteCustomWorkflowResponse,
)
async def execute_custom_workflow_endpoint(
    workflow_name: str,
    request_body: ExecuteCustomWorkflowRequest,
    api_key: str = Depends(get_api_key),
    manager: HostManager = Depends(get_host_manager),  # Use HostManager dependency
):
    """Executes a configured custom Python workflow by name using the HostManager."""
    logger.info(f"Received request to execute custom workflow: {workflow_name}")
    try:
        # Delegate execution to the HostManager
        result = await manager.execute_custom_workflow(
            workflow_name=workflow_name,
            initial_input=request_body.initial_input,
        )
        logger.info(
            f"Custom workflow '{workflow_name}' executed successfully via manager."
        )
        # Return success response
        return ExecuteCustomWorkflowResponse(
            workflow_name=workflow_name, status="completed", result=result
        )
    except (KeyError, FileNotFoundError):
        # Raised by manager if config or module file not found
        logger.warning(
            f"Custom workflow '{workflow_name}' not found or module file missing."
        )
        raise HTTPException(
            status_code=404,
            detail=f"Custom workflow '{workflow_name}' not found or its file is missing.",
        )
    except (AttributeError, ImportError, PermissionError, TypeError) as setup_err:
        # Raised by manager during import/setup
        logger.error(
            f"Error setting up custom workflow '{workflow_name}': {setup_err}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error setting up custom workflow '{workflow_name}': {str(setup_err)}",
        )
    except RuntimeError as exec_err:
        # Raised by manager for errors during the workflow's own execution
        logger.error(
            f"Error during custom workflow '{workflow_name}' execution: {exec_err}",
            exc_info=True,
        )
        # Return 200 OK but indicate failure in the response body (consistent with previous behavior)
        # Or consider returning 500 here? Let's stick to 200 + error for now.
        return ExecuteCustomWorkflowResponse(
            workflow_name=workflow_name, status="failed", error=str(exec_err)
        )
    except ValueError as ve:
        # Catch potential ValueError if manager wasn't initialized
        logger.error(f"ValueError during custom workflow execution: {ve}")
        raise HTTPException(status_code=503, detail=str(ve))
    except Exception as e:  # Catch-all for unexpected errors
        logger.error(
            f"Unexpected error during custom workflow '{workflow_name}' API call: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during custom workflow execution.",
        )


# --- Registration Endpoints ---


@app.post("/clients/register", status_code=201)
async def register_client_endpoint(
    client_config: ClientConfig,
    api_key: str = Depends(get_api_key),
    manager: HostManager = Depends(get_host_manager),
):
    """Dynamically registers a new MCP client."""
    logger.info(f"Received request to register client: {client_config.client_id}")
    try:
        await manager.register_client(client_config)
        return {"status": "success", "client_id": client_config.client_id}
    except ValueError as ve:
        # Could be duplicate ID or host not ready
        logger.warning(f"Failed to register client '{client_config.client_id}': {ve}")
        # Use 409 Conflict for duplicate, 503 if host not ready (though dependency should handle 503)
        status_code = 409 if "already registered" in str(ve) else 503
        raise HTTPException(status_code=status_code, detail=str(ve))
    except FileNotFoundError as fnf_err:  # If server_path doesn't exist during init
        logger.error(f"Client server path not found during registration: {fnf_err}")
        raise HTTPException(
            status_code=400, detail=f"Client server path not found: {fnf_err}"
        )
    except Exception as e:
        logger.error(
            f"Error registering client '{client_config.client_id}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error registering client: {str(e)}",
        )


@app.post("/agents/register", status_code=201)
async def register_agent_endpoint(
    agent_config: AgentConfig,
    api_key: str = Depends(get_api_key),
    manager: HostManager = Depends(get_host_manager),
):
    """Dynamically registers a new agent configuration."""
    logger.info(f"Received request to register agent: {agent_config.name}")
    try:
        await manager.register_agent(agent_config)
        return {"status": "success", "agent_name": agent_config.name}
    except ValueError as ve:
        # Could be duplicate name, invalid client ID, or host not ready
        logger.warning(f"Failed to register agent '{agent_config.name}': {ve}")
        status_code = (
            409 if "already registered" in str(ve) else 400
        )  # 400 for invalid client ID
        if "HostManager is not initialized" in str(ve):
            status_code = 503
        raise HTTPException(status_code=status_code, detail=str(ve))
    except (
        ValidationError
    ) as val_err:  # Should be caught by FastAPI ideally, but belt-and-suspenders
        logger.warning(
            f"Invalid agent configuration received for '{agent_config.name}': {val_err}"
        )
        raise HTTPException(
            status_code=422, detail=f"Invalid agent configuration: {val_err}"
        )
    except Exception as e:
        logger.error(
            f"Error registering agent '{agent_config.name}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Internal server error registering agent: {str(e)}"
        )


@app.post("/workflows/register", status_code=201)
async def register_workflow_endpoint(
    workflow_config: WorkflowConfig,
    api_key: str = Depends(get_api_key),
    manager: HostManager = Depends(get_host_manager),
):
    """Dynamically registers a new simple workflow configuration."""
    logger.info(f"Received request to register workflow: {workflow_config.name}")
    try:
        await manager.register_workflow(workflow_config)
        return {"status": "success", "workflow_name": workflow_config.name}
    except ValueError as ve:
        # Could be duplicate name, invalid agent name, or host not ready
        logger.warning(f"Failed to register workflow '{workflow_config.name}': {ve}")
        status_code = (
            409 if "already registered" in str(ve) else 400
        )  # 400 for invalid agent name
        if "HostManager is not initialized" in str(ve):
            status_code = 503
        raise HTTPException(status_code=status_code, detail=str(ve))
    except ValidationError as val_err:
        logger.warning(
            f"Invalid workflow configuration received for '{workflow_config.name}': {val_err}"
        )
        raise HTTPException(
            status_code=422, detail=f"Invalid workflow configuration: {val_err}"
        )
    except Exception as e:
        logger.error(
            f"Error registering workflow '{workflow_config.name}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error registering workflow: {str(e)}",
        )


def start():
    """Start the FastAPI application with uvicorn, using loaded configuration."""
    # Load config to get server settings
    # Note: This runs get_server_config() again, but @lru_cache makes it fast
    config = get_server_config()

    logger.info(
        f"Starting Uvicorn server on {config.HOST}:{config.PORT} with {config.WORKERS} worker(s)..."
    )

    # Update the app path for uvicorn
    uvicorn.run(
        "src.bin.api:app",  # Changed from "src.main:app"
        host=config.HOST,
        port=config.PORT,
        workers=config.WORKERS,
        log_level=config.LOG_LEVEL.lower(),  # Uvicorn expects lowercase log level
        reload=False,  # Typically False for production/running directly
    )


if __name__ == "__main__":
    start()
