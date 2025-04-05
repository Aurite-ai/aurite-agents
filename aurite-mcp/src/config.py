"""
Server-level configuration settings loaded from environment variables.
"""

import logging
from typing import Optional, List

from pydantic import Field, FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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

    # Host configuration path
    # Ensure HOST_CONFIG_PATH points to a valid host config JSON file
    HOST_CONFIG_PATH: FilePath = Field(
        ..., description="Path to the MCP Host configuration JSON file"
    )

    # Pydantic-settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",  # Load .env file if present
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from environment
        case_sensitive=False,  # Environment variables are typically uppercase
    )


# Example of how to load the config:
# try:
#     server_config = ServerConfig()
#     logger.info("Server configuration loaded successfully.")
#     # Access settings like server_config.API_KEY, server_config.HOST_CONFIG_PATH
# except ValidationError as e:
#     logger.error(f"Failed to load server configuration: {e}")
#     # Handle configuration error (e.g., exit application)
