"""
Unit tests for the ToolManager.
"""

import pytest
import re # Import re for escaping
from unittest.mock import MagicMock, AsyncMock, call
from typing import List, Dict, Any

# Import the class to test and dependencies/models
from src.host.resources.tools import ToolManager
from src.host.foundation.routing import MessageRouter
from src.host.foundation.roots import RootManager
from src.host.filtering import FilteringManager
from src.host.models import ClientConfig, RootConfig, AgentConfig
import mcp.types as types
from mcp.client.session import ClientSession # For mocking

# Mark tests as host_unit and async
pytestmark = [pytest.mark.host_unit, pytest.mark.anyio]


# --- Fixtures ---

@pytest.fixture
def mock_message_router() -> MagicMock:
    """Fixture for a mocked MessageRouter."""
    return AsyncMock(spec=MessageRouter)

@pytest.fixture
def mock_filtering_manager() -> MagicMock:
    """Fixture for a mocked FilteringManager."""
    mock = MagicMock(spec=FilteringManager)
    mock.is_registration_allowed.return_value = True # Default to allowed
    mock.filter_component_list.side_effect = lambda tools, config: tools # Pass through by default
    return mock

@pytest.fixture
def mock_root_manager() -> MagicMock:
    """Fixture for a mocked RootManager."""
    mock = MagicMock(spec=RootManager)
    mock.validate_access.return_value = True # Default to allowed
    return mock

@pytest.fixture
def mock_client_session() -> MagicMock:
    """Fixture for a mocked ClientSession."""
    # Mock async methods needed
    mock = AsyncMock(spec=ClientSession)
    mock.list_tools = AsyncMock(return_value=[]) # Default to empty list
    # Corrected type: CallToolResult, added missing 'type' field for TextContent
    mock.call_tool = AsyncMock(return_value=types.CallToolResult(content=[types.TextContent(type="text", text="mock result")]))
    return mock

@pytest.fixture
def tool_manager(
    mock_message_router: MagicMock,
    mock_root_manager: MagicMock
) -> ToolManager:
    """Fixture to provide a clean ToolManager instance with mocked dependencies."""
    return ToolManager(
        message_router=mock_message_router,
        root_manager=mock_root_manager
    )

@pytest.fixture
def sample_client_config() -> ClientConfig:
    """Fixture for a sample ClientConfig for tools."""
    return ClientConfig(
        client_id="client_T",
        server_path="path/to/server_t.py",
        capabilities=["tools"],
        roots=[RootConfig(name="root_t", uri="file:///tools/", capabilities=[])],
    )

@pytest.fixture
def sample_tool() -> types.Tool:
    """Fixture for a sample Tool."""
    # Define arguments using inputSchema (JSON Schema format)
    input_schema = {
        "type": "object",
        "properties": {
            "arg1": {"type": "string", "description": "The first argument"}
        },
        "required": ["arg1"]
    }
    return types.Tool(
        name="tool1",
        description="Sample tool one",
        inputSchema=input_schema
    )

@pytest.fixture
def sample_agent_config() -> AgentConfig:
    """Fixture for a basic AgentConfig."""
    return AgentConfig(name="test_agent")


# --- Test Cases ---

def test_tool_manager_init(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_root_manager: MagicMock
):
    """Test initial state of the ToolManager."""
    assert tool_manager._tools == {}
    assert tool_manager._clients == {} # Corrected attribute name
    assert tool_manager._message_router == mock_message_router
    assert tool_manager._root_manager == mock_root_manager


async def test_register_client(
    tool_manager: ToolManager,
    mock_client_session: MagicMock,
):
    """Test registering a client session."""
    client_id = "client_T_reg"
    # register_client is not async
    tool_manager.register_client(client_id, mock_client_session)
    assert client_id in tool_manager._clients # Corrected attribute name
    assert tool_manager._clients[client_id] == mock_client_session


# --- Tests for register_tool ---

async def test_register_tool_success(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
    sample_tool: types.Tool,
):
    """Test registering a tool successfully."""
    client_id = sample_client_config.client_id
    tool_name = sample_tool.name

    # Ensure filtering allows
    mock_filtering_manager.is_registration_allowed.return_value = True

    registered = await tool_manager.register_tool(
        tool_name=tool_name,
        tool=sample_tool,
        client_id=client_id,
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    assert registered is True
    # Check internal state
    assert tool_name in tool_manager._tools
    assert tool_manager._tools[tool_name] == sample_tool
    assert tool_name in tool_manager._tool_metadata
    assert tool_manager._tool_metadata[tool_name]["client_id"] == client_id
    assert tool_manager._tool_metadata[tool_name]["description"] == sample_tool.description
    # Check that metadata stored the inputSchema
    assert tool_manager._tool_metadata[tool_name]["parameters"] == sample_tool.inputSchema

    # Check calls to dependencies
    mock_filtering_manager.is_registration_allowed.assert_called_once_with(
        tool_name, sample_client_config
    )
    mock_message_router.register_tool.assert_called_once_with(tool_name, client_id)


async def test_register_tool_filtered(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
    sample_tool: types.Tool,
):
    """Test that a tool is not registered if filtered out."""
    client_id = sample_client_config.client_id
    tool_name = sample_tool.name

    # Ensure filtering denies
    mock_filtering_manager.is_registration_allowed.return_value = False

    registered = await tool_manager.register_tool(
        tool_name=tool_name,
        tool=sample_tool,
        client_id=client_id,
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    assert registered is False
    # Check internal state (should not be added)
    assert tool_name not in tool_manager._tools
    assert tool_name not in tool_manager._tool_metadata

    # Check calls to dependencies
    mock_filtering_manager.is_registration_allowed.assert_called_once_with(
        tool_name, sample_client_config
    )
    mock_message_router.register_tool.assert_not_called()


async def test_register_tool_with_input_schema(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test registering a tool that uses inputSchema instead of arguments."""
    client_id = sample_client_config.client_id
    tool_name = "schema_tool"
    input_schema = {"type": "object", "properties": {"param1": {"type": "integer"}}}
    schema_tool = types.Tool(
        name=tool_name,
        description="Tool with inputSchema",
        inputSchema=input_schema # Use inputSchema field
    )

    mock_filtering_manager.is_registration_allowed.return_value = True

    registered = await tool_manager.register_tool(
        tool_name=tool_name,
        tool=schema_tool,
        client_id=client_id,
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    assert registered is True
    assert tool_name in tool_manager._tools
    assert tool_manager._tools[tool_name] == schema_tool
    assert tool_name in tool_manager._tool_metadata
    # Verify metadata uses inputSchema when present
    assert tool_manager._tool_metadata[tool_name]["parameters"] == input_schema

    mock_filtering_manager.is_registration_allowed.assert_called_once_with(
        tool_name, sample_client_config
    )
    mock_message_router.register_tool.assert_called_once_with(tool_name, client_id)


# --- Tests for discover_client_tools ---

async def test_discover_client_tools_success(
    tool_manager: ToolManager,
    mock_client_session: MagicMock,
    sample_tool: types.Tool,
):
    """Test discovering tools from a client session successfully."""
    client_id = "client_discover"
    # Provide a default empty inputSchema for tool2
    tool2 = types.Tool(name="tool2", description="Second tool", inputSchema={"type": "object", "properties": {}})
    # Mock the list_tools response - assuming it returns an object with a 'tools' attribute
    mock_response = MagicMock()
    mock_response.tools = [sample_tool, tool2]
    mock_client_session.list_tools = AsyncMock(return_value=mock_response)

    discovered = await tool_manager.discover_client_tools(client_id, mock_client_session)

    assert discovered == [sample_tool, tool2]
    mock_client_session.list_tools.assert_called_once()


async def test_discover_client_tools_unexpected_format(
    tool_manager: ToolManager,
    mock_client_session: MagicMock,
    caplog: pytest.LogCaptureFixture,
):
    """Test discovery when list_tools returns an unexpected format."""
    client_id = "client_bad_format"
    # Mock list_tools to return something without a .tools attribute
    mock_client_session.list_tools = AsyncMock(return_value={"wrong": "format"})

    caplog.set_level("WARNING")
    discovered = await tool_manager.discover_client_tools(client_id, mock_client_session)

    assert discovered == []
    mock_client_session.list_tools.assert_called_once()
    assert f"Unexpected response format from list_tools for client {client_id}" in caplog.text


async def test_discover_client_tools_exception(
    tool_manager: ToolManager,
    mock_client_session: MagicMock,
):
    """Test discovery when list_tools raises an exception."""
    client_id = "client_exception"
    mock_client_session.list_tools = AsyncMock(side_effect=RuntimeError("Connection failed"))

    with pytest.raises(RuntimeError, match="Connection failed"):
        await tool_manager.discover_client_tools(client_id, mock_client_session)

    mock_client_session.list_tools.assert_called_once()


# --- Tests for execute_tool ---

async def test_execute_tool_success_unique_client(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_root_manager: MagicMock,
    mock_client_session: MagicMock,
    sample_tool: types.Tool,
):
    """Test successful tool execution when the tool is found on a unique client."""
    client_id = "client_T_exec"
    tool_name = sample_tool.name
    arguments = {"arg1": "value1"}

    # Setup mocks
    tool_manager.register_client(client_id, mock_client_session)
    mock_message_router.get_clients_for_tool = AsyncMock(return_value=[client_id])
    mock_root_manager.validate_access = AsyncMock() # Mock the async method
    mock_client_session.call_tool = AsyncMock(return_value=types.CallToolResult(content=[types.TextContent(type="text", text="Success!")]))

    result = await tool_manager.execute_tool(tool_name=tool_name, arguments=arguments)

    assert result == [types.TextContent(type="text", text="Success!")]
    mock_message_router.get_clients_for_tool.assert_called_once_with(tool_name)
    mock_root_manager.validate_access.assert_called_once_with(client_id=client_id)
    mock_client_session.call_tool.assert_called_once_with(tool_name, arguments)


async def test_execute_tool_success_specific_client(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_root_manager: MagicMock,
    mock_client_session: MagicMock,
    sample_tool: types.Tool,
):
    """Test successful tool execution when a specific client is provided."""
    client_id = "client_T_spec"
    tool_name = sample_tool.name
    arguments = {"arg1": "value1"}

    # Setup mocks
    tool_manager.register_client(client_id, mock_client_session)
    # Router needs to confirm this client provides the tool
    mock_message_router.get_clients_for_tool = AsyncMock(return_value=[client_id, "other_client"])
    mock_root_manager.validate_access = AsyncMock()
    mock_client_session.call_tool = AsyncMock(return_value=types.CallToolResult(content=[types.TextContent(type="text", text="Specific Success!")]))

    result = await tool_manager.execute_tool(
        tool_name=tool_name, arguments=arguments, client_name=client_id
    )

    assert result == [types.TextContent(type="text", text="Specific Success!")]
    # Router is still called to validate the specific client provides the tool
    mock_message_router.get_clients_for_tool.assert_called_once_with(tool_name)
    mock_root_manager.validate_access.assert_called_once_with(client_id=client_id)
    mock_client_session.call_tool.assert_called_once_with(tool_name, arguments)


async def test_execute_tool_fail_not_found(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
):
    """Test execution failure when the tool is not found on any client."""
    tool_name = "unknown_tool"
    arguments = {}
    mock_message_router.get_clients_for_tool = AsyncMock(return_value=[]) # No clients provide it

    with pytest.raises(ValueError, match=f"Tool '{tool_name}' not found on any registered client."):
        await tool_manager.execute_tool(tool_name=tool_name, arguments=arguments)

    mock_message_router.get_clients_for_tool.assert_called_once_with(tool_name)


async def test_execute_tool_fail_ambiguous(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
):
    """Test execution failure when the tool is ambiguous and no client is specified."""
    tool_name = "ambiguous_tool"
    arguments = {}
    providing_clients = ["client1", "client2"]
    mock_message_router.get_clients_for_tool = AsyncMock(return_value=providing_clients)

    expected_error_msg = f"Tool '{tool_name}' is ambiguous; found on multiple clients: {providing_clients}. Specify a client_name."
    with pytest.raises(ValueError, match=re.escape(expected_error_msg)): # Escape the error message
        await tool_manager.execute_tool(tool_name=tool_name, arguments=arguments)

    mock_message_router.get_clients_for_tool.assert_called_once_with(tool_name)


async def test_execute_tool_fail_specific_client_not_registered(
    tool_manager: ToolManager,
):
    """Test execution failure when the specified client is not registered."""
    tool_name = "some_tool"
    arguments = {}
    client_name = "unregistered_client"
    # No need to mock router, check happens before

    with pytest.raises(ValueError, match=f"Specified client '{client_name}' is not registered."):
        await tool_manager.execute_tool(tool_name=tool_name, arguments=arguments, client_name=client_name)


async def test_execute_tool_fail_specific_client_does_not_provide(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_client_session: MagicMock, # Need a registered client
):
    """Test execution failure when the specified client doesn't provide the tool."""
    client_id = "client_T_noprovide"
    tool_name = "tool_x"
    arguments = {}
    tool_manager.register_client(client_id, mock_client_session)
    # Mock router to return other clients, but not this one
    mock_message_router.get_clients_for_tool = AsyncMock(return_value=["other_client"])

    with pytest.raises(ValueError, match=f"Specified client '{client_id}' does not provide tool '{tool_name}'."):
        await tool_manager.execute_tool(tool_name=tool_name, arguments=arguments, client_name=client_id)

    mock_message_router.get_clients_for_tool.assert_called_once_with(tool_name)


async def test_execute_tool_fail_root_validation(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_root_manager: MagicMock,
    mock_client_session: MagicMock,
    sample_tool: types.Tool,
):
    """Test execution failure when root validation fails."""
    client_id = "client_T_rootfail"
    tool_name = sample_tool.name
    arguments = {"arg1": "value1"}

    # Setup mocks
    tool_manager.register_client(client_id, mock_client_session)
    mock_message_router.get_clients_for_tool = AsyncMock(return_value=[client_id])
    # Mock root manager to raise validation error
    mock_root_manager.validate_access = AsyncMock(side_effect=ValueError("Access Denied"))

    with pytest.raises(ValueError, match="Access Denied"):
        await tool_manager.execute_tool(tool_name=tool_name, arguments=arguments)

    mock_message_router.get_clients_for_tool.assert_called_once_with(tool_name)
    mock_root_manager.validate_access.assert_called_once_with(client_id=client_id)
    mock_client_session.call_tool.assert_not_called() # Should fail before calling tool


async def test_execute_tool_fail_call_tool_exception(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_root_manager: MagicMock,
    mock_client_session: MagicMock,
    sample_tool: types.Tool,
):
    """Test execution failure when the client session's call_tool raises an exception."""
    client_id = "client_T_callfail"
    tool_name = sample_tool.name
    arguments = {"arg1": "value1"}

    # Setup mocks
    tool_manager.register_client(client_id, mock_client_session)
    mock_message_router.get_clients_for_tool = AsyncMock(return_value=[client_id])
    mock_root_manager.validate_access = AsyncMock()
    # Mock call_tool to raise an error
    mock_client_session.call_tool = AsyncMock(side_effect=ConnectionError("Network Error"))

    with pytest.raises(ConnectionError, match="Network Error"):
        await tool_manager.execute_tool(tool_name=tool_name, arguments=arguments)

    mock_message_router.get_clients_for_tool.assert_called_once_with(tool_name)
    mock_root_manager.validate_access.assert_called_once_with(client_id=client_id)
    mock_client_session.call_tool.assert_called_once_with(tool_name, arguments)


async def test_execute_tool_fail_call_tool_returns_error(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_root_manager: MagicMock,
    mock_client_session: MagicMock,
    sample_tool: types.Tool,
):
    """Test execution failure when the client session's call_tool returns an error result."""
    client_id = "client_T_resulterr"
    tool_name = sample_tool.name
    arguments = {"arg1": "value1"}
    error_message = "Tool failed internally"

    # Setup mocks
    tool_manager.register_client(client_id, mock_client_session)
    mock_message_router.get_clients_for_tool = AsyncMock(return_value=[client_id])
    mock_root_manager.validate_access = AsyncMock()
    # Mock call_tool to return an error CallToolResult
    error_result = types.CallToolResult(
        isError=True,
        content=[types.TextContent(type="text", text=error_message)]
    )
    mock_client_session.call_tool = AsyncMock(return_value=error_result)

    with pytest.raises(ValueError, match=f"Tool execution failed: {error_message}"):
        await tool_manager.execute_tool(tool_name=tool_name, arguments=arguments)

    mock_message_router.get_clients_for_tool.assert_called_once_with(tool_name)
    mock_root_manager.validate_access.assert_called_once_with(client_id=client_id)
    mock_client_session.call_tool.assert_called_once_with(tool_name, arguments)


# --- Tests for get_tool / has_tool ---

async def test_get_tool_and_has_tool(
    tool_manager: ToolManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
    sample_tool: types.Tool,
):
    """Test get_tool and has_tool for existing and non-existing tools."""
    # Pre-check
    assert tool_manager.get_tool(sample_tool.name) is None
    assert tool_manager.has_tool(sample_tool.name) is False
    assert tool_manager.get_tool("non_existent_tool") is None
    assert tool_manager.has_tool("non_existent_tool") is False

    # Register the tool
    await tool_manager.register_tool(
        tool_name=sample_tool.name,
        tool=sample_tool,
        client_id=sample_client_config.client_id,
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # Post-check
    assert tool_manager.has_tool(sample_tool.name) is True
    retrieved_tool = tool_manager.get_tool(sample_tool.name)
    assert retrieved_tool == sample_tool

    # Check non-existent again
    assert tool_manager.get_tool("non_existent_tool") is None
    assert tool_manager.has_tool("non_existent_tool") is False


# --- Tests for format_tools_for_llm ---

# Helper function to register multiple tools for testing formatting
async def _register_test_tools(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    tools_to_register: List[Dict[str, Any]], # Expects dicts with tool, client_id, client_config
):
    for item in tools_to_register:
        await tool_manager.register_tool(
            tool_name=item["tool"].name,
            tool=item["tool"],
            client_id=item["client_id"],
            client_config=item["client_config"],
            filtering_manager=mock_filtering_manager,
        )

# Define some tools and configs for reuse in formatting tests
tool_A1 = types.Tool(name="tool_A1", description="Tool 1 from Client A", inputSchema={"type": "object", "properties": {"p1": {"type": "string"}}})
tool_A2 = types.Tool(name="tool_A2", description="Tool 2 from Client A", inputSchema={"type": "object", "properties": {}})
tool_B1 = types.Tool(name="tool_B1", description="Tool 1 from Client B", inputSchema={"type": "object", "properties": {"q1": {"type": "integer"}}})
config_A = ClientConfig(client_id="clientA", server_path="path/A", capabilities=["tools"], roots=[])
config_B = ClientConfig(client_id="clientB", server_path="path/B", capabilities=["tools"], roots=[])

async def test_format_tools_for_llm_no_tools(
    tool_manager: ToolManager,
    mock_filtering_manager: MagicMock,
    sample_agent_config: AgentConfig,
):
    """Test formatting when no tools are registered."""
    formatted = tool_manager.format_tools_for_llm(
        filtering_manager=mock_filtering_manager,
        agent_config=sample_agent_config
    )
    assert formatted == []

async def test_format_tools_for_llm_basic(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
):
    """Test basic formatting with multiple tools, no agent filtering."""
    await _register_test_tools(tool_manager, mock_message_router, mock_filtering_manager, [
        {"tool": tool_A1, "client_id": "clientA", "client_config": config_A},
        {"tool": tool_B1, "client_id": "clientB", "client_config": config_B},
    ])

    # No agent config means no filtering applied by default in this mock setup
    formatted = tool_manager.format_tools_for_llm(filtering_manager=mock_filtering_manager)

    assert len(formatted) == 2
    # Check structure of one tool
    tool_a1_formatted = next(t for t in formatted if t["name"] == "tool_A1")
    assert tool_a1_formatted == {
        "name": tool_A1.name,
        "description": tool_A1.description,
        "input_schema": tool_A1.inputSchema,
    }
    tool_b1_formatted = next(t for t in formatted if t["name"] == "tool_B1")
    assert tool_b1_formatted == {
        "name": tool_B1.name,
        "description": tool_B1.description,
        "input_schema": tool_B1.inputSchema,
    }

async def test_format_tools_for_llm_filter_client_ids(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
):
    """Test formatting tools filtered by agent_config.client_ids."""
    await _register_test_tools(tool_manager, mock_message_router, mock_filtering_manager, [
        {"tool": tool_A1, "client_id": "clientA", "client_config": config_A},
        {"tool": tool_A2, "client_id": "clientA", "client_config": config_A},
        {"tool": tool_B1, "client_id": "clientB", "client_config": config_B},
    ])

    # Agent config allowing only clientA
    agent_config_client_a = AgentConfig(name="agent_a", client_ids=["clientA"])

    # Configure mock filtering manager to simulate client filtering
    original_filter = mock_filtering_manager.filter_clients_for_request
    mock_filtering_manager.filter_clients_for_request = MagicMock(return_value=["clientA"])

    formatted = tool_manager.format_tools_for_llm(
        filtering_manager=mock_filtering_manager,
        agent_config=agent_config_client_a
    )

    # Restore mock
    mock_filtering_manager.filter_clients_for_request = original_filter

    assert len(formatted) == 2
    assert all(t["name"] in ["tool_A1", "tool_A2"] for t in formatted)
    assert not any(t["name"] == "tool_B1" for t in formatted)
    # Check structure
    tool_a1_formatted = next(t for t in formatted if t["name"] == "tool_A1")
    assert tool_a1_formatted["input_schema"] == tool_A1.inputSchema


async def test_format_tools_for_llm_filter_exclude_components(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
):
    """Test formatting tools filtered by agent_config.exclude_components."""
    await _register_test_tools(tool_manager, mock_message_router, mock_filtering_manager, [
        {"tool": tool_A1, "client_id": "clientA", "client_config": config_A}, # To be excluded
        {"tool": tool_A2, "client_id": "clientA", "client_config": config_A},
        {"tool": tool_B1, "client_id": "clientB", "client_config": config_B},
    ])

    # Agent config excluding tool_A1
    agent_config_exclude_a1 = AgentConfig(name="agent_exclude", exclude_components=["tool_A1"])

    # --- Mock FilteringManager ---
    # 1. Mock client filtering: Since this agent_config doesn't restrict clients,
    #    filter_clients_for_request should return all clients providing tools.
    original_client_filter = mock_filtering_manager.filter_clients_for_request
    mock_filtering_manager.filter_clients_for_request = MagicMock(return_value=["clientA", "clientB"])

    # 2. Mock component exclusion
    original_component_filter = mock_filtering_manager.filter_component_list
    def exclude_side_effect(components, config):
        excluded = config.exclude_components or []
        return [c for c in components if c.get("name") not in excluded]
    # Assign side_effect directly to the existing mock attribute
    mock_filtering_manager.filter_component_list.side_effect = exclude_side_effect

    # --- Execute ---
    formatted = tool_manager.format_tools_for_llm(
        filtering_manager=mock_filtering_manager,
        agent_config=agent_config_exclude_a1
    )

    # --- Restore mocks ---
    mock_filtering_manager.filter_clients_for_request = original_client_filter
    mock_filtering_manager.filter_component_list.side_effect = None # Reset side effect

    # --- Assert ---
    assert len(formatted) == 2
    assert all(t["name"] in ["tool_A2", "tool_B1"] for t in formatted)
    assert not any(t["name"] == "tool_A1" for t in formatted)


async def test_format_tools_for_llm_filter_both(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
):
    """Test formatting tools filtered by both client_ids and exclude_components."""
    await _register_test_tools(tool_manager, mock_message_router, mock_filtering_manager, [
        {"tool": tool_A1, "client_id": "clientA", "client_config": config_A}, # Allowed client, but excluded component
        {"tool": tool_A2, "client_id": "clientA", "client_config": config_A}, # Allowed client, allowed component
        {"tool": tool_B1, "client_id": "clientB", "client_config": config_B}, # Disallowed client
    ])

    # Agent config allowing clientA but excluding tool_A1
    agent_config_complex = AgentConfig(name="agent_complex", client_ids=["clientA"], exclude_components=["tool_A1"])

    # Configure mocks for both filtering steps
    mock_filtering_manager.filter_clients_for_request = MagicMock(return_value=["clientA"])
    def exclude_side_effect(components, config):
        # Corrected indentation within the function
        excluded = config.exclude_components or []
        # Important: filter_component_list receives list of dicts from list_tools
        return [c for c in components if c.get("name") not in excluded]
    # Assign side_effect directly to the existing mock attribute
    mock_filtering_manager.filter_component_list.side_effect = exclude_side_effect

    # Corrected indentation for subsequent lines
    formatted = tool_manager.format_tools_for_llm(
        filtering_manager=mock_filtering_manager,
        agent_config=agent_config_complex
    )

    # Restore mock side_effect
    mock_filtering_manager.filter_component_list.side_effect = None # Reset side effect

    assert len(formatted) == 1
    assert formatted[0]["name"] == "tool_A2"
    assert formatted[0]["description"] == tool_A2.description
    assert formatted[0]["input_schema"] == tool_A2.inputSchema


async def test_format_tools_for_llm_filter_tool_names_arg(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
):
    """Test formatting tools filtered by the tool_names argument."""
    await _register_test_tools(tool_manager, mock_message_router, mock_filtering_manager, [
        {"tool": tool_A1, "client_id": "clientA", "client_config": config_A},
        {"tool": tool_A2, "client_id": "clientA", "client_config": config_A},
        {"tool": tool_B1, "client_id": "clientB", "client_config": config_B},
    ])

    # Request only tool_A1 and tool_B1 (even though A2 is available)
    formatted = tool_manager.format_tools_for_llm(
        filtering_manager=mock_filtering_manager,
        tool_names=["tool_A1", "tool_B1"] # Specify names
    )

    assert len(formatted) == 2
    assert all(t["name"] in ["tool_A1", "tool_B1"] for t in formatted)
    assert not any(t["name"] == "tool_A2" for t in formatted)


async def test_format_tools_for_llm_ensure_schema_type(
    tool_manager: ToolManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test that 'type': 'object' is added to schema if missing."""
    tool_no_type = types.Tool(
        name="no_type_tool",
        description="Tool schema missing type",
        inputSchema={"properties": {"p1": {"type": "string"}}} # Missing top-level type
    )
    await _register_test_tools(tool_manager, mock_message_router, mock_filtering_manager, [
        {"tool": tool_no_type, "client_id": sample_client_config.client_id, "client_config": sample_client_config},
    ])

    formatted = tool_manager.format_tools_for_llm(filtering_manager=mock_filtering_manager)

    assert len(formatted) == 1
    assert formatted[0]["name"] == "no_type_tool"
    # Verify 'type': 'object' was added
    assert formatted[0]["input_schema"] == {"type": "object", "properties": {"p1": {"type": "string"}}}


# --- Tests for format_tool_result ---

def test_format_tool_result_string(tool_manager: ToolManager):
    """Test formatting a simple string result."""
    result = "Simple success"
    formatted = tool_manager.format_tool_result(result)
    assert formatted == "Simple success"

def test_format_tool_result_list_text_content(tool_manager: ToolManager):
    """Test formatting a list of TextContent objects."""
    result = [
        types.TextContent(type="text", text="Part 1."),
        types.TextContent(type="text", text="Part 2.")
    ]
    formatted = tool_manager.format_tool_result(result)
    assert formatted == "Part 1.\nPart 2."

def test_format_tool_result_other_types(tool_manager: ToolManager):
    """Test formatting other types falls back to str()."""
    result_dict = {"key": "value"}
    result_int = 123
    assert tool_manager.format_tool_result(result_dict) == "{'key': 'value'}"
    assert tool_manager.format_tool_result(result_int) == "123"


# --- Tests for create_tool_result_blocks ---

def test_create_tool_result_blocks_string(tool_manager: ToolManager):
    """Test creating result blocks from a simple string."""
    tool_use_id = "toolu_123"
    result = "Simple success"
    blocks = tool_manager.create_tool_result_blocks(tool_use_id, result)
    expected = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": [{"type": "text", "text": "Simple success"}],
    }
    assert blocks == expected

def test_create_tool_result_blocks_list_text_content(tool_manager: ToolManager):
    """Test creating result blocks from a list of TextContent."""
    tool_use_id = "toolu_456"
    result = [
        types.TextContent(type="text", text="First part."),
        types.TextContent(type="text", text="Second part.")
    ]
    blocks = tool_manager.create_tool_result_blocks(tool_use_id, result)
    expected = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": [
            {"type": "text", "text": "First part."},
            {"type": "text", "text": "Second part."}
        ],
    }
    assert blocks == expected

def test_create_tool_result_blocks_other_types(tool_manager: ToolManager):
    """Test creating result blocks from other types (fallback to str)."""
    tool_use_id = "toolu_789"
    result_dict = {"a": 1}
    blocks = tool_manager.create_tool_result_blocks(tool_use_id, result_dict)
    expected = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": [{"type": "text", "text": "{'a': 1}"}],
    }
    assert blocks == expected


# --- Test for shutdown ---

async def test_shutdown(
    tool_manager: ToolManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
    sample_tool: types.Tool,
    mock_client_session: MagicMock,
):
    """Test the shutdown process clears internal state."""
    client_id = sample_client_config.client_id
    # Register client and tool
    tool_manager.register_client(client_id, mock_client_session)
    await tool_manager.register_tool(
        tool_name=sample_tool.name,
        tool=sample_tool,
        client_id=client_id,
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # Ensure state is populated
    assert client_id in tool_manager._clients
    assert sample_tool.name in tool_manager._tools
    assert sample_tool.name in tool_manager._tool_metadata

    # Call shutdown
    await tool_manager.shutdown()

    # Assert internal state is cleared
    assert tool_manager._clients == {}
    assert tool_manager._tools == {}
    assert tool_manager._tool_metadata == {}
