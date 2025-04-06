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

# Base configuration directory
CONFIG_DIR = Path(__file__).parents[2] / "config"


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

    name: Optional[str]
    clients: List[ClientConfig]


class AgentConfig(BaseModel):
    """Configuration for an Agent"""

    ## Host Properties (defines roots and available prompts, resources, tools)
    name: Optional[str]
    host: Optional[HostConfig]
    ## LLM Properties (defines LLM properties)
    system_prompt: Optional[str]
    model: Optional[str]
    temperature: Optional[float]
    include_history: Optional[
        bool
    ]  # Whether to include the conversation history, or just the latest message


# Type variable for generic config loading
T = TypeVar("T")


# Removed ConfigurationManager class as it is deprecated and its functionality
# for loading storage config is now handled directly in StorageManager.
# Other potential uses (like workflow config) are not currently implemented
# or will be handled differently.
