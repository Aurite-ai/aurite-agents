"""
Reusable mocks for the MCPHost system, primarily for unit testing dependents.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Any

# Import the class we are mocking to ensure the mock spec matches
from src.host.host import MCPHost


@pytest.fixture
def mock_mcp_host() -> MagicMock:
    """
    Provides a reusable MagicMock for the MCPHost instance, suitable for
    unit testing components that depend on it (like HostManager).

    Configured with common attributes and methods needed for HostManager tests.
    """
    host_mock = MagicMock(spec=MCPHost)

    # --- Mock Attributes ---
    # Mock internal structures often checked by HostManager during registration
    host_mock._clients: Dict[str, MagicMock] = {
        "existing_client_1": MagicMock(),
        "existing_client_2": MagicMock(),
    }
    # Add other attributes if needed by tests (e.g., config)
    host_mock.config = MagicMock()  # Basic mock for the host config if accessed

    # --- Mock Methods ---
    # Mock async methods used by HostManager
    host_mock.register_client = AsyncMock()
    host_mock.initialize = AsyncMock()
    host_mock.shutdown = AsyncMock()

    # Mock synchronous methods if needed
    # host_mock.get_tool_details = MagicMock(return_value=...)

    # Configure return values or side effects as needed for specific test scenarios
    # Example: Make register_client raise an error for a specific ID
    # async def register_client_side_effect(config):
    #     if config.client_id == "fail_client":
    #         raise ValueError("Client registration failed")
    #     host_mock._clients[config.client_id] = MagicMock() # Simulate adding
    # host_mock.register_client.side_effect = register_client_side_effect

    return host_mock
