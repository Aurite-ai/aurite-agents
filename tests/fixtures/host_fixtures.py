"""
Pytest fixtures related to MCPHost configuration and mocking.
"""

import pytest
from unittest.mock import (
    Mock,
    AsyncMock,
)  # Ensure patch and MagicMock are here
import json
import logging  # Added logging import

# import pytest_asyncio # Removed - Use standard pytest fixture with anyio plugin

# Use relative imports assuming tests run from aurite-mcp root
# Import necessary models
from src.config.config_models import (
    HostConfig,
)  # Ensure ProjectConfig and ClientConfig are here
from src.host.host import MCPHost
from src.host_manager import HostManager
from src.host.resources import ToolManager, PromptManager
from src.config import PROJECT_ROOT_DIR  # Import project root

# Define logger for this fixtures module
logger = logging.getLogger(__name__)


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

    # Mock the method Agent actually calls
    host.get_formatted_tools = Mock(return_value=[])  # Return empty list by default

    # Mock the execute_tool method directly on the host mock
    host.execute_tool = AsyncMock(
        return_value={"result": "Mock tool executed successfully"}
    )

    # Mock the create_tool_result_blocks method on the tools manager mock
    host.tools.create_tool_result_blocks = Mock(
        return_value=[  # Ensure this returns a list of blocks
            {
                "type": "tool_result",
                "tool_use_id": "mock_id",
                "content": [{"type": "text", "text": "Mock tool result"}],
            }
        ]
    )

    # Keep the old mock for format_tools_for_llm in case other tests use it,
    # but the primary one Agent uses is get_formatted_tools
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
    # host.tools.execute_tool = AsyncMock(...) # Removed, moved to host mock
    # host.tools.create_tool_result_blocks = Mock(...) # Already defined above on host.tools

    return host


# --- Shared Mock Manager Fixtures ---
# (Moved to tests/host/conftest.py)

# --- Integration Fixture ---


@pytest.fixture(scope="function")  # Changed scope to function for better isolation
async def host_manager(anyio_backend) -> HostManager:  # Add anyio_backend argument
    """
    Provides an initialized HostManager instance for testing, based on
    the testing_config.json file. Handles setup and teardown.
    """
    # Define path to the test config file relative to the project root
    test_config_path = (
        PROJECT_ROOT_DIR / "config/testing_config.json"
    )  # Use PROJECT_ROOT_DIR directly

    if not test_config_path.exists():
        pytest.skip(f"Test host config file not found at {test_config_path}")

    # Check if the referenced server paths exist relative to the project root
    try:
        with open(test_config_path, "r") as f:
            raw_config = json.load(f)
        clients = raw_config.get("clients", [])
        if not clients:
            pytest.fail("No clients defined in testing_config.json for fixture setup.")

        for client_config in clients:
            client_path_str = client_config.get("server_path")
            if client_path_str:
                # Resolve client path relative to PROJECT_ROOT_DIR
                client_path = (
                    PROJECT_ROOT_DIR / client_path_str
                ).resolve()  # Use PROJECT_ROOT_DIR directly
                if not client_path.exists():
                    pytest.skip(
                        f"Test server path in config does not exist: {client_path}"  # Keep skip message
                    )
            else:
                pytest.fail(
                    f"Client '{client_config.get('client_id', 'UNKNOWN')}' missing 'server_path' in testing config."
                )
    except Exception as e:
        pytest.fail(f"Failed to pre-check server paths in testing config: {e}")

    # Instantiate HostManager - This will use the real ProjectManager now
    manager = HostManager(config_path=test_config_path)

    # Initialize (this loads configs via real ProjectManager and starts MCPHost/clients)
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
        # Only shutdown should be called here
        if manager and manager.host:  # Check if manager and host exist before shutdown
            logger.debug(f"Attempting shutdown for host: {manager.host._config.name}")
            await manager.shutdown()
            logger.debug(
                f"Finished shutdown for host: {manager.host._config.name if manager.host else 'N/A'}"
            )  # Check host again as shutdown sets it to None
        else:
            logger.debug("Manager or host not available for shutdown in teardown.")
    except RuntimeError as e:
        # Catch and log the specific "Event loop is closed" error during teardown
        # Also catch "Cannot run shutdown() while loop is stopping" which might occur
        if "Event loop is closed" in str(
            e
        ) or "Cannot run shutdown() while loop is stopping" in str(e):
            print(
                f"\n[WARN] Suppressed known teardown error in host_manager fixture: {e}"
            )
        else:
            # Re-raise other RuntimeErrors
            print(
                f"\n[ERROR] Unexpected RuntimeError during HostManager shutdown in fixture: {e}"
            )
            raise  # Re-raise unexpected RuntimeErrors
    except Exception as shutdown_e:
        # Log or handle other teardown errors if necessary
        print(f"\n[ERROR] Error during HostManager shutdown in fixture: {shutdown_e}")


# Note: The old real_host_and_manager fixture is removed as host_manager replaces it.
# The mock_mcp_host fixture remains useful for unit tests not needing real clients.
