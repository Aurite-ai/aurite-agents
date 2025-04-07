"""
Global pytest configuration and fixtures for Aurite MCP testing.

This module provides shared fixtures and configurations for testing the Aurite MCP
framework, with special attention to agent and workflow testing fixtures.
"""

import json
import logging
import pytest
import asyncio  # Added for event loop fixture

# Import fixtures from the fixtures directory to make them discoverable
# Note: Fixtures need to be imported, even if not directly used in conftest.py,
# for pytest to find them when running tests in other files.
from tests.fixtures.agent_fixtures import (
    minimal_agent_config,  # noqa: F401
    agent_config_filtered,  # noqa: F401 - Add this fixture
    agent_config_with_llm_params,  # noqa: F401
    # agent_config_with_mock_host, # This was correctly removed
)
from tests.fixtures.host_fixtures import mock_host_config, mock_mcp_host, real_mcp_host  # noqa: F401
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


# --- Event Loop Fixture ---


# Change scope to "function" for potentially safer async context management per test
@pytest.fixture(scope="function")
def event_loop(request):
    """Create an instance of the default event loop for each test function."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
