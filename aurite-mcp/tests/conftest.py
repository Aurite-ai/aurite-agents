"""
Global pytest configuration and fixtures for Aurite MCP testing.

This module provides shared fixtures and configurations for testing the Aurite MCP
framework, with special attention to agent and workflow testing fixtures.
"""

import json
import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import mcp.types as types
from mcp import ClientSession

# Import Aurite components
from src.host.host import MCPHost, HostConfig, ClientConfig
from src.host.resources.tools import ToolManager
from src.host.foundation import RootManager, SecurityManager
from src.host.communication import MessageRouter

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Global Setup and Teardown ---


def pytest_configure(config):
    """Configure pytest environment."""
    logger.info("Setting up test environment")
    # Setup can be expanded as needed


def pytest_unconfigure(config):
    """Clean up after all tests have run."""
    logger.info("Tearing down test environment")
    # Cleanup can be expanded as needed


# --- Host Testing Infrastructure ---


@pytest.fixture
async def mock_mcp_host():
    """
    Create a mock MCPHost for testing agent functionality.

    Returns a configured but not initialized host for testing.
    """
    pass


@pytest.fixture
def parse_json_result():
    """Utility function to parse JSON results from tool executions."""

    def _parse(result):
        """Parse JSON from tool result text content."""
        if isinstance(result, list) and len(result) > 0:
            text_content = result[0]
            if hasattr(text_content, "text"):
                try:
                    return json.loads(text_content.text.strip())
                except json.JSONDecodeError:
                    return {"error": "Failed to parse JSON", "raw": text_content.text}
        return {"error": "Invalid result format", "raw": str(result)}

    return _parse
