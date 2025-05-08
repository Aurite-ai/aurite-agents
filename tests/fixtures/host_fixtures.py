"""
Pytest fixtures related to MCPHost configuration and mocking.
"""

import pytest
from unittest.mock import (
    Mock,
    AsyncMock,
    patch,
    MagicMock,
)  # Ensure patch and MagicMock are here
import json
import logging  # Added logging import
from pathlib import Path

# import pytest_asyncio # Removed - Use standard pytest fixture with anyio plugin

# Use relative imports assuming tests run from aurite-mcp root
# Import necessary models
from src.config.config_models import (
    HostConfig,
    ProjectConfig,
    ClientConfig,
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
    # --- Use a minimal, hardcoded HostConfig for debugging initialization ---
    actual_project_root = PROJECT_ROOT_DIR.parent
    minimal_client_config = ClientConfig(
        client_id="weather_server_minimal",  # Use a distinct ID for clarity
        server_path=(
            actual_project_root / "src/packaged_servers/weather_mcp_server.py"
        ).resolve(),
        capabilities=["tools"],
        roots=[],
    )
    minimal_host_config_for_test = HostConfig(
        name="MinimalTestHost", clients=[minimal_client_config]
    )

    # Check if the single client path exists
    if not minimal_client_config.server_path.exists():
        pytest.skip(
            f"Minimal test server path does not exist: {minimal_client_config.server_path}"
        )

    # Instantiate HostManager with a dummy path, as we'll inject the config
    dummy_path = actual_project_root / "config/dummy_for_fixture.json"
    manager = HostManager(config_path=dummy_path)

    # --- Mock ProjectManager to return a ProjectConfig derived from our minimal HostConfig ---
    # This keeps the HostManager internal logic consistent while controlling the clients MCPHost sees.
    minimal_project_config = ProjectConfig(
        name=minimal_host_config_for_test.name,
        description="Minimal project config for fixture debugging",
        clients={minimal_client_config.client_id: minimal_client_config},
        agent_configs={},
        llm_configs={},
        simple_workflow_configs={},
        custom_workflow_configs={},
    )

    with patch("src.host_manager.ProjectManager") as MockProjectManager:
        mock_pm_instance = MagicMock()
        mock_pm_instance.load_project.return_value = minimal_project_config
        MockProjectManager.return_value = mock_pm_instance

        # Re-instantiate HostManager *inside* the patch context so it uses the mock
        manager = HostManager(config_path=dummy_path)

        # Initialize (this will now use the minimal_project_config via the mock)
        try:
            await manager.initialize()
            # Verify that MCPHost received the minimal config
            assert manager.host is not None
            assert len(manager.host._config.clients) == 1
            assert (
                manager.host._config.clients[0].client_id
                == minimal_client_config.client_id
            )
        except Exception as init_e:
            # Attempt cleanup even if init fails partially
            try:
                await manager.shutdown()
            except Exception:
                pass  # Ignore shutdown errors after init failure
            pytest.fail(
                f"HostManager initialization failed in fixture with minimal config: {init_e}"
            )

    # --- End of modifications for fixture setup ---

    yield manager  # Provide the initialized manager (initialized with minimal config) to the test

    # --- Teardown Logic ---
    logger.debug("Starting teardown for host_manager fixture...")
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
