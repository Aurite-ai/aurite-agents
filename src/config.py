"""
Server-level configuration settings loaded from environment variables,
and utilities for loading other configurations like HostConfig from JSON.
"""

import json
import logging
from typing import Optional, List, Dict, Tuple  # Added Dict, Tuple
from pathlib import Path

from pydantic import Field, FilePath, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Assuming models are accessible from here
from .host.models import (
    HostConfig,
    ClientConfig,
    RootConfig,
    AgentConfig,
)  # Added AgentConfig

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


# --- HostConfig Loading Utility ---

# Define project root relative to this file (src/config.py -> aurite-mcp/)
PROJECT_ROOT_DIR = Path(__file__).parent.parent.resolve()


def load_host_config_from_json(
    config_path: Path,
) -> Tuple[HostConfig, Dict[str, AgentConfig]]:
    """
    Loads MCP Host and Agent configurations from a JSON file, validates them,
    and resolves relative server paths for clients.

    Args:
        config_path: The path to the JSON configuration file.

    Returns:
        A tuple containing:
            - A validated HostConfig object.
            - A dictionary mapping agent names to validated AgentConfig objects.

    Raises:
        FileNotFoundError: If the config file does not exist.
        RuntimeError: If JSON parsing, Pydantic validation, or required keys are missing.
    """
    logger.info(f"Attempting to load HostConfig from: {config_path}")
    if not config_path.is_file():
        logger.error(f"Host configuration file not found: {config_path}")
        raise FileNotFoundError(f"Host configuration file not found: {config_path}")

    try:
        with open(config_path, "r") as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing configuration file {config_path}: {e}")
        raise RuntimeError(f"Error parsing configuration file: {e}") from e

    try:
        # --- Load Client Configs ---
        client_configs = []
        for client_data in config_data.get("clients", []):
            # Resolve server_path relative to the project root directory
            raw_server_path = client_data.get("server_path")
            if not raw_server_path:
                raise KeyError(
                    f"Missing 'server_path' for client_id: {client_data.get('client_id', 'UNKNOWN')}"
                )

            resolved_server_path = (PROJECT_ROOT_DIR / raw_server_path).resolve()
            if not resolved_server_path.exists():
                logger.warning(
                    f"Server path does not exist for client '{client_data.get('client_id', 'UNKNOWN')}': {resolved_server_path}"
                )
                # Decide if this should be a fatal error or just a warning
                # For now, let's allow it but log a warning. Pydantic might still fail if Path validation is strict.

            client_configs.append(
                ClientConfig(
                    client_id=client_data[
                        "client_id"
                    ],  # Let potential KeyError raise here
                    server_path=resolved_server_path,
                    roots=[
                        RootConfig(
                            uri=root["uri"],
                            name=root["name"],
                            capabilities=root["capabilities"],
                        )
                        for root in client_data.get("roots", [])
                    ],
                    capabilities=client_data.get("capabilities", []),
                    timeout=client_data.get("timeout", 10.0),
                    routing_weight=client_data.get("routing_weight", 1.0),
                    exclude=client_data.get("exclude", None),  # Include exclude field
                )
            )

        # Create the HostConfig Pydantic model
        host_pydantic_config = HostConfig(
            name=config_data.get("name"),  # Allow optional host name
            clients=client_configs,
        )
        logger.info(f"HostConfig loaded successfully from {config_path}")

        # --- Load Agent Configs ---
        agent_configs_dict: Dict[str, AgentConfig] = {}
        for agent_data in config_data.get("agents", []):
            agent_name = agent_data.get("name")
            if not agent_name:
                logger.error(f"Agent definition missing 'name' in {config_path}")
                raise RuntimeError(f"Agent definition missing 'name' in {config_path}")

            # Convert string bools/numbers if necessary (Pydantic usually handles this, but explicit is safer)
            try:
                temperature = (
                    float(agent_data["temperature"])
                    if "temperature" in agent_data
                    else None
                )
                max_tokens = (
                    int(agent_data["max_tokens"])
                    if "max_tokens" in agent_data
                    else None
                )
                max_iterations = (
                    int(agent_data["max_iterations"])
                    if "max_iterations" in agent_data
                    else None
                )
                include_history_str = agent_data.get("include_history")
                include_history = (
                    include_history_str.lower() == "true"
                    if isinstance(include_history_str, str)
                    else include_history_str  # Assume bool if not str
                )

                agent_config = AgentConfig(
                    name=agent_name,
                    client_ids=agent_data.get("client_ids"),  # Added
                    system_prompt=agent_data.get("system_prompt"),
                    model=agent_data.get("model"),
                    temperature=temperature,
                    max_tokens=max_tokens,
                    max_iterations=max_iterations,
                    include_history=include_history,
                )
                agent_configs_dict[agent_name] = agent_config
            except (ValueError, TypeError) as conv_err:
                logger.error(
                    f"Error converting agent parameter for '{agent_name}' in {config_path}: {conv_err}"
                )
                raise RuntimeError(
                    f"Invalid parameter type for agent '{agent_name}': {conv_err}"
                ) from conv_err
            except ValidationError as agent_val_err:
                logger.error(
                    f"Agent configuration validation failed for '{agent_name}' in {config_path}: {agent_val_err}"
                )
                raise RuntimeError(
                    f"Agent configuration validation failed for '{agent_name}': {agent_val_err}"
                ) from agent_val_err

        logger.info(
            f"{len(agent_configs_dict)} AgentConfig(s) loaded successfully from {config_path}"
        )

        return host_pydantic_config, agent_configs_dict

    except ValidationError as e:
        # Catch validation errors during HostConfig creation specifically
        logger.error(f"Host configuration validation failed for {config_path}: {e}")
        raise RuntimeError(f"Host configuration validation failed: {e}") from e
    except KeyError as e:
        logger.error(
            f"Missing required key in configuration data from {config_path}: {e}"
        )
        raise RuntimeError(f"Missing required key in configuration data: {e}") from e
    except Exception as e:
        # Catch any other unexpected errors during loading
        logger.error(
            f"An unexpected error occurred loading config from {config_path}: {e}"
        )
        raise RuntimeError(f"Failed to load config: {e}") from e
