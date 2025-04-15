"""
Global pytest configuration and fixtures for Aurite MCP testing.

This module provides shared fixtures and configurations for testing the Aurite MCP
framework, with special attention to agent and workflow testing fixtures.
"""

import json
import logging
import pytest
# import asyncio # Removed - anyio plugin handles the loop

# Import fixtures from the fixtures directory to make them discoverable
# Note: Fixtures need to be imported, even if not directly used in conftest.py,
# for pytest to find them when running tests in other files.
from tests.fixtures.agent_fixtures import (
    minimal_agent_config,  # noqa: F401
    agent_config_filtered,  # noqa: F401 - Add this fixture
    agent_config_with_llm_params,  # noqa: F401
    # agent_config_with_mock_host, # This was correctly removed
)
from tests.fixtures.host_fixtures import (
    mock_host_config,  # noqa: F401
    mock_mcp_host,  # noqa: F401
    host_manager,  # noqa: F401 - Import the new fixture
)
# Import weather server fixture explicitly if needed globally, otherwise tests import directly
# from tests.fixtures.servers.weather_mcp_server import weather_mcp_server_fixture # noqa: F401

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Global Setup and Teardown ---


def pytest_configure(config):
    """Configure pytest environment, register markers."""
    logger.info("Setting up test environment")
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (component interaction)",
    )
    config.addinivalue_line(
        "markers",
        "e2e: marks tests as end-to-end tests (may require external resources)",
    )
    # Setup can be expanded as needed


def pytest_unconfigure(config):
    """Clean up after all tests have run."""
    logger.info("Tearing down test environment")
    # Cleanup can be expanded as needed


# --- AnyIO Backend Configuration ---


@pytest.fixture(scope="session")
def anyio_backend():
    """
    Configure AnyIO to use the asyncio backend globally for all tests.
    This fixture is session-scoped as recommended by AnyIO for potentially
    sharing resources across tests if higher-scoped async fixtures are used later.
    """
    # Options can be added here if needed, e.g., {'use_uvloop': True}
    return "asyncio"


# Removed the explicit event_loop fixture as the anyio plugin manages it.

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
        "--config", action="store", default=None, help="The config file to use located in config/testing/ (e.g. planning_agent.json)"
    )