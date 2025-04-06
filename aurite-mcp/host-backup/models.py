"""
Configuration classes and utilities for MCP Host and clients.

This module provides:
1. Configuration models for Host, Client, and Root settings
2. JSON configuration loading and validation
3. Helper functions for working with config files
"""

import logging
from typing import List, TypeVar
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


class HostConfig(BaseModel):
    """Configuration for the MCP host"""

    clients: List[ClientConfig]
    enable_memory: bool = False  # Feature flag for memory client


# Type variable for generic config loading
T = TypeVar("T")


# Removed ConfigurationManager class as it is deprecated and its functionality
# for loading storage config is now handled directly in StorageManager.
# Other potential uses (like workflow config) are not currently implemented
# or will be handled differently.
