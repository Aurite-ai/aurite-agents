"""
Configuration classes and utilities for MCP Host and clients.
These models define the structure of the configuration files used to set up the MCP environment, including client and root configurations, as well as LLM and agent settings.

This module provides:
1. Configuration models for Host, Client, and Root settings
2. JSON configuration loading and validation
3. Helper functions for working with config files
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional  # Added Dict and Literal

from pydantic import BaseModel, Field, model_validator  # Use model_validator

logger = logging.getLogger(__name__)


class BaseComponentConfig(BaseModel):
    """A base model for all components, providing common fields."""

    name: str = Field(description="The unique name of the component.")
    description: Optional[str] = Field(default=None, description="A brief description of the component.")


class RootConfig(BaseModel):
    """Configuration for an MCP root"""

    uri: str = Field(description="The URI of the root.")
    name: str = Field(description="The name of the root.")
    capabilities: List[str] = Field(description="A list of capabilities provided by this root.")


class ClientConfig(BaseComponentConfig):
    """Configuration for an MCP client"""

    type: Literal["mcp_server"] = "mcp_server"
    transport_type: Optional[Literal["stdio", "http_stream", "local"]] = Field(
        default=None, description="The transport type for the client."
    )
    server_path: Optional[Path | str] = Field(
        default=None, description="Path to the server script for 'stdio' transport."
    )
    http_endpoint: Optional[str] = Field(default=None, description="URL endpoint for 'http_stream' transport.")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers for 'http_stream' transport.")
    command: Optional[str] = Field(default=None, description="The command to run for 'local' transport.")
    args: Optional[List[str]] = Field(default=None, description="Arguments for the 'local' transport command.")
    roots: List[RootConfig] = Field(default_factory=list, description="List of root configurations for this client.")
    capabilities: List[str] = Field(description="List of capabilities this client provides (e.g., 'tools', 'prompts').")
    timeout: float = Field(default=10.0, description="Default timeout in seconds for client operations.")
    registration_timeout: float = Field(default=30.0, description="Timeout for registering the mcp client")
    routing_weight: float = Field(default=1.0, description="Weight for server selection during routing.")
    exclude: Optional[List[str]] = Field(
        default=None,
        description="List of component names (prompt, resource, tool) to exclude from this client.",
    )

    @model_validator(mode="before")
    @classmethod
    def infer_and_validate_transport_type(cls, data: Any) -> Any:
        """
        Converts `server_path` to a Path object if provided as a string.
        Infers transport_type based on provided fields if it's not set,
        and validates that the correct fields for the transport type are present.
        """
        if not isinstance(data, dict):
            return data  # Let other validators handle non-dict data

        # Convert server_path from str to Path if necessary, before validation
        if "server_path" in data and isinstance(data.get("server_path"), str):
            data["server_path"] = Path(data["server_path"])

        values = data  # Use 'values' for consistency with previous logic
        transport_type = values.get("transport_type")
        server_path = values.get("server_path")
        http_endpoint = values.get("http_endpoint")
        command = values.get("command")

        # --- Inference Logic ---
        if not transport_type:
            if command is not None:
                values["transport_type"] = "local"
            elif http_endpoint is not None:
                values["transport_type"] = "http_stream"
            elif server_path is not None:
                values["transport_type"] = "stdio"
            else:
                # If no transport can be inferred, validation will fail below.
                pass

        # Re-read transport_type after potential inference
        transport_type = values.get("transport_type")

        # --- Validation Logic ---
        if transport_type == "stdio":
            if server_path is None:
                raise ValueError("`server_path` is required for 'stdio' transport")
            if http_endpoint is not None or command is not None:
                raise ValueError("Only `server_path` is allowed for 'stdio' transport")
        elif transport_type == "http_stream":
            if http_endpoint is None:
                raise ValueError("`http_endpoint` is required for 'http_stream' transport")
            if server_path is not None or command is not None:
                raise ValueError("Only `http_endpoint` is allowed for 'http_stream' transport")
        elif transport_type == "local":
            if command is None:
                raise ValueError("`command` is required for 'local' transport")
            # `args` are optional for local, so we don't need to check them here.
            if server_path is not None or http_endpoint is not None:
                raise ValueError("Only `command` and `args` are allowed for 'local' transport")
        else:
            raise ValueError(
                "Could not determine transport type. Please provide one of: "
                "'server_path' (for stdio), 'http_endpoint' (for http_stream), or 'command' (for local)."
            )

        return values


class HostConfig(BaseComponentConfig):
    """Configuration for the MCP host"""

    type: Literal["host"] = "host"
    mcp_servers: List[ClientConfig] = Field(description="A list of MCP server client configurations.")


class WorkflowComponent(BaseModel):
    name: str = Field(description="The name of the component in the workflow step.")
    type: Literal["agent", "simple_workflow", "custom_workflow"] = Field(description="The type of the component.")


class WorkflowConfig(BaseComponentConfig):
    """
    Configuration for a simple, sequential agent workflow.
    """

    type: Literal["simple_workflow"] = "simple_workflow"
    steps: List[str | WorkflowComponent] = Field(
        description="List of component names or component objects to execute in sequence."
    )
    include_history: Optional[bool] = Field(
        default=None, description="If set, overrides the include_history setting for all agents in this workflow."
    )


# --- LLM Configuration ---


class LLMConfig(BaseComponentConfig):
    """Configuration for a specific LLM setup."""

    type: Literal["llm"] = "llm"
    provider: str = Field(description="The LLM provider (e.g., 'anthropic', 'openai', 'gemini').")
    model: str = Field(description="The specific model name for the provider.")

    # Common LLM parameters
    temperature: Optional[float] = Field(default=None, description="Default sampling temperature.")
    max_tokens: Optional[int] = Field(default=None, description="Default maximum tokens to generate.")
    default_system_prompt: Optional[str] = Field(
        default=None,
        description="A default system prompt for this LLM configuration.",
    )

    # Provider-specific settings (Example - adjust as needed)
    api_key_env_var: Optional[str] = Field(
        None, description="Environment variable name for the API key (if not using default like ANTHROPIC_API_KEY)."
    )
    # credentials_path: Optional[Path] = Field(None, description="Path to credentials file for some providers.")
    api_base: Optional[str] = Field(default=None, description="The base URL for the LLM.")
    # api_key: Optional[str] = Field(default=None, description="The API key for the LLM.")
    api_version: Optional[str] = Field(default=None, description="The API version for the LLM.")

    class Config:
        extra = "allow"  # Allow provider-specific fields not explicitly defined


class LLMConfigOverrides(BaseModel):
    """A model for agent-specific overrides of LLM parameters."""

    model: Optional[str] = Field(default=None, description="Overrides model from LLMConfig if specified.")
    temperature: Optional[float] = Field(default=None, description="Overrides temperature from LLMConfig if specified.")
    max_tokens: Optional[int] = Field(default=None, description="Overrides max_tokens from LLMConfig if specified.")
    system_prompt: Optional[str] = Field(default=None, description="The primary system prompt for the agent.")
    api_base: Optional[str] = Field(default=None, description="Overrides the base URL for the LLM.")
    api_key: Optional[str] = Field(default=None, description="Overrides the API key for the LLM.")
    api_version: Optional[str] = Field(default=None, description="Overrides the API version for the LLM.")

    class Config:
        extra = "allow"


# --- Agent Configuration ---


class AgentConfig(BaseComponentConfig):
    """
    Configuration for an Agent instance.

    Defines agent-specific settings and links to the host configuration
    that provides the necessary MCP clients and capabilities.
    """

    type: Literal["agent"] = "agent"
    # Link to the Host configuration defining available clients/capabilities
    # host: Optional[HostConfig] = None # Removed as AgentConfig is now loaded separately
    # List of client IDs this agent is allowed to use (for host filtering)
    mcp_servers: Optional[List[str]] = Field(
        default_factory=list,
        description="List of mcp_server names this agent can use.",
    )
    auto: Optional[bool] = Field(
        default=False,
        description="If true, an LLM will dynamically select client_ids for the agent at runtime.",
    )
    # --- LLM Selection ---
    llm_config_id: Optional[str] = Field(default=None, description="ID of the LLMConfig to use for this agent.")
    llm: Optional[LLMConfigOverrides] = Field(
        default=None, description="LLM parameters to override the base LLMConfig."
    )
    # --- LLM Overrides (Optional) ---
    # Agent-specific LLM parameters (override LLMConfig or act as primary if no llm_config_id)
    system_prompt: Optional[str] = Field(default=None, description="The primary system prompt for the agent.")
    config_validation_schema: Optional[dict[str, Any]] = Field(
        default=None,
        description="JSON schema for validating agent-specific configurations.",
    )
    # --- Agent Behavior ---
    max_iterations: Optional[int] = Field(default=50, description="Max conversation turns before stopping.")
    include_history: Optional[bool] = Field(
        default=None,
        description="Whether to include the conversation history, or just the latest message.",
    )
    # --- Component Filtering ---
    # List of component names (tool, prompt, resource) to specifically exclude for this agent
    exclude_components: Optional[List[str]] = Field(
        default=None,
        description="List of component names (tool, prompt, resource) to specifically exclude for this agent, even if provided by allowed clients.",
    )
    # --- Evaluation (Experimental/Specific Use Cases) ---
    evaluation: Optional[str] = Field(
        default=None,
        description="Optional runtime evaluation. Set to the name of a file in config/testing, or a prompt describing expected output for simple evaluation.",
    )


class CustomWorkflowConfig(BaseComponentConfig):
    """
    Configuration for a custom Python-based workflow.
    """

    type: Literal["custom_workflow"] = "custom_workflow"
    module_path: Path = Field(description="Resolved absolute path to the Python file containing the workflow class.")
    class_name: str = Field(description="Name of the class within the module that implements the workflow.")


# --- Project Configuration ---


class ProjectConfig(BaseComponentConfig):
    """
    Defines the overall configuration for a specific project, including
    all its components (clients, LLMs, agents, workflows).
    This is typically loaded from a project file (e.g., config/projects/my_project.json)
    and may reference component configurations defined elsewhere.
    """

    type: Literal["project"] = "project"
    mcp_servers: List[ClientConfig] = Field(
        default_factory=list,
        description="Defines MCP Servers available within this project.",
    )
    llms: List[LLMConfig] = Field(
        default_factory=list,
        description="LLM configurations available within this project.",
    )
    agents: List[AgentConfig] = Field(
        default_factory=list,
        description="Agents defined or referenced by this project.",
    )
    simple_workflows: List[WorkflowConfig] = Field(
        default_factory=list,
        description="Simple workflows defined or referenced by this project.",
    )
    custom_workflows: List[CustomWorkflowConfig] = Field(
        default_factory=list,
        description="Custom workflows defined or referenced by this project.",
    )
