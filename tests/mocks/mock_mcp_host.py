"""
Reusable mocks for the MCPHost system, primarily for unit testing dependents
like Aurite, Agent, and Executors.
"""

from unittest.mock import AsyncMock, MagicMock, Mock  # Added Mock

import pytest

# Import the class we are mocking to ensure the mock spec matches
from aurite.execution.mcp_host.host import MCPHost
from aurite.execution.mcp_host.resources import ToolManager  # Import ToolManager for spec


@pytest.fixture
def mock_mcp_host() -> MagicMock:
    """
    Provides a reusable MagicMock for the MCPHost instance, suitable for
    unit testing components that depend on it.

    Includes attributes/methods needed for Aurite, Agent, and Executor tests.
    Uses MagicMock for flexibility with async methods.
    """
    # Use MagicMock which handles async methods more gracefully by default
    # Restore spec=MCPHost to ensure isinstance checks pass
    host_mock = MagicMock(spec=MCPHost)

    # Configure the mock using configure_mock for specified methods/attributes
    host_mock.configure_mock(
        # === Attributes/Methods for Aurite Registration ===
        # Don't configure _clients here. Use is_client_registered mock instead.
        config=MagicMock(),
        register_client=AsyncMock(),
        is_client_registered=Mock(return_value=True),  # Add mock for the new method
        initialize=AsyncMock(),
        shutdown=AsyncMock(),
        # === Attributes/Methods for Agent/Executor Execution ===
        tools=MagicMock(spec=ToolManager),  # Mock the 'tools' attribute
        get_formatted_tools=Mock(return_value=[]),  # Default: no tools - Should be synchronous Mock
        execute_tool=AsyncMock(),  # Default: no specific return/side_effect
    )

    # Configure methods on the nested 'tools' mock separately
    host_mock.tools.configure_mock(
        create_tool_result_blocks=Mock()  # Sync method
    )

    # Do NOT explicitly set host_mock._clients here, as spec=MCPHost likely prevents it.
    # Tests needing client ID validation will patch host_mock._clients.__contains__ directly.

    # --- Configuration Examples (commented out, use in tests if needed) ---
    # Configure return values or side effects as needed for specific test scenarios
    # Example: Make register_client raise an error for a specific ID
    # async def register_client_side_effect(config):
    #     if config.client_id == "fail_client":
    #         raise ValueError("Client registration failed")
    #     host_mock._clients[config.client_id] = MagicMock() # Simulate adding
    # host_mock.register_client.side_effect = register_client_side_effect

    # Example: Configure get_formatted_tools for a specific test
    # host_mock.get_formatted_tools.return_value = [{"name": "test_tool", ...}]

    # Example: Configure execute_tool for a specific test
    # host_mock.execute_tool.return_value = "Specific tool result"

    # Example: Configure create_tool_result_blocks
    # mock_tool_result_block_content = {"type": "tool_result", ...}
    # host_mock.tools.create_tool_result_blocks.return_value = [mock_tool_result_block_content]

    return host_mock
