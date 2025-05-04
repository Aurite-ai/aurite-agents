from __future__ import annotations

import logging
import os
import secrets  # For safe comparison
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, Callable, Optional  # Added Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError  # Added BaseModel
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse  # Add JSONResponse

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


# --- Custom Exception Handlers ---
# Define handlers before endpoints that might raise these exceptions


# Handler for KeyErrors (typically indicates resource not found)
@app.exception_handler(KeyError)
async def key_error_exception_handler(request: Request, exc: KeyError):
    logger.warning(
        f"Resource not found (KeyError): {exc} for request {request.url.path}"
    )
    # Extract the key name if possible from the exception args
    detail = f"Resource not found: {str(exc)}"
    return JSONResponse(
        status_code=404,
        content={"detail": detail},
    )


# Handler for ValueErrors (can indicate bad input, conflicts, or bad state)
@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    detail = f"Invalid request or state: {str(exc)}"
    status_code = 400  # Default to Bad Request

    # Check for specific error messages to set more specific status codes
    exc_str = str(exc).lower()
    if "already registered" in exc_str:
        status_code = 409  # Conflict
        logger.warning(
            f"Conflict during registration: {exc} for request {request.url.path}"
        )
    elif "hostmanager is not initialized" in exc_str:
        status_code = 503  # Service Unavailable
        logger.error(
            f"Service unavailable (HostManager not init): {exc} for request {request.url.path}"
        )
    elif "not found for agent" in exc_str or "not found for workflow" in exc_str:
        status_code = (
            400  # Bad request because config references non-existent component
        )
        logger.warning(
            f"Configuration error (invalid reference): {exc} for request {request.url.path}"
        )
    else:
        logger.warning(f"ValueError encountered: {exc} for request {request.url.path}")

    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )


# Handler for FileNotFoundError (e.g., custom workflow module, client server path)
@app.exception_handler(FileNotFoundError)
async def file_not_found_error_handler(request: Request, exc: FileNotFoundError):
    logger.error(f"Required file not found: {exc} for request {request.url.path}")
    return JSONResponse(
        status_code=404,  # Treat as Not Found, could argue 500 if it's internal config
        content={"detail": f"Required file not found: {str(exc)}"},
    )


# Handler for setup/import errors related to custom workflows
@app.exception_handler(AttributeError)
@app.exception_handler(ImportError)
@app.exception_handler(PermissionError)
@app.exception_handler(TypeError)
async def custom_workflow_setup_error_handler(request: Request, exc: Exception):
    # Check if the request path involves custom_workflows to be more specific
    # This is a basic check; more robust checking might involve inspecting the exception origin
    is_custom_workflow_path = "/custom_workflows/" in request.url.path
    error_type = type(exc).__name__

    if is_custom_workflow_path:
        logger.error(
            f"Error setting up custom workflow ({error_type}): {exc} for request {request.url.path}",
            exc_info=True,
        )
        detail = f"Error setting up custom workflow: {error_type}: {str(exc)}"
        status_code = 500  # Internal server error during setup
    else:
        # If it's not a custom workflow path, treat as a generic internal error
        logger.error(
            f"Internal server error ({error_type}): {exc} for request {request.url.path}",
            exc_info=True,
        )
        detail = f"Internal server error: {error_type}: {str(exc)}"
        status_code = 500

    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )


# Handler for RuntimeErrors (e.g., during custom workflow execution, config loading)
@app.exception_handler(RuntimeError)
async def runtime_error_exception_handler(request: Request, exc: RuntimeError):
    logger.error(
        f"Runtime error encountered: {exc} for request {request.url.path}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,  # Internal Server Error
        content={"detail": f"Internal server error: {str(exc)}"},
    )


# Generic fallback handler for any other exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc} for request {request.url.path}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"An unexpected internal server error occurred: {type(exc).__name__}"
        },
    )


# Get project root (2 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Mount static files - use relative path from project root
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(PROJECT_ROOT / "static" / "index.html")


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
    # Removed try...except block; exceptions will be caught by handlers
    # Use the ExecutionFacade via the manager
    result = await manager.execution.run_agent(
        agent_name=agent_name,
        user_message=request_body.user_message,
        system_prompt=request_body.system_prompt,
    )
    logger.info(f"Agent '{agent_name}' execution finished successfully via manager.")
    # The result from manager.execution.run_agent should be directly returnable
    # If run_agent raises KeyError, ValueError, etc., the handlers will catch it.
    return result


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
    # Removed try...except block; exceptions will be caught by handlers
    # Use the ExecutionFacade via the manager
    result = await manager.execution.run_simple_workflow(
        workflow_name=workflow_name,
        initial_input=request_body.initial_user_message,  # Facade expects initial_input
    )
    logger.info(f"Workflow '{workflow_name}' execution finished via manager.")
    # manager.execution.run_simple_workflow returns a dict matching ExecuteWorkflowResponse structure
    # If run_simple_workflow raises KeyError, ValueError, etc., the handlers will catch it.
    # We still need to handle the case where the *facade itself* returns an error structure
    if isinstance(result, dict) and result.get("status") == "failed":
        logger.error(
            f"Simple workflow '{workflow_name}' failed (reported by facade): {result.get('error')}"
        )
        # Re-raise a specific exception type that a handler can catch, or return the structure directly
        # Let's return the structure directly, matching the response model
        return ExecuteWorkflowResponse(
            **result
        )  # This assumes the facade error structure matches the response model
    else:
        # Assume success structure matches response model
        return ExecuteWorkflowResponse(**result)


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
    # Removed try...except block; exceptions will be caught by handlers
    # Use the ExecutionFacade via the manager
    result = await manager.execution.run_custom_workflow(
        workflow_name=workflow_name,
        initial_input=request_body.initial_input,
    )
    logger.info(f"Custom workflow '{workflow_name}' executed successfully via manager.")
    # The facade returns the direct result or an error structure
    # If run_custom_workflow raises an exception (KeyError, FileNotFoundError, setup errors, RuntimeError),
    # the handlers will catch it.
    # We still need to handle the case where the *facade itself* returns an error structure
    if isinstance(result, dict) and result.get("status") == "failed":
        logger.error(
            f"Custom workflow '{workflow_name}' execution failed (reported by facade): {result.get('error')}"
        )
        # Return the error structure from the facade, matching the response model
        return ExecuteCustomWorkflowResponse(
            workflow_name=workflow_name,
            status="failed",
            error=result.get("error", "Unknown execution error"),
        )
    else:
        # Return success response with the result from the custom workflow
        return ExecuteCustomWorkflowResponse(
            workflow_name=workflow_name, status="completed", result=result
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
    # Removed try...except block; exceptions will be caught by handlers
    await manager.register_client(client_config)
    # If register_client raises ValueError, FileNotFoundError, etc., the handlers will catch it.
    return {"status": "success", "client_id": client_config.client_id}


@app.post("/agents/register", status_code=201)
async def register_agent_endpoint(
    agent_config: AgentConfig,
    api_key: str = Depends(get_api_key),
    manager: HostManager = Depends(get_host_manager),
):
    """Dynamically registers a new agent configuration."""
    logger.info(f"Received request to register agent: {agent_config.name}")
    # Removed try...except block; exceptions will be caught by handlers
    # Note: Pydantic ValidationError should be handled automatically by FastAPI (422)
    await manager.register_agent(agent_config)
    # If register_agent raises ValueError, etc., the handlers will catch it.
    return {"status": "success", "agent_name": agent_config.name}


@app.post("/workflows/register", status_code=201)
async def register_workflow_endpoint(
    workflow_config: WorkflowConfig,
    api_key: str = Depends(get_api_key),
    manager: HostManager = Depends(get_host_manager),
):
    """Dynamically registers a new simple workflow configuration."""
    logger.info(f"Received request to register workflow: {workflow_config.name}")
    # Removed try...except block; exceptions will be caught by handlers
    # Note: Pydantic ValidationError should be handled automatically by FastAPI (422)
    await manager.register_workflow(workflow_config)
    # If register_workflow raises ValueError, etc., the handlers will catch it.
    return {"status": "success", "workflow_name": workflow_config.name}


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
