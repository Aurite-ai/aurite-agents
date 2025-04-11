"""
Pytest fixtures related to MCPHost configuration and mocking.
"""

import pytest
from unittest.mock import Mock, AsyncMock

# import pytest_asyncio # Removed - Use standard pytest fixture with anyio plugin

# Use relative imports assuming tests run from aurite-mcp root
from src.host.models import HostConfig
from src.host.host import MCPHost
from src.host_manager import HostManager  # Import HostManager
from src.host.resources import ToolManager, PromptManager
from src.config import PROJECT_ROOT_DIR  # Import project root


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


@pytest.fixture(scope="class")  # Use standard pytest fixture decorator
async def host_manager(anyio_backend) -> HostManager:  # Add anyio_backend argument
    """
    Provides an initialized HostManager instance for testing, based on
    the testing_config.json file. Handles setup and teardown.
    """
    # Define path to the test config file relative to project root
    test_config_path = PROJECT_ROOT_DIR / "config/testing_config.json"

    if not test_config_path.exists():
        pytest.skip(f"Test host config file not found at {test_config_path}")

    # Check if the referenced server path exists to avoid unnecessary setup failure
    # This requires loading the config partially or making assumptions.
    # Let's load it quickly just to check the server path for skipping.
    try:
        import json

        with open(test_config_path, "r") as f:
            raw_config = json.load(f)
        first_client_path_str = raw_config.get("clients", [{}])[0].get("server_path")
        if first_client_path_str:
            first_client_path = (PROJECT_ROOT_DIR / first_client_path_str).resolve()
            if not first_client_path.exists():
                pytest.skip(
                    f"Test server path in config does not exist: {first_client_path}"
                )
        else:
            pytest.fail("Could not read first client server_path from testing config.")
    except Exception as e:
        pytest.fail(f"Failed to pre-check server path in testing config: {e}")

    # Instantiate HostManager
    manager = HostManager(config_path=test_config_path)

    # Initialize (this loads configs and starts MCPHost/clients)
    try:
        await manager.initialize()
    except Exception as init_e:
        # Attempt cleanup even if init fails partially
        try:
            await manager.shutdown()
        except Exception:
            pass  # Ignore shutdown errors after init failure
        pytest.fail(f"HostManager initialization failed in fixture: {init_e}")

    yield manager  # Provide the initialized manager to the test

    # Teardown: Shutdown the manager (which shuts down the host)
    try:
        await manager.shutdown()
    except Exception as shutdown_e:
        # Log or handle teardown errors if necessary, but don't fail the test run here
        print(f"Error during HostManager shutdown in fixture: {shutdown_e}")


# Note: The old real_host_and_manager fixture is removed as host_manager replaces it.
# The mock_mcp_host fixture remains useful for unit tests not needing real clients.
