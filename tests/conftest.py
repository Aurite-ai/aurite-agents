"""
Global pytest configuration and fixtures for Aurite MCP testing.

This module provides shared fixtures and configurations for testing the Aurite MCP
framework.
"""

import json
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.aurite.config.config_models import HostConfig

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Global Setup and Teardown ---

# Markers are now defined in pyproject.toml


# --- AnyIO Backend Configuration ---


@pytest.fixture(scope="session")
def anyio_backend():
    """
    Explicitly configure AnyIO to use the asyncio backend globally for all tests.
    This overrides the default behavior of pytest-anyio trying to run on all
    supported backends.
    """
    return "asyncio"


# --- Utility Fixtures ---


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


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--config",
        action="store",
        default=None,
        help="The config file to use located in config/testing/ (e.g. planning_agent.json)",
    )


@pytest.fixture
def host_config() -> HostConfig:
    """
    Provides a default HostConfig object for tests.
    """
    return HostConfig(name="test_host", mcp_servers=[])


@pytest.fixture
def mock_client_session_group() -> MagicMock:
    """
    Provides a reusable MagicMock for the ClientSessionGroup.
    This mock can be used to simulate the behavior of the session group
    without making actual network connections.
    """
    mock_group = MagicMock()
    mock_group.__aenter__.return_value = None
    mock_group.__aexit__.return_value = None
    mock_group.connect_to_server = AsyncMock()
    mock_group.call_tool = AsyncMock()
    mock_group.prompts = {}
    mock_group.resources = {}
    mock_group.tools = {}
    mock_group.sessions = {}
    return mock_group
