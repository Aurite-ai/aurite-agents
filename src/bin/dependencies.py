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
        config = ServerConfig()
        logger.info("Server configuration loaded successfully.")
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
            status_code=401,
            detail="API key required in X-API-Key header",
        )

    # Ensure API_KEY is loaded correctly
    expected_api_key = getattr(server_config, "API_KEY", None)
    if not expected_api_key:
        logger.error("API_KEY not found in server configuration.")
        raise HTTPException(
            status_code=500, detail="Server configuration error: API Key not set."
        )

    if not secrets.compare_digest(api_key_header_value, expected_api_key):
        logger.warning("Invalid API key received.")
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key",
        )
    return api_key_header_value


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
