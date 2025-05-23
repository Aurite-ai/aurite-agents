import logging
import secrets
from functools import lru_cache
from typing import Optional
from pathlib import Path

from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import APIKeyHeader

# Import config/models needed by dependencies
from ..config import ServerConfig
from ..host_manager import HostManager  # Needed for get_host_manager
from ..config.component_manager import ComponentManager  # Added for new dependency
from ..config.project_manager import ProjectManager  # Added for new dependency

logger = logging.getLogger(__name__)

# --- Project Root ---
# Define project root relative to this file's location (src/bin/dependencies.py)
# Assuming this file is at src/bin/dependencies.py
PROJECT_ROOT = Path(__file__).parent.parent.parent


# --- Configuration Dependency ---
# Moved from api.py - needed by get_api_key
@lru_cache()
def get_server_config() -> ServerConfig:
    """
    Loads server configuration using pydantic-settings.
    Uses lru_cache to load only once.
    """
    try:
        config = ServerConfig()  # type: ignore[call-arg] # Ignore pydantic-settings false positive
        logger.debug("Server configuration loaded successfully.")  # Changed to DEBUG
        logging.getLogger().setLevel(config.LOG_LEVEL.upper())
        return config
    except Exception as e:  # Catch generic Exception during config load
        logger.error(f"!!! Failed to load server configuration: {e}", exc_info=True)
        raise RuntimeError(f"Server configuration error: {e}") from e


# --- Security Dependency (API Key) ---
# Moved from api.py
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(
    request: Request,
    server_config: ServerConfig = Depends(get_server_config),
    api_key_header_value: Optional[str] = Security(api_key_header),
) -> str:
    """
    Dependency to verify the API key.
    For /agents/.../execute-stream, it first checks the 'api_key' query parameter.
    Otherwise, or as a fallback, it checks the X-API-Key header.
    Uses secrets.compare_digest for timing attack resistance.
    """
    provided_api_key: Optional[str] = None
    auth_source: str = ""

    # Check query parameter first for specific streaming endpoint
    if "/agents/" in request.url.path and request.url.path.endswith("/execute-stream"):
        query_api_key = request.query_params.get("api_key")
        if query_api_key:
            provided_api_key = query_api_key
            auth_source = "query parameter"
            logger.debug("API key provided via query parameter for streaming.")

    # Fallback to header if not found in query for streaming, or for any other endpoint
    if not provided_api_key and api_key_header_value:
        provided_api_key = api_key_header_value
        auth_source = "X-API-Key header"
        logger.debug("API key provided via header.")

    if not provided_api_key:
        logger.warning("API key missing. Attempted sources: query (for stream), header.")
        raise HTTPException(
            status_code=401,
            detail="API key required either in X-API-Key header or as 'api_key' query parameter for streaming endpoints.",
        )

    expected_api_key = getattr(server_config, "API_KEY", None)

    if not expected_api_key:
        logger.error("API_KEY not found in server configuration.")
        raise HTTPException(
            status_code=500, detail="Server configuration error: API Key not set."
        )

    if not secrets.compare_digest(provided_api_key, expected_api_key):
        logger.warning(f"Invalid API key. Source: {auth_source}, Provided: '{provided_api_key}', Expected: '{expected_api_key[:4]}...{expected_api_key[-4:]}'") # Enhanced log, avoid logging full expected key
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key",
        )
    logger.debug(f"API key validated successfully from {auth_source}.")
    return provided_api_key


# --- HostManager Dependency ---
# Moved from api.py - might be needed by multiple routers
async def get_host_manager(request: Request) -> HostManager:
    """
    Dependency function to get the initialized HostManager instance from app state.
    """
    manager: Optional[HostManager] = getattr(request.app.state, "host_manager", None)
    if not manager:
        logger.error("HostManager not initialized or not found in app state.")
        raise HTTPException(
            status_code=503,
            detail="HostManager is not available or not initialized.",
        )
    # Removed debug log from here, keep it in api.py if needed upon retrieval
    return manager


# --- ComponentManager Dependency ---
async def get_component_manager(
    host_manager: HostManager = Depends(get_host_manager),
) -> ComponentManager:
    """
    Dependency function to get the ComponentManager instance from the HostManager.
    """
    if not host_manager.component_manager:
        # This case should ideally not happen if HostManager is initialized correctly
        logger.error(
            "ComponentManager not found on HostManager instance. This indicates an initialization issue."
        )
        raise HTTPException(
            status_code=503,
            detail="ComponentManager is not available due to an internal error.",
        )
    return host_manager.component_manager


# --- ProjectManager Dependency ---
async def get_project_manager(
    host_manager: HostManager = Depends(get_host_manager),
) -> ProjectManager:
    """
    Dependency function to get the ProjectManager instance from the HostManager.
    """
    if not host_manager.project_manager:
        # This case should ideally not happen if HostManager is initialized correctly
        logger.error(
            "ProjectManager not found on HostManager instance. This indicates an initialization issue."
        )
        raise HTTPException(
            status_code=503,
            detail="ProjectManager is not available due to an internal error.",
        )
    return host_manager.project_manager
