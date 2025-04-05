from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Callable, Optional, List, Dict, Any
from pathlib import Path
from functools import lru_cache
import secrets  # For safe comparison

from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
import uvicorn
import json

from src.host.host import MCPHost
from src.host.config import (
    HostConfig,
    ClientConfig,
    RootConfig,
)  # Keep HostConfig for now, might be needed for host init
from src.config import ServerConfig  # Import the new ServerConfig

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

        # Load host config from file specified in server config
        try:
            with open(server_config.HOST_CONFIG_PATH, "r") as f:
                host_config_data = json.load(f)
        except FileNotFoundError:
            logger.error(
                f"Host configuration file not found: {server_config.HOST_CONFIG_PATH}"
            )
            raise RuntimeError(
                f"Host configuration file not found: {server_config.HOST_CONFIG_PATH}"
            )
        except json.JSONDecodeError as e:
            logger.error(
                f"Error parsing host configuration file {server_config.HOST_CONFIG_PATH}: {e}"
            )
            raise RuntimeError(f"Error parsing host configuration file: {e}")

        # Validate and create HostConfig using Pydantic models
        try:
            # Manually construct ClientConfig and RootConfig lists (similar to old /initialize logic)
            # This assumes the JSON structure matches the Pydantic models
            # Determine the base directory for resolving relative server paths (aurite-mcp directory)
            # Since this file (main.py) is in aurite-mcp/src/, go up two levels.
            aurite_mcp_base_dir = Path(__file__).parent.parent.resolve()
            client_configs = [
                ClientConfig(
                    client_id=agent["client_id"],
                    # Resolve server_path relative to the aurite-mcp base directory
                    server_path=(aurite_mcp_base_dir / agent["server_path"]).resolve(),
                    roots=[
                        RootConfig(
                            uri=root["uri"],
                            name=root["name"],
                            capabilities=root["capabilities"],
                        )
                        for root in agent.get("roots", [])  # Use .get for safety
                    ],
                    capabilities=agent.get("capabilities", []),  # Use .get for safety
                    timeout=agent.get("timeout", 10.0),
                    routing_weight=agent.get("routing_weight", 1.0),
                )
                for agent in host_config_data.get("agents", [])  # Use .get for safety
            ]
            # Read host-specific settings from the JSON config
            host_settings_from_json = host_config_data.get(
                "host", {}
            )  # Default to empty dict if 'host' key is missing
            enable_memory_flag = host_settings_from_json.get(
                "enable_memory", False
            )  # Default to False if key is missing in 'host' dict

            # Create the HostConfig Pydantic model, passing the flag
            host_pydantic_config = HostConfig(
                clients=client_configs, enable_memory=enable_memory_flag
            )
        except ValidationError as e:
            logger.error(f"Host configuration validation failed: {e}")
            raise RuntimeError(f"Host configuration validation failed: {e}")
        except KeyError as e:
            logger.error(f"Missing key in host configuration data: {e}")
            raise RuntimeError(f"Missing key in host configuration data: {e}")

        # Initialize MCPHost
        host_instance = MCPHost(
            config=host_pydantic_config, encryption_key=server_config.ENCRYPTION_KEY
        )
        await (
            host_instance.initialize()
        )  # This should handle workflow registration based on config now
        logger.info("MCPHost initialized successfully.")

        # Store host instance in app state
        app.state.mcp_host = host_instance

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


# Define request models
class PreparePromptRequest(BaseModel):
    prompt_name: str
    prompt_arguments: Dict[str, Any]
    client_id: str
    tool_names: Optional[List[str]] = None


class ExecutePromptRequest(BaseModel):
    prompt_name: str
    prompt_arguments: Dict[str, Any]
    client_id: str
    user_message: str
    tool_names: Optional[List[str]] = None
    model: str = "claude-3-opus-20240229"
    max_tokens: int = 4096
    temperature: float = 0.7
    # anthropic_api_key is removed; host retrieves it from secure config


class ExecuteWorkflowRequest(BaseModel):
    workflow_name: str
    input_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


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


@app.post("/prepare_prompt")
async def prepare_prompt(
    request: PreparePromptRequest,
    api_key: str = Depends(get_api_key),
    host: MCPHost = Depends(get_mcp_host),
):
    """Endpoint to prepare a prompt with associated tools."""
    try:
        result = await host.prepare_prompt_with_tools(
            prompt_name=request.prompt_name,
            prompt_arguments=request.prompt_arguments,
            client_id=request.client_id,
            tool_names=request.tool_names,
        )
        return result
    except ValueError as ve:
        logger.warning(f"Value error during prompt preparation: {ve}")
        # Assuming ValueError implies client-side error (e.g., prompt not found)
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error preparing prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/execute_prompt")
async def execute_prompt(
    request: ExecutePromptRequest,
    api_key: str = Depends(get_api_key),
    host: MCPHost = Depends(get_mcp_host),
):
    """Endpoint to execute a prompt with associated tools."""
    try:
        # Note: anthropic_api_key is intentionally removed from the call below
        # The host should handle retrieving it securely (e.g., from env vars)
        result = await host.execute_prompt_with_tools(
            prompt_name=request.prompt_name,
            prompt_arguments=request.prompt_arguments,
            client_id=request.client_id,
            user_message=request.user_message,
            tool_names=request.tool_names,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            # anthropic_api_key=request.anthropic_api_key, # Removed
        )
        return result
    except ValueError as ve:
        logger.warning(f"Value error during prompt execution: {ve}")
        # Assuming ValueError implies client-side error (e.g., prompt not found, bad args)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error executing prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/execute_workflow")
async def execute_workflow(
    request: ExecuteWorkflowRequest,
    api_key: str = Depends(get_api_key),
    host: MCPHost = Depends(get_mcp_host),
):
    """Endpoint to execute a registered workflow."""
    try:
        result = await host.execute_workflow(
            workflow_name=request.workflow_name,
            input_data=request.input_data,
            metadata=request.metadata,
        )
        return result
    except ValueError as ve:
        logger.warning(f"Value error during workflow execution: {ve}")
        # Assuming ValueError implies client-side error (e.g., workflow not found)
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error executing workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
