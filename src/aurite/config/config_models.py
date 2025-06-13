"""
Configuration classes and utilities for MCP Host and clients.
These models define the structure of the configuration files used to set up the MCP environment, including client and root configurations, as well as LLM and agent settings.

This module provides:
1. Configuration models for Host, Client, and Root settings
2. JSON configuration loading and validation
3. Helper functions for working with config files
"""

import logging
from typing import Any, List, Optional, Dict, Literal  # Added Dict and Literal
from pathlib import Path
from pydantic import BaseModel, Field, model_validator  # Use model_validator

logger = logging.getLogger(__name__)


class RootConfig(BaseModel):
    """Configuration for an MCP root"""

    uri: str = Field(description="The URI of the root.")
    name: str = Field(description="The name of the root.")
    capabilities: List[str] = Field(
        description="A list of capabilities provided by this root."
    )


class GCPSecretConfig(BaseModel):
    """Configuration for a single GCP Secret to resolve."""

    secret_id: str = Field(
        ...,
        description="Full GCP Secret Manager secret ID (e.g., projects/my-proj/secrets/my-secret/versions/latest)",
    )
    env_var_name: str = Field(
        ..., description="Environment variable name to map the secret value to"
    )


class ClientConfig(BaseModel):
    """Configuration for an MCP client"""

    name: str = Field(description="Unique name for the MCP server client.")
    transport_type: Optional[Literal["stdio", "http_stream", "local"]] = Field(
        default=None, description="The transport type for the client."
    )
    server_path: Optional[Path | str] = Field(
        default=None, description="Path to the server script for 'stdio' transport."
    )
    http_endpoint: Optional[str] = Field(
        default=None, description="URL endpoint for 'http_stream' transport."
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="HTTP headers for 'http_stream' transport."
    )
    command: Optional[str] = Field(
        default=None, description="The command to run for 'local' transport."
    )
    args: Optional[List[str]] = Field(
        default=None, description="Arguments for the 'local' transport command."
    )
    roots: List[RootConfig] = Field(
        default_factory=list, description="List of root configurations for this client."
    )
    capabilities: List[str] = Field(
        description="List of capabilities this client provides (e.g., 'tools', 'prompts')."
    )
    timeout: float = Field(
        default=10.0, description="Default timeout in seconds for client operations."
    )
    routing_weight: float = Field(
        default=1.0, description="Weight for server selection during routing."
    )
    exclude: Optional[List[str]] = Field(
        default=None,
        description="List of component names (prompt, resource, tool) to exclude from this client.",
    )
    gcp_secrets: Optional[List[GCPSecretConfig]] = Field(
        default=None,
        description="List of GCP secrets to resolve and inject into the server environment",
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
                raise ValueError(
                    "`http_endpoint` is required for 'http_stream' transport"
                )
            if server_path is not None or command is not None:
                raise ValueError(
                    "Only `http_endpoint` is allowed for 'http_stream' transport"
                )
        elif transport_type == "local":
            if command is None:
                raise ValueError("`command` is required for 'local' transport")
            # `args` are optional for local, so we don't need to check them here.
            if server_path is not None or http_endpoint is not None:
                raise ValueError(
                    "Only `command` and `args` are allowed for 'local' transport"
                )
        else:
            raise ValueError(
                "Could not determine transport type. Please provide one of: "
                "'server_path' (for stdio), 'http_endpoint' (for http_stream), or 'command' (for local)."
            )

        return values


class HostConfig(BaseModel):
    """Configuration for the MCP host"""

    mcp_servers: List[ClientConfig] = Field(
        description="A list of MCP server client configurations."
    )
    name: Optional[str] = Field(default=None, description="The name of the host.")
    description: Optional[str] = Field(
        default=None, description="A description of the host."
    )


class WorkflowComponent(BaseModel):
    name: str = Field(description="The name of the component in the workflow step.")
    type: Literal["agent", "simple_workflow", "custom_workflow"] = Field(
        description="The type of the component."
    )


class WorkflowConfig(BaseModel):
    """
    Configuration for a simple, sequential agent workflow.
    """

    name: str = Field(description="The unique name of the workflow.")
    steps: List[str | WorkflowComponent] = Field(
        description="List of component names or component objects to execute in sequence."
    )
    description: Optional[str] = Field(
        default=None, description="A description of the workflow."
    )


# --- LLM Configuration ---


class LLMConfig(BaseModel):
    """Configuration for a specific LLM setup."""

    llm_id: str = Field(description="Unique identifier for this LLM configuration.")
    provider: str = Field(
        default="anthropic",
        description="The LLM provider (e.g., 'anthropic', 'openai', 'gemini').",
    )
    model_name: Optional[str] = Field(
        None, description="The specific model name for the provider."
    )  # Made optional

    # Common LLM parameters
    temperature: Optional[float] = Field(
        default=0.7, description="Default sampling temperature."
    )
    max_tokens: Optional[int] = Field(
        default=None, description="Default maximum tokens to generate."
    )
    default_system_prompt: Optional[str] = Field(
        default="You are a helpful AI Assistant.",
        description="A default system prompt for this LLM configuration.",
    )

    # Provider-specific settings (Example - adjust as needed)
    # api_key_env_var: Optional[str] = Field(None, description="Environment variable name for the API key (if not using default like ANTHROPIC_API_KEY).")
    # credentials_path: Optional[Path] = Field(None, description="Path to credentials file for some providers.")

    class Config:
        extra = "allow"  # Allow provider-specific fields not explicitly defined


# --- Agent Configuration ---


class AgentConfig(BaseModel):
    """
    Configuration for an Agent instance.

    Defines agent-specific settings and links to the host configuration
    that provides the necessary MCP clients and capabilities.
    """

    # Optional name for the agent instance
    name: Optional[str] = Field(
        default=None, description="A unique name for the agent instance."
    )
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
    llm_config_id: Optional[str] = Field(
        default=None, description="ID of the LLMConfig to use for this agent."
    )
    # --- LLM Overrides (Optional) ---
    # Agent-specific LLM parameters (override LLMConfig or act as primary if no llm_config_id)
    system_prompt: Optional[str] = Field(
        default=None, description="The primary system prompt for the agent."
    )
    config_validation_schema: Optional[dict[str, Any]] = Field(
        default=None,
        description="JSON schema for validating agent-specific configurations.",
    )
    model: Optional[str] = Field(
        default=None, description="Overrides model_name from LLMConfig if specified."
    )
    temperature: Optional[float] = Field(
        default=None, description="Overrides temperature from LLMConfig if specified."
    )
    max_tokens: Optional[int] = Field(
        default=None, description="Overrides max_tokens from LLMConfig if specified."
    )
    # --- Agent Behavior ---
    max_iterations: Optional[int] = Field(
        default=None, description="Max conversation turns before stopping."
    )
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


class CustomWorkflowConfig(BaseModel):
    """
    Configuration for a custom Python-based workflow.
    """

    name: str = Field(description="The unique name of the custom workflow.")
    module_path: Path = Field(
        description="Resolved absolute path to the Python file containing the workflow class."
    )
    class_name: str = Field(
        description="Name of the class within the module that implements the workflow."
    )
    description: Optional[str] = Field(
        default=None, description="A description of the custom workflow."
    )


# --- Project Configuration ---


class ProjectConfig(BaseModel):
    """
    Defines the overall configuration for a specific project, including
    all its components (clients, LLMs, agents, workflows).
    This is typically loaded from a project file (e.g., config/projects/my_project.json)
    and may reference component configurations defined elsewhere.
    """

    name: str = Field(description="The unique name of the project.")
    description: Optional[str] = Field(
        None, description="A brief description of the project."
    )
    mcp_servers: Dict[str, ClientConfig] = Field(
        default_factory=dict,
        description="Defines MCP Servers available within this project.",
    )
    llms: Dict[str, LLMConfig] = Field(  # Renamed from llm_configs
        default_factory=dict,
        description="LLM configurations available within this project.",
    )
    agents: Dict[str, AgentConfig] = Field(
        default_factory=dict,
        description="Agents defined or referenced by this project.",
    )
    simple_workflows: Dict[str, WorkflowConfig] = Field(
        default_factory=dict,
        description="Simple workflows defined or referenced by this project.",
    )
    custom_workflows: Dict[str, CustomWorkflowConfig] = Field(
        default_factory=dict,
        description="Custom workflows defined or referenced by this project.",
    )
