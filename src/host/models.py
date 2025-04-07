"""
Configuration classes and utilities for MCP Host and clients.

This module provides:
1. Configuration models for Host, Client, and Root settings
2. JSON configuration loading and validation
3. Helper functions for working with config files
"""

import logging
from typing import List, TypeVar, Optional
from pathlib import Path
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RootConfig(BaseModel):
    """Configuration for an MCP root"""

    uri: str
    name: str
    capabilities: List[str]


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
    host: Optional[HostConfig] = None
    # Agent-specific LLM parameters (override host/defaults if provided)
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    max_iterations: Optional[int] = None  # Max conversation turns before stopping
    include_history: Optional[bool] = (
        None  # Whether to include the conversation history, or just the latest message
    )
