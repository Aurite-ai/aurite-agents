"""
Initialization file for the aurite.config package.

This makes 'aurite/config' a Python package and allows importing
key configuration elements directly from 'aurite.config'.

It also defines the ServerConfig (loaded from environment variables)
and the project's root directory.
"""

import logging
from typing import Optional, List
from pydantic import Field, FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Define project root relative to this __init__.py file (src/config/__init__.py -> aurite-agents/)
# PROJECT_ROOT_DIR = Path(__file__).parent.parent.parent.resolve()  # Go up one more level
# This static PROJECT_ROOT_DIR is being replaced by a dynamic `current_project_root`
# established by ProjectManager based on the main project config file's location.


class ServerConfig(BaseSettings):
    """
    Defines the configuration settings for the FastAPI server,
    loaded primarily from environment variables.
    """

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    LOG_LEVEL: str = "INFO"

    # Security settings
    # Ensure API_KEY and ENCRYPTION_KEY are set in the environment
    API_KEY: str = Field(..., description="API key required for accessing endpoints")
    ENCRYPTION_KEY: Optional[str] = Field(
        None, description="Key for data encryption (if used by host)"
    )
    ALLOWED_ORIGINS: List[str] = ["*"]  # Default to allow all, refine as needed

    # Host configuration path (Now refers to the *Project* config file)
    # Ensure PROJECT_CONFIG_PATH points to a valid project config JSON file
    PROJECT_CONFIG_PATH: FilePath = Field(
        "aurite_config.json",
        description="Path to the Project configuration JSON file (e.g., config/projects/default.json)",
    )

    # Pydantic-settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",  # Load .env file if present
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from environment
        case_sensitive=False,  # Environment variables are typically uppercase
    )

    # Redis configuration (for worker)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_STREAM_NAME: str = "aurite:tasks"  # Default stream name for worker tasks


# Expose the key elements for direct import from aurite.config
__all__ = [
    # "PROJECT_ROOT_DIR", # Removed as it's being replaced by dynamic project root
    "ServerConfig",
]
