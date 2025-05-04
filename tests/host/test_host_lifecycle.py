"""
Tests for MCPHost lifecycle methods (initialize, shutdown) and error handling during init.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Import the class to test and dependencies
from src.host.host import MCPHost
from src.host.models import HostConfig, ClientConfig, RootConfig
import mcp.client.session  # To mock ClientSession

# Mark tests as host_unit and async
pytestmark = [pytest.mark.host_unit, pytest.mark.anyio]


# --- Fixtures ---


@pytest.fixture
def minimal_host_config() -> HostConfig:
    """Provides a minimal HostConfig with one client."""
    return HostConfig(
        name="test_host",  # Add a default name
        clients=[
            ClientConfig(
                client_id="test_client",
                server_path="dummy/path.py",
                capabilities=["tools"],
                roots=[RootConfig(name="root", uri="file:///", capabilities=[])],
            )
        ],
    )


# Removed unused mock_managers fixture


@pytest.fixture
def mock_client_session() -> MagicMock:
    """Fixture for a mocked ClientSession."""
    mock = AsyncMock(spec=mcp.client.session.ClientSession)
    # Mock methods called during initialization
    mock.initialize = AsyncMock(
        return_value=MagicMock(capabilities=[])
    )  # Mock initialize response
    mock.initialized = AsyncMock()
    mock.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
    mock.list_prompts = AsyncMock(return_value=MagicMock(prompts=[]))
    mock.list_resources = AsyncMock(return_value=MagicMock(resources=[]))
    mock.close = AsyncMock()
    return mock


# --- Test Cases ---


# Keep patches for external dependencies only
@patch("src.host.host.stdio_client")
@patch("src.host.host.ClientSession")
async def test_initialize_client_connection_error(
    mock_ClientSession: MagicMock,  # Patcher for ClientSession class
    mock_stdio_client: MagicMock,  # Patcher for stdio_client function
    minimal_host_config: HostConfig,
):
    """Test MCPHost initialize handles stdio_client connection errors."""
    # Configure mocks
    # Make the __aenter__ of the object returned by stdio_client() raise the error
    mock_stdio_client.return_value.__aenter__.side_effect = ConnectionRefusedError(
        "Failed to connect"
    )

    # MCPHost will now create REAL manager instances in __init__
    host = MCPHost(config=minimal_host_config)

    with pytest.raises(ConnectionRefusedError, match="Failed to connect"):
        await (
            host.initialize()
        )  # This will call initialize on real managers, then fail on stdio_client

    # Assert stdio_client was called (where the error occurred)
    mock_stdio_client.assert_called_once()
    # Assert ClientSession was NOT instantiated because stdio_client failed first
    mock_ClientSession.assert_not_called()
    # We don't need to (and can't easily without more mocks) assert calls on the real managers here.
    # The main point is the expected exception was raised due to the stdio_client mock.


# Keep patches for external dependencies only
@patch("src.host.host.stdio_client")
@patch("src.host.host.ClientSession")
async def test_initialize_manager_init_error(
    mock_ClientSession: MagicMock,  # Patcher for ClientSession class
    mock_stdio_client: MagicMock,  # Patcher for stdio_client function
    minimal_host_config: HostConfig,
    mock_client_session: MagicMock,  # Use the fixture for a configured session mock instance
):
    """Test MCPHost initialize handles errors during manager initialization."""
    # Configure external mocks for success
    mock_stdio_client.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
    mock_ClientSession.return_value = mock_client_session

    # Create host with REAL managers
    host = MCPHost(config=minimal_host_config)

    # Patch the 'initialize' method of a REAL manager instance ON the host object
    # to raise an error, using patch.object as a context manager.
    with patch.object(
        host._tool_manager,
        "initialize",
        side_effect=RuntimeError("Tool manager failed"),
    ):
        with pytest.raises(RuntimeError, match="Tool manager failed"):
            await host.initialize()

    # We can optionally assert that initialize was called on managers before the failing one,
    # but the primary check is catching the specific exception.
    # Example (requires managers to have async initialize methods):
    # assert host._security_manager.initialize.call_count == 1 # Need to ensure these methods exist and are async


# Keep patches for external dependencies only
@patch("src.host.host.stdio_client")
@patch("src.host.host.ClientSession")
async def test_shutdown(
    mock_ClientSession: MagicMock,  # Patcher for ClientSession class
    mock_stdio_client: MagicMock,  # Patcher for stdio_client function
    minimal_host_config: HostConfig,
    mock_client_session: MagicMock,  # Mock ClientSession instance from fixture
):
    """Test MCPHost shutdown calls shutdown on managers and closes sessions."""
    # Configure external mocks for successful initialization
    mock_stdio_client.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
    mock_ClientSession.return_value = mock_client_session

    # Create host with REAL managers
    host = MCPHost(config=minimal_host_config)

    # Initialize successfully (using mocked externals)
    await host.initialize()
    client_id = minimal_host_config.clients[0].client_id
    assert client_id in host._clients  # Verify client session was stored

    # Use patch.object to spy on the shutdown methods of the REAL manager instances
    with (
        patch.object(
            host._tool_manager, "shutdown", wraps=host._tool_manager.shutdown
        ) as spy_tool_shutdown,
        patch.object(
            host._resource_manager, "shutdown", wraps=host._resource_manager.shutdown
        ) as spy_resource_shutdown,
        patch.object(
            host._prompt_manager, "shutdown", wraps=host._prompt_manager.shutdown
        ) as spy_prompt_shutdown,
        patch.object(
            host._message_router, "shutdown", wraps=host._message_router.shutdown
        ) as spy_router_shutdown,
        patch.object(
            host._root_manager, "shutdown", wraps=host._root_manager.shutdown
        ) as spy_root_shutdown,
        patch.object(
            host._security_manager, "shutdown", wraps=host._security_manager.shutdown
        ) as spy_security_shutdown,
    ):
        # Call shutdown
        await host.shutdown()

        # Assert shutdown was called on managers
        spy_tool_shutdown.assert_called_once()
        spy_resource_shutdown.assert_called_once()
        spy_prompt_shutdown.assert_called_once()
        spy_router_shutdown.assert_called_once()
        spy_root_shutdown.assert_called_once()
        spy_security_shutdown.assert_called_once()

    # Assert the __aexit__ method of the ClientSession mock instance was called by the AsyncExitStack
    mock_ClientSession.return_value.__aexit__.assert_called_once()
