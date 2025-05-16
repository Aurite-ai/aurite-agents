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
from pydantic import BaseModel, Field, root_validator  # Added Field and root_validator

logger = logging.getLogger(__name__)


class RootConfig(BaseModel):
    """Configuration for an MCP root"""

    uri: str
    name: str
    capabilities: List[str]


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

    client_id: str
    transport_type: Literal["stdio", "http_stream"] = "stdio"  # Use http_stream
    server_path: Optional[Path] = None
    http_endpoint: Optional[str] = None  # Use http_endpoint
    roots: Optional[List[RootConfig]] = None
    capabilities: List[str]
    timeout: float = 10.0  # Default timeout in seconds
    routing_weight: float = 1.0  # Weight for server selection
    exclude: Optional[List[str]] = (
        None  # List of component names (prompt, resource, tool) to exclude
    )
    gcp_secrets: Optional[List[GCPSecretConfig]] = Field(
        None,
        description="List of GCP secrets to resolve and inject into the server environment",
    )

    @root_validator(pre=False, skip_on_failure=True)
    def check_transport_specific_fields(cls, values):
        transport_type = values.get("transport_type")
        server_path = values.get("server_path")
        http_endpoint = values.get("http_endpoint")  # Use http_endpoint

        if transport_type == "stdio":
            if server_path is None:
                raise ValueError("server_path is required for stdio transport type")
        elif transport_type == "http_stream":  # Use http_stream
            if http_endpoint is None:
                raise ValueError(
                    "http_endpoint is required for http_stream transport type"
                )
            # Basic URL validation
            if not (
                http_endpoint.startswith("http://")
                or http_endpoint.startswith("https://")
            ):
                raise ValueError("http_endpoint must be a valid HTTP/HTTPS URL")
        return values


class HostConfig(BaseModel):
    """Configuration for the MCP host"""

    clients: List[ClientConfig]
    name: Optional[str] = None
    description: Optional[str] = None


class WorkflowConfig(BaseModel):
    """
    Configuration for a simple, sequential agent workflow.
    """

    name: str
    steps: List[str]  # List of agent names (must match keys in loaded AgentConfig dict)
    description: Optional[str] = None


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
        None, description="Default sampling temperature."
    )
    max_tokens: Optional[int] = Field(
        None, description="Default maximum tokens to generate."
    )
    default_system_prompt: Optional[str] = Field(
        None, description="A default system prompt for this LLM configuration."
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
    name: Optional[str] = None
    # Link to the Host configuration defining available clients/capabilities
    # host: Optional[HostConfig] = None # Removed as AgentConfig is now loaded separately
    # List of client IDs this agent is allowed to use (for host filtering)
    client_ids: Optional[List[str]] = None
    auto: Optional[bool] = Field(
        False,
        description="If true, an LLM will dynamically select client_ids for the agent at runtime.",
    )
    # --- LLM Selection ---
    llm_config_id: Optional[str] = Field(
        None, description="ID of the LLMConfig to use for this agent."
    )
    # --- LLM Overrides (Optional) ---
    # Agent-specific LLM parameters (override LLMConfig or act as primary if no llm_config_id)
    system_prompt: Optional[str] = None
    config_validation_schema: Optional[dict[str, Any]] = Field(  # Renamed again
        None,
        description="JSON schema for validating agent-specific configurations",
    )
    model: Optional[str] = Field(
        None, description="Overrides model_name from LLMConfig if specified."
    )
    temperature: Optional[float] = Field(
        None, description="Overrides temperature from LLMConfig if specified."
    )
    max_tokens: Optional[int] = Field(
        None, description="Overrides max_tokens from LLMConfig if specified."
    )
    # --- Agent Behavior ---
    max_iterations: Optional[int] = None  # Max conversation turns before stopping
    include_history: Optional[bool] = (
        None  # Whether to include the conversation history, or just the latest message
    )
    # --- Component Filtering ---
    # List of component names (tool, prompt, resource) to specifically exclude for this agent
    exclude_components: Optional[List[str]] = Field(
        None,
        description="List of component names (tool, prompt, resource) to specifically exclude for this agent, even if provided by allowed clients.",
    )
    # --- Evaluation (Experimental/Specific Use Cases) ---
    evaluation: Optional[str] = Field(
        None,
        description="Optional runtime evaluation. Set to the name of a file in config/testing, or a prompt describing expected output for simple evaluation.",
    )


class CustomWorkflowConfig(BaseModel):
    """
    Configuration for a custom Python-based workflow.
    """

    name: str
    module_path: Path  # Resolved absolute path to the python file
    class_name: str  # Name of the class within the file implementing the workflow
    description: Optional[str] = None


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
    clients: Dict[str, ClientConfig] = Field(
        default_factory=dict, description="Clients available within this project."
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
