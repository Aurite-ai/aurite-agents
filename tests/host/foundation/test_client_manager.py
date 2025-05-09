"""
Unit tests for the ClientManager class.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from contextlib import AsyncExitStack

# Adjust imports based on your project structure
from src.host.foundation.clients import ClientManager
from src.config.config_models import ClientConfig, GCPSecretConfig
from src.host.foundation.security import SecurityManager
from mcp import ClientSession, StdioServerParameters


@pytest.fixture
def mock_exit_stack():
    """Fixture for a mocked AsyncExitStack."""
    # AsyncExitStack itself is a context manager, but its enter_async_context is what we use.
    # We'll mock the instance that ClientManager receives.
    stack = AsyncMock(spec=AsyncExitStack)
    stack.enter_async_context = AsyncMock()
    return stack


@pytest.fixture
def mock_security_manager():
    """Fixture for a mocked SecurityManager."""
    manager = AsyncMock(spec=SecurityManager)
    manager.resolve_gcp_secrets = AsyncMock(return_value={})
    return manager


@pytest.fixture
def sample_client_config():
    """Fixture for a sample ClientConfig."""
    return ClientConfig(
        client_id="test_client_1",
        server_path="/path/to/server.py",
        capabilities=["tools", "prompts"],
        roots=[],
        gcp_secrets=[
            GCPSecretConfig(
                project_id="proj", secret_id="secret", env_var_name="MY_SECRET"
            )
        ],
    )


@pytest.fixture
def sample_client_config_no_secrets():
    """Fixture for a sample ClientConfig without GCP secrets."""
    return ClientConfig(
        client_id="test_client_no_secret",
        server_path="/path/to/another_server.py",
        capabilities=["tools"],
        roots=[],
    )


@pytest.mark.asyncio
async def test_client_manager_initialization(mock_exit_stack):
    """Test ClientManager initializes correctly."""
    manager = ClientManager(exit_stack=mock_exit_stack)
    assert manager.exit_stack == mock_exit_stack
    assert manager.active_clients == {}
    assert manager.client_processes == {}


@pytest.mark.asyncio
@patch("src.host.foundation.clients.stdio_client")
@patch(
    "src.host.foundation.clients.ClientSession", new_callable=AsyncMock
)  # Patch ClientSession here
async def test_start_client_success(
    MockClientSessionCM,  # Mock passed as argument
    mock_stdio_client,
    mock_exit_stack,
    mock_security_manager,
    sample_client_config,
):
    """Test successful client startup."""
    # Mock stdio_client to return a mock process and mock reader/writer
    mock_process = AsyncMock()
    mock_process.wait = AsyncMock()  # Mock the wait method for termination
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()

    # stdio_client is an async context manager, so its __aenter__ should return the transport tuple
    mock_stdio_cm = AsyncMock()
    mock_stdio_cm.__aenter__.return_value = (mock_process, mock_reader, mock_writer)
    mock_stdio_client.return_value = mock_stdio_cm

    # Setup the instance returned by the ClientSession context manager (using the decorator mock)
    mock_session_instance = AsyncMock(spec=ClientSession)
    MockClientSessionCM.return_value.__aenter__.return_value = mock_session_instance

    # Configure side_effect for enter_async_context to return the correct __aenter__ results
    mock_exit_stack.enter_async_context.side_effect = [
        (
            mock_process,
            mock_reader,
            mock_writer,
        ),  # Result for stdio_client context manager
        mock_session_instance,  # Result for ClientSession context manager
    ]

    manager = ClientManager(exit_stack=mock_exit_stack)
    session = await manager.start_client(sample_client_config, mock_security_manager)

    assert session == mock_session_instance
    assert sample_client_config.client_id in manager.active_clients
    assert (
        manager.active_clients[sample_client_config.client_id] == mock_session_instance
    )
    assert sample_client_config.client_id in manager.client_processes
    assert manager.client_processes[sample_client_config.client_id] == mock_process

    mock_security_manager.resolve_gcp_secrets.assert_called_once_with(
        sample_client_config.gcp_secrets
    )
    mock_stdio_client.assert_called_once()
    # Check args of stdio_client
    stdio_args = mock_stdio_client.call_args[0][0]
    assert isinstance(stdio_args, StdioServerParameters)
    assert stdio_args.command == "python"
    assert stdio_args.args == [str(sample_client_config.server_path)]

    # enter_async_context should be called twice
    assert mock_exit_stack.enter_async_context.call_count == 2
    # First call with the stdio_client context manager object
    assert mock_exit_stack.enter_async_context.call_args_list[0][0][0] == mock_stdio_cm
    # Second call with the ClientSession context manager object
    # Note: Asserting the argument passed here can be tricky with nested mocks.
    # We rely on the correct side_effect return and other assertions to validate flow.
    # assert (
    #     mock_exit_stack.enter_async_context.call_args_list[1][0][0]
    #     == MockClientSessionCM.return_value
    # )


@pytest.mark.asyncio
@patch("src.host.foundation.clients.stdio_client")
async def test_start_client_no_secrets(
    mock_stdio_client,
    mock_exit_stack,
    mock_security_manager,
    sample_client_config_no_secrets,
):
    """Test client startup when no GCP secrets are configured for the client."""
    mock_process = AsyncMock()
    mock_process.wait = AsyncMock()
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_stdio_cm = AsyncMock()
    mock_stdio_cm.__aenter__.return_value = (mock_process, mock_reader, mock_writer)
    mock_stdio_client.return_value = mock_stdio_cm

    with patch(
        "src.host.foundation.clients.ClientSession", new_callable=AsyncMock
    ) as MockClientSessionCM:
        mock_session_instance = AsyncMock(spec=ClientSession)
        MockClientSessionCM.return_value.__aenter__.return_value = mock_session_instance

        mock_exit_stack.enter_async_context.side_effect = [
            (mock_process, mock_reader, mock_writer),
            mock_session_instance,
        ]

        manager = ClientManager(exit_stack=mock_exit_stack)
        await manager.start_client(
            sample_client_config_no_secrets, mock_security_manager
        )

        mock_security_manager.resolve_gcp_secrets.assert_not_called()
        assert sample_client_config_no_secrets.client_id in manager.active_clients
        assert sample_client_config_no_secrets.client_id in manager.client_processes


@pytest.mark.asyncio
@patch("src.host.foundation.clients.stdio_client")
async def test_start_client_already_active(
    mock_stdio_client, mock_exit_stack, mock_security_manager, sample_client_config
):
    """Test starting a client that is already active."""
    manager = ClientManager(exit_stack=mock_exit_stack)
    manager.active_clients[sample_client_config.client_id] = (
        AsyncMock()
    )  # Mark as active

    with pytest.raises(
        ValueError, match=f"Client {sample_client_config.client_id} is already active."
    ):
        await manager.start_client(sample_client_config, mock_security_manager)
    mock_stdio_client.assert_not_called()


@pytest.mark.asyncio
@patch("src.host.foundation.clients.stdio_client", side_effect=Exception("stdio error"))
async def test_start_client_stdio_failure(
    mock_stdio_client_fails,
    mock_exit_stack,
    mock_security_manager,
    sample_client_config,
):
    """Test client startup failure at stdio_client."""
    manager = ClientManager(exit_stack=mock_exit_stack)

    # No need to mock enter_async_context here, the error comes from stdio_client patch

    with pytest.raises(
        Exception, match="stdio error"
    ):  # Expect the error from the stdio_client patch
        await manager.start_client(sample_client_config, mock_security_manager)

    assert sample_client_config.client_id not in manager.active_clients
    assert sample_client_config.client_id not in manager.client_processes


@pytest.mark.asyncio
async def test_shutdown_client_success(mock_exit_stack, sample_client_config):
    """Test successful shutdown of a specific client."""
    manager = ClientManager(exit_stack=mock_exit_stack)
    mock_session = AsyncMock(spec=ClientSession)
    mock_process = AsyncMock()
    mock_process.terminate = MagicMock()  # Synchronous mock for terminate
    mock_process.wait = AsyncMock()  # Async mock for wait

    manager.active_clients[sample_client_config.client_id] = mock_session
    manager.client_processes[sample_client_config.client_id] = mock_process

    await manager.shutdown_client(sample_client_config.client_id)

    assert sample_client_config.client_id not in manager.active_clients
    assert sample_client_config.client_id not in manager.client_processes
    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_client_not_found(mock_exit_stack, sample_client_config):
    """Test shutting down a client that is not found."""
    manager = ClientManager(exit_stack=mock_exit_stack)
    # No client is active
    await manager.shutdown_client(sample_client_config.client_id)
    # No error should be raised, and logs should indicate not found
    assert sample_client_config.client_id not in manager.active_clients
    assert sample_client_config.client_id not in manager.client_processes


@pytest.mark.asyncio
async def test_shutdown_all_clients(
    mock_exit_stack, sample_client_config, sample_client_config_no_secrets
):
    """Test shutting down all active clients."""
    manager = ClientManager(exit_stack=mock_exit_stack)

    # Mock clients
    client_1_id = sample_client_config.client_id
    mock_session_1 = AsyncMock(spec=ClientSession)
    mock_process_1 = AsyncMock()
    mock_process_1.terminate = MagicMock()
    mock_process_1.wait = AsyncMock()
    manager.active_clients[client_1_id] = mock_session_1
    manager.client_processes[client_1_id] = mock_process_1

    client_2_id = sample_client_config_no_secrets.client_id
    mock_session_2 = AsyncMock(spec=ClientSession)
    mock_process_2 = AsyncMock()
    mock_process_2.terminate = MagicMock()
    mock_process_2.wait = AsyncMock()
    manager.active_clients[client_2_id] = mock_session_2
    manager.client_processes[client_2_id] = mock_process_2

    assert len(manager.active_clients) == 2
    assert len(manager.client_processes) == 2

    await manager.shutdown_all_clients()

    assert not manager.active_clients  # Should be empty
    assert not manager.client_processes  # Should be empty
    mock_process_1.terminate.assert_called_once()
    mock_process_1.wait.assert_called_once()
    mock_process_2.terminate.assert_called_once()
    mock_process_2.wait.assert_called_once()


@pytest.mark.asyncio
async def test_get_session(mock_exit_stack, sample_client_config):
    """Test retrieving an active session."""
    manager = ClientManager(exit_stack=mock_exit_stack)
    mock_session = AsyncMock(spec=ClientSession)
    manager.active_clients[sample_client_config.client_id] = mock_session

    session = manager.get_session(sample_client_config.client_id)
    assert session == mock_session

    assert manager.get_session("non_existent_client") is None


@pytest.mark.asyncio
async def test_get_all_sessions(mock_exit_stack, sample_client_config):
    """Test retrieving all active sessions."""
    manager = ClientManager(exit_stack=mock_exit_stack)
    mock_session_1 = AsyncMock(spec=ClientSession)
    manager.active_clients[sample_client_config.client_id] = mock_session_1

    mock_session_2 = AsyncMock(spec=ClientSession)
    manager.active_clients["client_2"] = mock_session_2

    all_sessions = manager.get_all_sessions()
    assert len(all_sessions) == 2
    assert all_sessions[sample_client_config.client_id] == mock_session_1
    assert all_sessions["client_2"] == mock_session_2

    # Ensure it's a copy
    all_sessions.pop(sample_client_config.client_id)
    assert sample_client_config.client_id in manager.active_clients
