"""
Configuration classes for MCP Host and clients.
"""

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class RootConfig:
    """Configuration for an MCP root"""

    uri: str
    name: str
    capabilities: List[str]


@dataclass
class ClientConfig:
    """Configuration for an MCP client"""

    client_id: str
    server_path: Path
    roots: List[RootConfig]
    capabilities: List[str]
    timeout: float = 10.0  # Default timeout in seconds
    routing_weight: float = 1.0  # Weight for server selection


@dataclass
class HostConfig:
    """Configuration for the MCP host"""

    clients: List[ClientConfig]
