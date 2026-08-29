import logging
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security, status  # Added status
from fastapi.security import APIKeyHeader
from pydantic import ValidationError

from ..aurite import Aurite  # Needed for get_aurite
from ..execution.aurite_engine import AuriteEngine
from ..execution.mcp_host.mcp_host import MCPHost  # Added for get_host
from ..lib.config.config_manager import ConfigManager

# Import config/models needed by dependencies
from ..lib.models.api.server import ServerConfig
from ..lib.storage.sessions.session_manager import SessionManager
from ..testing.qa.qa_engine import QAEngine
from ..testing.security.security_engine import SecurityEngine

logger = logging.getLogger(__name__)

# --- Project Root ---
# The project root is now determined by the Aurite instance's ConfigManager,
# which finds the nearest `.aurite` file. This makes the API project-aware.
PROJECT_ROOT = Path.cwd()


def _format_validation_error_message(validation_error: ValidationError) -> str:
    """
    Convert Pydantic ValidationError into a user-friendly error message.

    Args:
        validation_error: The ValidationError from Pydantic

    Returns:
        A formatted, user-friendly error message with setup instructions
    """
    missing_fields = []
    error_details = []

    for error in validation_error.errors():
        field_name = error.get("loc", ["unknown"])[0] if error.get("loc") else "unknown"
        error_type = error.get("type", "unknown")

        if error_type == "missing":
            missing_fields.append(field_name)
        else:
            error_details.append(f"{field_name}: {error.get('msg', 'validation error')}")

    # Build user-friendly message
    message_parts = []

    if missing_fields:
        message_parts.append("Missing required environment variables:")
        for field in missing_fields:
            if field == "API_KEY":
                message_parts.append(f"  • {field} - Required for API authentication")
                message_parts.append("    Example: API_KEY=your_secret_key_here")
            elif field == "ENCRYPTION_KEY":
                message_parts.append(f"  • {field} - Required for data encryption")
                message_parts.append("    Example: ENCRYPTION_KEY=your_encryption_key_here")
            else:
                message_parts.append(f"  • {field}")

    if error_details:
        if missing_fields:
            message_parts.append("")
        message_parts.append("Configuration errors:")
        for detail in error_details:
            message_parts.append(f"  • {detail}")

    # Add setup instructions
    message_parts.extend(
        [
            "",
            "To fix this:",
            "1. Create a .env file in your project root, or",
            "2. Set the environment variables in your shell",
            "",
            "For more information, see the installation guide:",
            "https://docs.aurite.ai/getting-started/installation/",
        ]
    )

    return "\n".join(message_parts)


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
        logger.debug("Server configuration loaded successfully.")
        logging.getLogger().setLevel(config.LOG_LEVEL.upper())
        return config
    except ValidationError as e:
        # Handle Pydantic validation errors with user-friendly messages
        user_friendly_message = _format_validation_error_message(e)
        logger.error("Server configuration validation failed:")
        logger.error(user_friendly_message)

        # Only show stack trace in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Validation error details:", exc_info=True)

        raise RuntimeError(f"Server configuration error:\n{user_friendly_message}") from e
    except Exception as e:
        # Handle other configuration errors
        logger.error(f"Failed to load server configuration: {e}")

        # Only show stack trace in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Configuration error details:", exc_info=True)

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
async def get_aurite(request: Request) -> Aurite:
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
async def get_host(aurite: Aurite = Depends(get_aurite)) -> MCPHost:
    """
    Dependency function to get the MCPHost instance from the Aurite manager.
    """
    if not aurite.kernel.host:
        # This case should ideally not happen if Aurite is initialized correctly
        logger.error("MCPHost not found on Aurite instance. This indicates an initialization issue.")
        raise HTTPException(
            status_code=503,
            detail="MCPHost is not available due to an internal error.",
        )
    return aurite.kernel.host


# --- ConfigManager Dependency ---
async def get_config_manager(
    aurite: Aurite = Depends(get_aurite),
) -> ConfigManager:
    """
    Dependency function to get the ConfigManager instance from the Aurite manager.
    """
    return aurite.get_config_manager()


# --- AuriteEngine Dependency ---
async def get_execution_facade(
    aurite: Aurite = Depends(get_aurite),
) -> AuriteEngine:
    """
    Dependency function to get the AuriteEngine instance from the Aurite manager.
    """
    if not aurite.kernel.execution:
        # This case should ideally not happen if Aurite is initialized correctly
        logger.error("AuriteEngine not found on Aurite instance. This indicates an initialization issue.")
        raise HTTPException(
            status_code=503,
            detail="AuriteEngine is not available due to an internal error.",
        )
    return aurite.kernel.execution


# --- SessionManager Dependency ---
async def get_session_manager(
    aurite: Aurite = Depends(get_aurite),
) -> SessionManager:
    """
    Dependency function to get the SessionManager instance from the Aurite manager.
    """
    # The SessionManager is now created and held by the AuriteEngine.
    # This dependency retrieves it from there.
    if not aurite.kernel.execution or not aurite.kernel.execution._session_manager:
        logger.error("SessionManager not found. This indicates an initialization issue.")
        raise HTTPException(
            status_code=503,
            detail="SessionManager is not available due to an internal error.",
        )
    return aurite.kernel.execution._session_manager


async def get_current_project_root(
    aurite: Aurite = Depends(get_aurite),
) -> Path:
    """
    Dependency function to get the current project's root path
    from the Aurite instance.
    """
    if not aurite.kernel.project_root:
        logger.error(
            "Current project root not available via aurite.project_root. "
            "This indicates an initialization issue or no active project."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Project context is not fully initialized or no project is active. Cannot determine project root.",
        )
    return aurite.kernel.project_root


# --- QA Engine Dependency ---
_qa_engine_instance: Optional[QAEngine] = None


async def get_qa_engine(
    config_manager: ConfigManager = Depends(get_config_manager),
    session_manager: SessionManager = Depends(get_session_manager),
) -> QAEngine:
    """
    Dependency function to get or create QAEngine instance with QASessionManager.
    """
    global _qa_engine_instance

    if _qa_engine_instance is None:
        # Import QASessionManager here to avoid circular imports
        from ..testing.qa.qa_session_manager import QASessionManager

        # Create QASessionManager wrapper around SessionManager
        qa_session_manager = QASessionManager(session_manager=session_manager)

        # Create QAEngine with both managers
        _qa_engine_instance = QAEngine(config_manager=config_manager, session_manager=qa_session_manager)
        logger.info("QAEngine instance created with ConfigManager and QASessionManager")

    return _qa_engine_instance


# --- Security Engine Dependency ---
_security_engine_instance: Optional[SecurityEngine] = None


async def get_security_engine(
    config_manager: ConfigManager = Depends(get_config_manager),
) -> SecurityEngine:
    """
    Dependency function to get or create SecurityEngine instance.
    """
    global _security_engine_instance

    if _security_engine_instance is None:
        from ..testing.security.security_models import create_default_security_config, load_security_config_from_dict

        # Try to load security config from ConfigManager
        security_config = None
        try:
            security_config_dict = config_manager.get_config("security", "default")
            if security_config_dict and "config_dict" in security_config_dict:
                security_config = load_security_config_from_dict(security_config_dict["config_dict"])
                logger.info("Loaded security configuration from ConfigManager")
        except Exception as e:
            logger.warning(f"Could not load security config from ConfigManager: {e}")

        # Fall back to default if no config found
        if security_config is None:
            security_config = create_default_security_config()
            logger.info("Using default security configuration")

        _security_engine_instance = SecurityEngine(security_config, config_manager)
        logger.info("SecurityEngine instance created")

    return _security_engine_instance
