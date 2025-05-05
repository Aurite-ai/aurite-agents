"""
Server-level configuration settings loaded from environment variables,
and utilities for loading other configurations like HostConfig from JSON.
"""

import json
import logging
from typing import Optional, List, Dict, Tuple, Any # Added Any
from pathlib import Path

from pydantic import Field, FilePath, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Assuming models are accessible from here
from .host.models import (
    HostConfig,
    ClientConfig,
    RootConfig,
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    GCPSecretConfig,
)

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

    # Redis configuration (for worker)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_STREAM_NAME: str = "aurite:tasks"  # Default stream name for worker tasks


# Define project root relative to this file (src/config.py -> aurite-mcp/)
PROJECT_ROOT_DIR = Path(__file__).parent.parent.resolve()


# --- Private Helper Functions for Config Loading ---


def _load_client_configs(
    config_data: Dict[str, Any], config_path: Path
) -> List[ClientConfig]:
    """Loads and validates client configurations from the raw config data."""
    client_configs = []
    for client_data in config_data.get("clients", []):
        client_id = client_data.get("client_id", "UNKNOWN")
        try:
            # Resolve server_path relative to the project root directory
            raw_server_path = client_data.get("server_path")
            if not raw_server_path:
                raise KeyError(f"Missing 'server_path' for client_id: {client_id}")

            resolved_server_path = (PROJECT_ROOT_DIR / raw_server_path).resolve()
            if not resolved_server_path.exists():
                logger.warning(
                    f"Server path does not exist for client '{client_id}': {resolved_server_path}"
                )

            # Parse GCP secrets if present
            gcp_secrets_config = None
            if "gcp_secrets" in client_data and client_data["gcp_secrets"]:
                try:
                    gcp_secrets_config = [
                        GCPSecretConfig(**secret_data)
                        for secret_data in client_data["gcp_secrets"]
                    ]
                except (ValidationError, KeyError) as secret_err:
                    logger.error(
                        f"Error parsing 'gcp_secrets' for client '{client_id}': {secret_err}"
                    )
                    raise RuntimeError(
                        f"Invalid 'gcp_secrets' configuration for client '{client_id}': {secret_err}"
                    ) from secret_err

            client_configs.append(
                ClientConfig(
                    client_id=client_data["client_id"],
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
                    exclude=client_data.get("exclude", None),
                    gcp_secrets=gcp_secrets_config,
                )
            )
        except (ValidationError, KeyError) as client_err:
            logger.error(
                f"Client configuration validation failed for '{client_id}' in {config_path}: {client_err}"
            )
            raise RuntimeError(
                f"Client configuration validation failed for '{client_id}': {client_err}"
            ) from client_err
    return client_configs


def _load_agent_configs(
    config_data: Dict[str, Any], config_path: Path
) -> Dict[str, AgentConfig]:
    """Loads and validates agent configurations from the raw config data."""
    agent_configs_dict: Dict[str, AgentConfig] = {}
    for agent_data in config_data.get("agents", []):
        agent_name = agent_data.get("name")
        if not agent_name:
            logger.error(f"Agent definition missing 'name' in {config_path}")
            raise RuntimeError(f"Agent definition missing 'name' in {config_path}")

        try:
            # Convert string bools/numbers if necessary
            temperature = (
                float(agent_data["temperature"])
                if "temperature" in agent_data
                else None
            )
            max_tokens = (
                int(agent_data["max_tokens"]) if "max_tokens" in agent_data else None
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
                else include_history_str
            )
            evaluation = (
                str(agent_data["evaluation"]) if "evaluation" in agent_data else None
            )

            agent_config = AgentConfig(
                name=agent_name,
                client_ids=agent_data.get("client_ids"),
                system_prompt=agent_data.get("system_prompt"),
                model=agent_data.get("model"),
                temperature=temperature,
                max_tokens=max_tokens,
                max_iterations=max_iterations,
                include_history=include_history,
                exclude_components=agent_data.get("exclude_components"),
                evaluation=evaluation,
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
    return agent_configs_dict


def _load_workflow_configs(
    config_data: Dict[str, Any], config_path: Path
) -> Dict[str, WorkflowConfig]:
    """Loads and validates simple workflow configurations from the raw config data."""
    workflow_configs_dict: Dict[str, WorkflowConfig] = {}
    for workflow_data in config_data.get("workflows", []):
        workflow_name = workflow_data.get("name")
        if not workflow_name:
            logger.error(f"Workflow definition missing 'name' in {config_path}")
            raise RuntimeError(f"Workflow definition missing 'name' in {config_path}")

        steps = workflow_data.get("steps", [])
        if not steps:
            logger.warning(
                f"Workflow '{workflow_name}' has no steps defined in {config_path}"
            )

        try:
            workflow_config = WorkflowConfig(
                name=workflow_name,
                steps=steps,
                description=workflow_data.get("description"),
            )
            workflow_configs_dict[workflow_name] = workflow_config
        except ValidationError as workflow_val_err:
            logger.error(
                f"Workflow configuration validation failed for '{workflow_name}' in {config_path}: {workflow_val_err}"
            )
            raise RuntimeError(
                f"Workflow configuration validation failed for '{workflow_name}': {workflow_val_err}"
            ) from workflow_val_err
    return workflow_configs_dict


def _load_custom_workflow_configs(
    config_data: Dict[str, Any], config_path: Path
) -> Dict[str, CustomWorkflowConfig]:
    """Loads and validates custom workflow configurations from the raw config data."""
    custom_workflow_configs_dict: Dict[str, CustomWorkflowConfig] = {}
    for cwf_data in config_data.get("custom_workflows", []):
        cwf_name = cwf_data.get("name")
        module_path_str = cwf_data.get("module_path")
        class_name = cwf_data.get("class_name")

        if not cwf_name:
            logger.error(f"Custom workflow definition missing 'name' in {config_path}")
            raise RuntimeError(
                f"Custom workflow definition missing 'name' in {config_path}"
            )
        if not module_path_str:
            logger.error(
                f"Custom workflow '{cwf_name}' missing 'module_path' in {config_path}"
            )
            raise RuntimeError(
                f"Custom workflow '{cwf_name}' missing 'module_path' in {config_path}"
            )
        if not class_name:
            logger.error(
                f"Custom workflow '{cwf_name}' missing 'class_name' in {config_path}"
            )
            raise RuntimeError(
                f"Custom workflow '{cwf_name}' missing 'class_name' in {config_path}"
            )

        # Resolve module_path relative to project root
        resolved_module_path = (PROJECT_ROOT_DIR / module_path_str).resolve()
        if not resolved_module_path.exists():
            logger.warning(
                f"Custom workflow module path does not exist for '{cwf_name}': {resolved_module_path}"
            )

        try:
            custom_workflow_config = CustomWorkflowConfig(
                name=cwf_name,
                module_path=resolved_module_path,
                class_name=class_name,
                description=cwf_data.get("description"),
            )
            custom_workflow_configs_dict[cwf_name] = custom_workflow_config
        except ValidationError as cwf_val_err:
            logger.error(
                f"Custom workflow configuration validation failed for '{cwf_name}' in {config_path}: {cwf_val_err}"
            )
            raise RuntimeError(
                f"Custom workflow configuration validation failed for '{cwf_name}': {cwf_val_err}"
            ) from cwf_val_err
    return custom_workflow_configs_dict


# --- Main HostConfig Loading Utility ---


def load_host_config_from_json(
    config_path: Path,
) -> Tuple[
    HostConfig,
    Dict[str, AgentConfig],
    Dict[str, WorkflowConfig],
    Dict[str, CustomWorkflowConfig],
]:
    """
    Loads MCP Host, Agent, Workflow, and Custom Workflow configurations from a JSON file,
    validates them, and resolves relative paths using helper functions.

    Args:
        config_path: The path to the JSON configuration file.

    Returns:
        A tuple containing:
            - A validated HostConfig object.
            - A dictionary mapping agent names to validated AgentConfig objects.
            - A dictionary mapping workflow names to validated WorkflowConfig objects.
            - A dictionary mapping custom workflow names to validated CustomWorkflowConfig objects.

    Raises:
        FileNotFoundError: If the config file does not exist.
        RuntimeError: If JSON parsing, Pydantic validation, or required keys are missing.
    """
    logger.debug(f"Attempting to load HostConfig from: {config_path}")
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
        # Load components using helper functions
        client_configs = _load_client_configs(config_data, config_path)
        agent_configs_dict = _load_agent_configs(config_data, config_path)
        workflow_configs_dict = _load_workflow_configs(config_data, config_path)
        custom_workflow_configs_dict = _load_custom_workflow_configs(
            config_data, config_path
        )

        # Create the HostConfig Pydantic model
        host_pydantic_config = HostConfig(
            name=config_data.get("name"),  # Allow optional host name
            clients=client_configs,
        )
        logger.debug(f"HostConfig loaded successfully from {config_path}")

        # Log counts
        logger.debug(
            f"{len(agent_configs_dict)} AgentConfig(s) loaded successfully from {config_path}"
        )
        logger.debug(
            f"{len(workflow_configs_dict)} WorkflowConfig(s) loaded successfully from {config_path}"
        )
        logger.debug(
            f"{len(custom_workflow_configs_dict)} CustomWorkflowConfig(s) loaded successfully from {config_path}"
        )

        return (
            host_pydantic_config,
            agent_configs_dict,
            workflow_configs_dict,
            custom_workflow_configs_dict,
        )

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
