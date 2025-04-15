"""
Configuration classes and utilities for MCP Host and clients.

This module provides:
1. Configuration models for Host, Client, and Root settings
2. JSON configuration loading and validation
3. Helper functions for working with config files
"""

import logging
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field  # Added Field

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
    server_path: Path
    roots: List[RootConfig]
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


class HostConfig(BaseModel):
    """Configuration for the MCP host"""

    clients: List[ClientConfig]
    name: Optional[str]


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
    # Agent-specific LLM parameters (override host/defaults if provided)
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    max_iterations: Optional[int] = None  # Max conversation turns before stopping
    include_history: Optional[bool] = (
        None  # Whether to include the conversation history, or just the latest message
    )
    # List of component names (tool, prompt, resource) to specifically exclude for this agent
    exclude_components: Optional[List[str]] = Field(
        None,
        description="List of component names (tool, prompt, resource) to specifically exclude for this agent, even if provided by allowed clients.",
    )


class WorkflowConfig(BaseModel):
    """
    Configuration for a simple, sequential agent workflow.
    """

    name: str
    steps: List[str]  # List of agent names (must match keys in loaded AgentConfig dict)
    description: Optional[str] = None


class CustomWorkflowConfig(BaseModel):
    """
    Configuration for a custom Python-based workflow.
    """

    name: str
    module_path: Path  # Resolved absolute path to the python file
    class_name: str  # Name of the class within the file implementing the workflow
    description: Optional[str] = None
