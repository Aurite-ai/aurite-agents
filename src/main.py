from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Callable, Optional
from functools import lru_cache
import secrets  # For safe comparison

from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError  # Added BaseModel
import uvicorn

from src.host.host import MCPHost

# Import Agent for type hinting if needed later, and AgentConfig
from src.agents.agent import Agent
from src.host.models import AgentConfig

# Import the new ServerConfig and the loading utility
from src.config import ServerConfig, load_host_config_from_json

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
    return host


# --- FastAPI Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle FastAPI lifecycle events: initialize MCPHost on startup, shutdown on exit."""
    host_instance: Optional[MCPHost] = None
    try:
        logger.info("Starting FastAPI server and initializing MCPHost...")
        # Load server config
        server_config = get_server_config()

        # Load host and agent configs using the utility function from src.config
        # The utility handles path resolution and validation
        host_pydantic_config, agent_configs_dict = load_host_config_from_json(
            server_config.HOST_CONFIG_PATH
        )

        # Initialize MCPHost, passing the loaded agent configurations
        host_instance = MCPHost(
            config=host_pydantic_config,
            agent_configs=agent_configs_dict,  # Pass loaded agent configs
            encryption_key=server_config.ENCRYPTION_KEY,
        )
        await (
            host_instance.initialize()
        )  # This should handle workflow registration based on config now
        logger.info("MCPHost initialized successfully.")

        # Store host instance and agent configs in app state
        app.state.mcp_host = host_instance
        app.state.agent_configs = agent_configs_dict  # Store loaded agent configs

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
        # Clear agent configs from state as well
        if hasattr(app.state, "agent_configs"):
            del app.state.agent_configs
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


# No explicit response model needed, as Agent.execute_agent returns a Dict


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
