import logging
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security, status  # Added status
from fastapi.security import APIKeyHeader

# Import config/models needed by dependencies
from ..config import ServerConfig
from ..config.config_manager import ConfigManager
from ..execution.facade import ExecutionFacade
from ..host.host import MCPHost  # Added for get_host
from ..host_manager import Aurite  # Needed for get_host_manager
from ..storage.session_manager import SessionManager

logger = logging.getLogger(__name__)

# --- Project Root ---
# The project root is now determined by the Aurite instance's ConfigManager,
# which finds the nearest `.aurite` file. This makes the API project-aware.
PROJECT_ROOT = Path.cwd()


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
        raise HTTPException(status_code=500, detail="Server configuration error: API Key not set.")

    if not secrets.compare_digest(provided_api_key, expected_api_key):
        logger.warning(
            f"Invalid API key. Source: {auth_source}, Provided: '{provided_api_key}', Expected: '{expected_api_key[:4]}...{expected_api_key[-4:]}'"
        )  # Enhanced log, avoid logging full expected key
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key",
        )
    logger.debug(f"API key validated successfully from {auth_source}.")
    return provided_api_key


# --- Aurite Dependency ---
# Moved from api.py - might be needed by multiple routers
async def get_host_manager(request: Request) -> Aurite:
    """
    Dependency function to get the initialized Aurite instance from app state.
    """
    manager: Optional[Aurite] = getattr(request.app.state, "aurite_instance", None)
    if not manager:
        logger.error("Aurite not initialized or not found in app state.")
        raise HTTPException(
            status_code=503,
            detail="Aurite is not available or not initialized.",
        )
    return manager


# --- MCPHost Dependency ---
async def get_host(host_manager: Aurite = Depends(get_host_manager)) -> MCPHost:
    """
    Dependency function to get the MCPHost instance from the Aurite manager.
    """
    if not host_manager.kernel.host:
        # This case should ideally not happen if Aurite is initialized correctly
        logger.error("MCPHost not found on Aurite instance. This indicates an initialization issue.")
        raise HTTPException(
            status_code=503,
            detail="MCPHost is not available due to an internal error.",
        )
    return host_manager.kernel.host


# --- ConfigManager Dependency ---
async def get_config_manager(
    host_manager: Aurite = Depends(get_host_manager),
) -> ConfigManager:
    """
    Dependency function to get the ConfigManager instance from the Aurite manager.
    """
    return host_manager.get_config_manager()


# --- ExecutionFacade Dependency ---
async def get_execution_facade(
    host_manager: Aurite = Depends(get_host_manager),
) -> ExecutionFacade:
    """
    Dependency function to get the ExecutionFacade instance from the Aurite manager.
    """
    if not host_manager.kernel.execution:
        # This case should ideally not happen if Aurite is initialized correctly
        logger.error("ExecutionFacade not found on Aurite instance. This indicates an initialization issue.")
        raise HTTPException(
            status_code=503,
            detail="ExecutionFacade is not available due to an internal error.",
        )
    return host_manager.kernel.execution


# --- SessionManager Dependency ---
async def get_session_manager(
    host_manager: Aurite = Depends(get_host_manager),
) -> SessionManager:
    """
    Dependency function to get the SessionManager instance from the Aurite manager.
    """
    # The SessionManager is now created and held by the ExecutionFacade.
    # This dependency retrieves it from there.
    if not host_manager.kernel.execution or not host_manager.kernel.execution._session_manager:
        logger.error("SessionManager not found. This indicates an initialization issue.")
        raise HTTPException(
            status_code=503,
            detail="SessionManager is not available due to an internal error.",
        )
    return host_manager.kernel.execution._session_manager


async def get_current_project_root(
    host_manager: Aurite = Depends(get_host_manager),
) -> Path:
    """
    Dependency function to get the current project's root path
    from the Aurite instance.
    """
    if not host_manager.kernel.project_root:
        logger.error(
            "Current project root not available via host_manager.project_root. "
            "This indicates an initialization issue or no active project."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Project context is not fully initialized or no project is active. Cannot determine project root.",
        )
    return host_manager.kernel.project_root
