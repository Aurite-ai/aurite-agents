"""
Pytest fixtures related to MCPHost configuration and mocking.
"""

import pytest
from unittest.mock import Mock, AsyncMock

# Use relative imports assuming tests run from aurite-mcp root
from src.host.models import HostConfig
from src.host.host import MCPHost
from src.host.resources import ToolManager, PromptManager


@pytest.fixture
def mock_host_config() -> HostConfig:
    """Provides a mock HostConfig."""
    # Define a simple mock host config if needed for AgentConfig initialization
    return HostConfig(
        name="MockHost", clients=[]
    )  # Keep clients empty for simplicity here


@pytest.fixture
def mock_mcp_host() -> Mock:
    """Provides a mock MCPHost instance with mocked managers."""
    host = Mock(spec=MCPHost)
    host.tools = Mock(spec=ToolManager)
    host.prompts = Mock(spec=PromptManager)
    # Mock the methods that will be called by Agent.execute
    host.tools.format_tools_for_llm = Mock(
        return_value=[
            {
                "name": "mock_tool",
                "description": "A mock tool",
                # Ensure the mock returns the required 'type' field for the schema
                "input_schema": {"type": "object", "properties": {}},
            }
        ]
    )
    host.tools.execute_tool = AsyncMock(
        return_value={"result": "Mock tool executed successfully"}
    )  # Must be AsyncMock
    host.tools.create_tool_result_blocks = Mock(
        return_value={
            "type": "tool_result",
            "tool_use_id": "mock_id",
            "content": [{"type": "text", "text": "Mock tool result"}],
        }
    )
    return host


# Change scope from "module" to "function" to potentially resolve async teardown issues
@pytest.fixture(scope="function")
async def real_mcp_host() -> MCPHost:
    """
    Sets up and tears down a real MCPHost instance connected to the example echo server.
    (Moved from test_agent_e2e.py)
    """
    # Import necessary modules
    from src.config import load_host_config_from_json, PROJECT_ROOT_DIR

    # Define path to the test config file relative to project root
    test_config_path = PROJECT_ROOT_DIR / "config/agents/testing_config.json"

    if not test_config_path.exists():
        pytest.skip(f"Test host config file not found at {test_config_path}")

    # Load host config using the utility function
    try:
        host_config = load_host_config_from_json(test_config_path)
        # Ensure the loaded config has the expected client for the test server
        # This assumes echo_server_fixture.py is correctly referenced in testing_config.json
        server_path_in_config = host_config.clients[0].server_path
        if not server_path_in_config.exists():
            pytest.skip(
                f"Test server path in config does not exist: {server_path_in_config}"
            )

    except Exception as e:
        pytest.fail(f"Failed to load host config for real_mcp_host fixture: {e}")

    # Initialize the host
    host_instance = MCPHost(config=host_config)
    await host_instance.initialize()  # This starts the client process

    yield host_instance  # Provide the initialized host to the test

    # Teardown: Shutdown the host and its clients
    await host_instance.shutdown()
