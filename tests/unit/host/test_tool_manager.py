"""
Unit tests for the ToolManager class.
"""

import mcp.types as types
import pytest

from src.aurite.host.resources.tools import ToolManager

# Mark all tests in this file as 'unit' and 'host'
pytestmark = [pytest.mark.unit, pytest.mark.host]


@pytest.mark.anyio
async def test_tool_manager_initialization(mock_root_manager, mock_message_router, mock_client_session_group):
    """
    Test that the ToolManager can be initialized successfully and registers tools.
    """
    # 1. Arrange
    tool = types.Tool(name="test_tool", description="A test tool", inputSchema={})
    tool.client_id = "test_client"
    mock_client_session_group.tools = {"test_tool": tool}

    # 2. Act
    tool_manager = ToolManager(
        root_manager=mock_root_manager,
        message_router=mock_message_router,
        session_group=mock_client_session_group,
    )
    await tool_manager.initialize()

    # 3. Assert
    assert isinstance(tool_manager, ToolManager)
    mock_message_router.register_tool.assert_awaited_once_with("test_tool", "test_client")


@pytest.mark.anyio
async def test_execute_tool(mock_root_manager, mock_message_router, mock_client_session_group):
    """
    Test that execute_tool calls the session group's call_tool method.
    """
    # 1. Arrange
    tool_manager = ToolManager(
        root_manager=mock_root_manager,
        message_router=mock_message_router,
        session_group=mock_client_session_group,
    )
    tool_name = "test_tool"
    tool_args = {"arg1": "value1"}
    expected_result = types.CallToolResult(isError=False, content=[types.TextContent(type="text", text="Success!")])
    mock_client_session_group.call_tool.return_value = expected_result

    # 2. Act
    result = await tool_manager.execute_tool(tool_name, tool_args)

    # 3. Assert
    assert result == expected_result
    mock_client_session_group.call_tool.assert_awaited_once_with(tool_name, tool_args)


@pytest.mark.anyio
async def test_list_tools(mock_root_manager, mock_message_router, mock_client_session_group):
    """
    Test that list_tools returns all tools from the session group.
    """
    # 1. Arrange
    tool1 = types.Tool(name="tool1", description="A test tool", inputSchema={})
    tool2 = types.Tool(name="tool2", description="Another test tool", inputSchema={})
    mock_client_session_group.tools = {"tool1": tool1, "tool2": tool2}
    tool_manager = ToolManager(
        root_manager=mock_root_manager,
        message_router=mock_message_router,
        session_group=mock_client_session_group,
    )

    # 2. Act
    all_tools = tool_manager.list_tools()

    # 3. Assert
    assert len(all_tools) == 2
    assert all_tools[0]["name"] == "tool1"
    assert all_tools[1]["name"] == "tool2"
