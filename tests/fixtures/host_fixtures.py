"""
Pytest fixtures related to MCPHost configuration and mocking.
"""

import pytest
from unittest.mock import (
    Mock,
    AsyncMock,
)  # Ensure patch and MagicMock are here
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


@pytest.fixture(scope="function")  # <<< Reverted scope back to function
async def host_manager(anyio_backend) -> HostManager:  # Add anyio_backend argument
    """
    Provides an initialized HostManager instance for testing, based on
    the testing_config.json file. Handles setup and teardown.
    """
    # Define path to the test config file relative to the project root
    test_config_path = (
        PROJECT_ROOT_DIR / "tests/fixtures/project_fixture.json"  # Updated path
    )  # Use PROJECT_ROOT_DIR directly

    if not test_config_path.exists():
        pytest.skip(f"Test host config file not found at {test_config_path}")

    # Instantiate HostManager - This will use the real ProjectManager now
    # The ProjectManager, when loading the project during manager.initialize(),
    # will resolve client string references to full ClientConfig objects
    # using the ComponentManager. Path validation for servers will occur
    # during MCPHost and ClientManager initialization.
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
        if manager:
            if manager.execution and hasattr(manager.execution, "aclose"):
                logger.debug("HostManager Fixture: Attempting to aclose ExecutionFacade...")
                await manager.execution.aclose()
                logger.debug("HostManager Fixture: ExecutionFacade aclosed.")
            if manager.host: # Check if manager and host exist before shutdown
                logger.debug(f"HostManager Fixture: Attempting shutdown for host: {manager.host._config.name}") # Log before shutdown
                await manager.shutdown() # Attempt shutdown
                logger.debug(f"HostManager Fixture: Finished shutdown for host: {manager.host._config.name if manager.host else 'N/A'}") # Log after successful shutdown
            else:
                logger.debug("HostManager Fixture: Host not available on manager for shutdown in teardown.")
        else:
            logger.debug("HostManager Fixture: Manager not available for shutdown in teardown.")
    except ExceptionGroup as eg:
        # Specifically catch ExceptionGroup, likely from TaskGroup/AsyncExitStack issues
        # Check if the known ProcessLookupError is within the group
        if any(isinstance(e, ProcessLookupError) for e in eg.exceptions):
             print(f"\n[WARN] Suppressed known ProcessLookupError during teardown in host_manager fixture: {eg}")
        else:
             # Re-raise other unexpected ExceptionGroups
             print(f"\n[ERROR] Unexpected ExceptionGroup during HostManager shutdown in fixture: {eg}")
             raise
    except RuntimeError as e:
        # Keep handling for specific RuntimeErrors like "Event loop is closed"
        if "Event loop is closed" in str(e) or "Cannot run shutdown() while loop is stopping" in str(e):
            print(f"\n[WARN] Suppressed known RuntimeError teardown error in host_manager fixture: {e}")
        else:
            print(f"\n[ERROR] Unexpected RuntimeError during HostManager shutdown in fixture: {e}")
            raise # Re-raise other RuntimeErrors
    except Exception as shutdown_e:
        # Catch any other unexpected exceptions during shutdown
        print(f"\n[ERROR] Unexpected generic Exception during HostManager shutdown in fixture: {shutdown_e}")
        raise # Re-raise other exceptions


# Note: The old real_host_and_manager fixture is removed as host_manager replaces it.
# The mock_mcp_host fixture remains useful for unit tests not needing real clients.
