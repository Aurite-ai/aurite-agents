"""
Unit tests for the ToolManager class.
"""

import pytest
from unittest.mock import Mock, AsyncMock
import mcp.types as types

from src.aurite.host.resources.tools import ToolManager

# Mark all tests in this file as 'unit' and 'host'
pytestmark = [pytest.mark.unit, pytest.mark.host]


@pytest.mark.anyio
async def test_tool_manager_initialization():
    """
    Test that the ToolManager can be initialized successfully.
    """
    # 1. Arrange
    # Create mock dependencies for the ToolManager constructor
    mock_root_manager = Mock()
    mock_message_router = Mock()

    # 2. Act
    # Instantiate the ToolManager
    tool_manager = ToolManager(
        root_manager=mock_root_manager,
        message_router=mock_message_router,
    )
    await tool_manager.initialize()

    # 3. Assert
    # Verify that the manager was created and its internal state is as expected
    assert isinstance(tool_manager, ToolManager)
    assert tool_manager._root_manager == mock_root_manager
    assert tool_manager._message_router == mock_message_router
    assert tool_manager._tools == {}
    assert tool_manager._clients == {}


@pytest.mark.anyio
async def test_register_client():
    """
    Test that a client can be registered with the ToolManager.
    """
    # 1. Arrange
    tool_manager = ToolManager(root_manager=Mock(), message_router=Mock())
    client_id = "test_client_01"
    mock_client_session = Mock()

    # 2. Act
    tool_manager.register_client(client_id, mock_client_session)

    # 3. Assert
    assert client_id in tool_manager._clients
    assert tool_manager._clients[client_id] == mock_client_session


@pytest.mark.anyio
async def test_register_tool_allowed():
    """
    Test that a tool is registered when the filtering manager allows it.
    """
    # 1. Arrange
    mock_router = AsyncMock()
    tool_manager = ToolManager(root_manager=Mock(), message_router=mock_router)

    mock_filtering_manager = Mock()
    mock_filtering_manager.is_registration_allowed.return_value = True

    client_id = "test_client"
    tool_name = "test_tool"
    mock_tool = Mock(description="A test tool", inputSchema={})
    mock_client_config = Mock()

    # 2. Act
    registered = await tool_manager.register_tool(
        tool_name=tool_name,
        tool=mock_tool,
        client_id=client_id,
        client_config=mock_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # 3. Assert
    assert registered is True
    assert tool_name in tool_manager._tools
    assert tool_manager.get_tool(tool_name) == mock_tool
    mock_filtering_manager.is_registration_allowed.assert_called_once_with(
        tool_name, mock_client_config
    )
    mock_router.register_tool.assert_awaited_once_with(tool_name, client_id)


@pytest.mark.anyio
async def test_register_tool_denied():
    """
    Test that a tool is not registered when the filtering manager denies it.
    """
    # 1. Arrange
    mock_router = AsyncMock()
    tool_manager = ToolManager(root_manager=Mock(), message_router=mock_router)

    mock_filtering_manager = Mock()
    mock_filtering_manager.is_registration_allowed.return_value = False

    client_id = "test_client"
    tool_name = "test_tool"
    mock_tool = Mock()
    mock_client_config = Mock()

    # 2. Act
    registered = await tool_manager.register_tool(
        tool_name=tool_name,
        tool=mock_tool,
        client_id=client_id,
        client_config=mock_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # 3. Assert
    assert registered is False
    assert tool_name not in tool_manager._tools
    mock_filtering_manager.is_registration_allowed.assert_called_once_with(
        tool_name, mock_client_config
    )
    mock_router.register_tool.assert_not_awaited()


@pytest.mark.anyio
async def test_discover_client_tools_happy_path():
    """
    Test that tools are discovered successfully from a client.
    """
    # 1. Arrange
    tool_manager = ToolManager(root_manager=Mock(), message_router=Mock())
    client_id = "test_client"

    # Create a mock for the client session
    mock_client_session = AsyncMock()
    mock_tool_list = [Mock(), Mock()]
    mock_list_tools_result = Mock(tools=mock_tool_list)
    mock_client_session.list_tools.return_value = mock_list_tools_result

    # 2. Act
    discovered_tools = await tool_manager.discover_client_tools(
        client_id, mock_client_session
    )

    # 3. Assert
    assert discovered_tools == mock_tool_list
    mock_client_session.list_tools.assert_awaited_once()


@pytest.mark.anyio
async def test_discover_client_tools_raises_exception():
    """
    Test that an exception from the client is propagated during discovery.
    """
    # 1. Arrange
    tool_manager = ToolManager(root_manager=Mock(), message_router=Mock())
    client_id = "test_client"

    mock_client_session = AsyncMock()
    mock_client_session.list_tools.side_effect = RuntimeError("Connection failed")

    # 2. Act & Assert
    with pytest.raises(RuntimeError, match="Connection failed"):
        await tool_manager.discover_client_tools(client_id, mock_client_session)

    mock_client_session.list_tools.assert_awaited_once()


@pytest.mark.anyio
async def test_execute_tool_happy_path():
    """
    Test successful execution of an unambiguous tool.
    """
    # 1. Arrange
    mock_root_manager = AsyncMock()
    mock_router = AsyncMock()
    tool_manager = ToolManager(
        root_manager=mock_root_manager, message_router=mock_router
    )

    client_id = "test_client"
    tool_name = "test_tool"
    tool_args = {"arg1": "value1"}
    expected_result = [types.TextContent(type="text", text="Success!")]

    # Mock the client session and its call_tool method
    mock_client_session = AsyncMock()
    # Simulate a successful tool call result
    mock_tool_result = Mock(isError=False, content=expected_result)
    mock_client_session.call_tool.return_value = mock_tool_result
    tool_manager.register_client(client_id, mock_client_session)

    # Mock the router to return the client
    mock_router.get_clients_for_tool.return_value = [client_id]

    # 2. Act
    result = await tool_manager.execute_tool(tool_name, tool_args)

    # 3. Assert
    assert result == expected_result
    mock_router.get_clients_for_tool.assert_awaited_once_with(tool_name)
    mock_root_manager.validate_access.assert_awaited_once_with(client_id=client_id)
    mock_client_session.call_tool.assert_awaited_once_with(tool_name, tool_args)


@pytest.mark.anyio
async def test_execute_tool_not_found():
    """
    Test that executing a non-existent tool raises a ValueError.
    """
    # 1. Arrange
    mock_router = AsyncMock()
    tool_manager = ToolManager(root_manager=Mock(), message_router=mock_router)
    mock_router.get_clients_for_tool.return_value = []  # No client provides the tool

    # 2. Act & Assert
    with pytest.raises(ValueError, match="Tool 'unknown_tool' not found"):
        await tool_manager.execute_tool("unknown_tool", {})

    mock_router.get_clients_for_tool.assert_awaited_once_with("unknown_tool")


@pytest.mark.anyio
async def test_list_tools_happy_path():
    """
    Test that list_tools returns a correctly formatted list of registered tools.
    """
    # 1. Arrange
    tool_manager = ToolManager(root_manager=Mock(), message_router=AsyncMock())
    mock_filtering_manager = Mock()
    mock_filtering_manager.is_registration_allowed.return_value = True

    # Register a tool
    tool_name = "test_tool_1"
    tool_desc = "A test tool."
    tool_params = {"type": "object", "properties": {"param1": {"type": "string"}}}
    mock_tool = Mock(name=tool_name, description=tool_desc, inputSchema=tool_params)
    await tool_manager.register_tool(
        tool_name=tool_name,
        tool=mock_tool,
        client_id="client_1",
        client_config=Mock(),
        filtering_manager=mock_filtering_manager,
    )

    # 2. Act
    tool_list = tool_manager.list_tools()

    # 3. Assert
    assert len(tool_list) == 1
    assert tool_list[0] == {
        "name": tool_name,
        "description": tool_desc,
        "client_id": "client_1",
        "parameters": tool_params,
    }
