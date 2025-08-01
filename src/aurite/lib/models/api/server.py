from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["ServerConfig"]


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
    ENCRYPTION_KEY: Optional[str] = Field(None, description="Key for data encryption (if used by host)")
    ALLOWED_ORIGINS: List[str] = ["*"]  # Default to allow all, refine as needed

    # Host configuration path (Now refers to the *Project* config file)

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
