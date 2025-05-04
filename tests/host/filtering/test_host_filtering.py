"""
Unit tests for MCPHost convenience method filtering logic.

These tests verify that the `filter_client_ids` parameter correctly restricts
client discovery and execution/retrieval in methods like `execute_tool`,
`get_prompt`, and `read_resource`. Managers are mocked to isolate host logic.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict

import mcp.types as types
from src.host.host import MCPHost
from src.host.models import HostConfig, ClientConfig
from src.host.resources import ToolManager, PromptManager, ResourceManager
from src.host.foundation import (
    MessageRouter,
    RootManager as FoundationRootManager,
    SecurityManager,
)

# --- Test Fixtures ---

CLIENT_A = "client-a"
CLIENT_B = "client-b"
CLIENT_C = "client-c"


@pytest.fixture
def mock_managers() -> Dict[str, Mock]:
    """Provides mocked manager instances."""
    # Create the router mock separately to configure it
    router_mock = AsyncMock(spec=MessageRouter)
    # Explicitly add the methods expected by the tests to the mock
    # We need get_clients_for_tool, get_clients_for_prompt, AND get_clients_for_resource
    router_mock.get_clients_for_tool = AsyncMock()
    router_mock.get_clients_for_prompt = AsyncMock()
    router_mock.get_clients_for_resource = AsyncMock()  # Add the missing one

    return {
        "tool_manager": AsyncMock(spec=ToolManager),
        "prompt_manager": AsyncMock(spec=PromptManager),
        "resource_manager": AsyncMock(spec=ResourceManager),
        "message_router": router_mock,  # Use the configured mock
        "root_manager": AsyncMock(spec=FoundationRootManager),
        "security_manager": AsyncMock(spec=SecurityManager),
    }


@pytest.fixture
def host_config_for_filtering() -> HostConfig:
    """Provides a HostConfig with multiple dummy clients."""
    # Paths don't matter as client initialization will be mocked
    return HostConfig(
        name="FilteringTestHost",
        clients=[
            ClientConfig(
                client_id=CLIENT_A,
                server_path="a.py",
                roots=[],
                capabilities=["tools", "prompts"],
            ),
            ClientConfig(
                client_id=CLIENT_B,
                server_path="b.py",
                roots=[],
                capabilities=["tools", "resources"],
            ),
            ClientConfig(
                client_id=CLIENT_C,
                server_path="c.py",
                roots=[],
                capabilities=["prompts", "resources"],
            ),
        ],
    )


@pytest.fixture
def host_for_filtering(
    host_config_for_filtering: HostConfig, mock_managers: Dict[str, Mock]
) -> MCPHost:
    """
    Provides an MCPHost instance ready for testing filtering logic.
    Managers are replaced with mocks. Client initialization is skipped.
    """
    # Patch the manager constructors within MCPHost.__init__
    with (
        patch(
            "src.host.host.SecurityManager",
            return_value=mock_managers["security_manager"],
        ),
        patch("src.host.host.RootManager", return_value=mock_managers["root_manager"]),
        patch(
            "src.host.host.MessageRouter", return_value=mock_managers["message_router"]
        ),
        patch(
            "src.host.host.PromptManager", return_value=mock_managers["prompt_manager"]
        ),
        patch(
            "src.host.host.ResourceManager",
            return_value=mock_managers["resource_manager"],
        ),
        patch("src.host.host.ToolManager", return_value=mock_managers["tool_manager"]),
    ):
        host = MCPHost(config=host_config_for_filtering)
        # Assign mocks directly to host attributes for easier access in tests
        host._security_manager = mock_managers["security_manager"]
        host._root_manager = mock_managers["root_manager"]
        host._message_router = mock_managers["message_router"]
        host._prompt_manager = mock_managers["prompt_manager"]
        host.prompts = mock_managers["prompt_manager"]  # Public accessor
        host._resource_manager = mock_managers["resource_manager"]
        host.resources = mock_managers["resource_manager"]  # Public accessor
        host._tool_manager = mock_managers["tool_manager"]
        host.tools = mock_managers["tool_manager"]  # Public accessor

        # Skip actual host.initialize() as we are mocking managers
        # and don't need real client connections for these unit tests.
        return host


# --- Filtering Tests ---


@pytest.mark.unit
class TestHostFiltering:
    """Tests the filter_client_ids parameter on MCPHost convenience methods."""

    # --- execute_tool Tests ---

    @pytest.mark.asyncio
    async def test_execute_tool_filter_success_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Filter finds unique client for tool discovery."""
        tool_name = "tool_only_on_b"
        filter_list = [CLIENT_B, CLIENT_C]
        # Mock router to return multiple clients initially, but only B within filter
        mock_managers["message_router"].get_clients_for_tool = AsyncMock(
            return_value=[CLIENT_A, CLIENT_B]
        )
        mock_managers["tool_manager"].execute_tool = AsyncMock(
            return_value="tool_b_result"
        )

        result = await host_for_filtering.execute_tool(
            tool_name=tool_name, arguments={}, filter_client_ids=filter_list
        )

        mock_managers["message_router"].get_clients_for_tool.assert_awaited_once_with(
            tool_name
        )
        # Assert execute_tool was called on the *correct* filtered client
        mock_managers["tool_manager"].execute_tool.assert_awaited_once_with(
            client_name=CLIENT_B, tool_name=tool_name, arguments={}
        )
        assert result == "tool_b_result"

    @pytest.mark.asyncio
    async def test_execute_tool_filter_ambiguous_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Filter still results in multiple clients -> raises ValueError."""
        tool_name = "tool_on_a_and_b"
        filter_list = [CLIENT_A, CLIENT_B, CLIENT_C]
        mock_managers["message_router"].get_clients_for_tool = AsyncMock(
            return_value=[CLIENT_A, CLIENT_B]
        )

        with pytest.raises(ValueError, match="ambiguous within the filter"):
            await host_for_filtering.execute_tool(
                tool_name=tool_name, arguments={}, filter_client_ids=filter_list
            )
        mock_managers["message_router"].get_clients_for_tool.assert_awaited_once_with(
            tool_name
        )
        mock_managers["tool_manager"].execute_tool.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_tool_filter_not_found_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Tool exists, but not on any client within the filter."""
        tool_name = "tool_only_on_a"
        filter_list = [CLIENT_B, CLIENT_C]  # A is excluded
        mock_managers["message_router"].get_clients_for_tool = AsyncMock(
            return_value=[CLIENT_A]
        )

        with pytest.raises(
            ValueError, match="not found on any registered client matching the filter"
        ):
            await host_for_filtering.execute_tool(
                tool_name=tool_name, arguments={}, filter_client_ids=filter_list
            )
        mock_managers["message_router"].get_clients_for_tool.assert_awaited_once_with(
            tool_name
        )
        mock_managers["tool_manager"].execute_tool.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_tool_filter_direct_success(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Filter allows specified client_name."""
        tool_name = "tool_on_b"
        filter_list = [CLIENT_B, CLIENT_C]
        mock_managers["tool_manager"].execute_tool = AsyncMock(
            return_value="tool_b_direct_result"
        )

        result = await host_for_filtering.execute_tool(
            tool_name=tool_name,
            arguments={},
            client_name=CLIENT_B,
            filter_client_ids=filter_list,
        )

        # Discovery via router should NOT be called when client_name is specified
        mock_managers["message_router"].get_clients_for_tool.assert_not_called()
        mock_managers["tool_manager"].execute_tool.assert_awaited_once_with(
            client_name=CLIENT_B, tool_name=tool_name, arguments={}
        )
        assert result == "tool_b_direct_result"

    @pytest.mark.asyncio
    async def test_execute_tool_filter_direct_fail_excluded(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Specified client_name is excluded by the filter -> raises ValueError."""
        tool_name = "tool_on_a"
        filter_list = [CLIENT_B, CLIENT_C]  # Excludes A

        with pytest.raises(ValueError, match="not in the allowed filter list"):
            await host_for_filtering.execute_tool(
                tool_name=tool_name,
                arguments={},
                client_name=CLIENT_A,
                filter_client_ids=filter_list,
            )
        # Discovery via router should NOT be called
        mock_managers["message_router"].get_clients_for_tool.assert_not_called()
        mock_managers["tool_manager"].execute_tool.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_tool_no_filter_success_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """No filter, unique client found."""
        tool_name = "tool_only_on_c"  # Assume only C provides this
        mock_managers["message_router"].get_clients_for_tool = AsyncMock(
            return_value=[CLIENT_C]
        )
        mock_managers["tool_manager"].execute_tool = AsyncMock(
            return_value="tool_c_result"
        )

        result = await host_for_filtering.execute_tool(
            tool_name=tool_name, arguments={}
        )

        mock_managers["message_router"].get_clients_for_tool.assert_awaited_once_with(
            tool_name
        )
        mock_managers["tool_manager"].execute_tool.assert_awaited_once_with(
            client_name=CLIENT_C, tool_name=tool_name, arguments={}
        )
        assert result == "tool_c_result"

    @pytest.mark.asyncio
    async def test_execute_tool_no_filter_ambiguous_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """No filter, multiple clients found -> raises ValueError."""
        tool_name = "tool_on_a_and_b"
        mock_managers["message_router"].get_clients_for_tool = AsyncMock(
            return_value=[CLIENT_A, CLIENT_B]
        )

        with pytest.raises(
            ValueError, match="ambiguous"
        ):  # Don't check "within filter" part
            await host_for_filtering.execute_tool(tool_name=tool_name, arguments={})
        mock_managers["message_router"].get_clients_for_tool.assert_awaited_once_with(
            tool_name
        )
        mock_managers["tool_manager"].execute_tool.assert_not_awaited()

    # --- get_prompt Tests (Structure mirrors execute_tool tests) ---

    @pytest.mark.asyncio
    async def test_get_prompt_filter_success_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Filter finds unique client for prompt discovery."""
        prompt_name = "prompt_only_on_c"
        filter_list = [CLIENT_B, CLIENT_C]
        mock_prompt_def = types.Prompt(name=prompt_name, description="...")
        mock_managers["message_router"].get_clients_for_prompt = AsyncMock(
            return_value=[CLIENT_A, CLIENT_C]
        )
        mock_managers["prompt_manager"].get_prompt = AsyncMock(
            return_value=mock_prompt_def
        )

        result = await host_for_filtering.get_prompt(
            prompt_name=prompt_name, arguments={}, filter_client_ids=filter_list
        )

        mock_managers["message_router"].get_clients_for_prompt.assert_awaited_once_with(
            prompt_name
        )
        mock_managers["prompt_manager"].get_prompt.assert_awaited_once_with(
            name=prompt_name, client_id=CLIENT_C
        )
        assert result == mock_prompt_def

    @pytest.mark.asyncio
    async def test_get_prompt_filter_ambiguous_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Filter still results in multiple clients -> raises ValueError."""
        prompt_name = "prompt_on_a_and_c"
        filter_list = [CLIENT_A, CLIENT_B, CLIENT_C]
        mock_managers["message_router"].get_clients_for_prompt = AsyncMock(
            return_value=[CLIENT_A, CLIENT_C]
        )

        with pytest.raises(ValueError, match="ambiguous within the filter"):
            await host_for_filtering.get_prompt(
                prompt_name=prompt_name, arguments={}, filter_client_ids=filter_list
            )
        mock_managers["message_router"].get_clients_for_prompt.assert_awaited_once_with(
            prompt_name
        )
        mock_managers["prompt_manager"].get_prompt.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_prompt_filter_not_found_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Prompt exists, but not on any client within the filter."""
        prompt_name = "prompt_only_on_a"
        filter_list = [CLIENT_B, CLIENT_C]  # A is excluded
        mock_managers["message_router"].get_clients_for_prompt = AsyncMock(
            return_value=[CLIENT_A]
        )

        # get_prompt returns None if not found after filtering, doesn't raise error itself
        result = await host_for_filtering.get_prompt(
            prompt_name=prompt_name, arguments={}, filter_client_ids=filter_list
        )
        assert result is None
        mock_managers["message_router"].get_clients_for_prompt.assert_awaited_once_with(
            prompt_name
        )
        mock_managers["prompt_manager"].get_prompt.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_prompt_filter_direct_success(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Filter allows specified client_name."""
        prompt_name = "prompt_on_c"
        filter_list = [CLIENT_B, CLIENT_C]
        mock_prompt_def = types.Prompt(name=prompt_name, description="...")
        mock_managers["prompt_manager"].get_prompt = AsyncMock(
            return_value=mock_prompt_def
        )

        result = await host_for_filtering.get_prompt(
            prompt_name=prompt_name,
            arguments={},
            client_name=CLIENT_C,
            filter_client_ids=filter_list,
        )

        # Discovery via router should NOT be called
        mock_managers["message_router"].get_clients_for_prompt.assert_not_called()
        mock_managers["prompt_manager"].get_prompt.assert_awaited_once_with(
            name=prompt_name, client_id=CLIENT_C
        )
        assert result == mock_prompt_def

    @pytest.mark.asyncio
    async def test_get_prompt_filter_direct_fail_excluded(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Specified client_name is excluded by the filter -> raises ValueError."""
        prompt_name = "prompt_on_a"
        filter_list = [CLIENT_B, CLIENT_C]  # Excludes A

        with pytest.raises(ValueError, match="not in the allowed filter list"):
            await host_for_filtering.get_prompt(
                prompt_name=prompt_name,
                arguments={},
                client_name=CLIENT_A,
                filter_client_ids=filter_list,
            )
        # Discovery via router should NOT be called
        mock_managers["message_router"].get_clients_for_prompt.assert_not_called()
        mock_managers["prompt_manager"].get_prompt.assert_not_awaited()

    # --- read_resource Tests (Structure mirrors get_prompt tests) ---

    @pytest.mark.asyncio
    async def test_read_resource_filter_success_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Filter finds unique client for resource discovery."""
        uri = "resource://on_b_only"
        filter_list = [CLIENT_B, CLIENT_C]
        mock_resource_def = types.Resource(uri=uri, name="res_b")
        mock_managers["message_router"].get_clients_for_resource = AsyncMock(
            return_value=[CLIENT_A, CLIENT_B]
        )
        mock_managers["resource_manager"].get_resource = AsyncMock(
            return_value=mock_resource_def
        )

        result = await host_for_filtering.read_resource(
            uri=uri, filter_client_ids=filter_list
        )

        mock_managers[
            "message_router"
        ].get_clients_for_resource.assert_awaited_once_with(uri)
        mock_managers["resource_manager"].get_resource.assert_awaited_once_with(
            uri=uri, client_id=CLIENT_B
        )
        assert result == mock_resource_def

    @pytest.mark.asyncio
    async def test_read_resource_filter_ambiguous_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Filter still results in multiple clients -> raises ValueError."""
        uri = "resource://on_b_and_c"
        filter_list = [CLIENT_A, CLIENT_B, CLIENT_C]
        mock_managers["message_router"].get_clients_for_resource = AsyncMock(
            return_value=[CLIENT_B, CLIENT_C]
        )

        with pytest.raises(ValueError, match="ambiguous within the filter"):
            await host_for_filtering.read_resource(
                uri=uri, filter_client_ids=filter_list
            )
        mock_managers[
            "message_router"
        ].get_clients_for_resource.assert_awaited_once_with(uri)
        mock_managers["resource_manager"].get_resource.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_read_resource_filter_not_found_discovery(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Resource exists, but not on any client within the filter."""
        uri = "resource://on_a_only"
        filter_list = [CLIENT_B, CLIENT_C]  # A is excluded
        mock_managers["message_router"].get_clients_for_resource = AsyncMock(
            return_value=[CLIENT_A]
        )

        result = await host_for_filtering.read_resource(
            uri=uri, filter_client_ids=filter_list
        )
        assert result is None
        mock_managers[
            "message_router"
        ].get_clients_for_resource.assert_awaited_once_with(uri)
        mock_managers["resource_manager"].get_resource.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_read_resource_filter_direct_success(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Filter allows specified client_name."""
        uri = "resource://on_c"
        filter_list = [CLIENT_B, CLIENT_C]
        mock_resource_def = types.Resource(uri=uri, name="res_c")
        mock_managers["resource_manager"].get_resource = AsyncMock(
            return_value=mock_resource_def
        )

        result = await host_for_filtering.read_resource(
            uri=uri, client_name=CLIENT_C, filter_client_ids=filter_list
        )

        # Discovery via router should NOT be called
        mock_managers["message_router"].get_clients_for_resource.assert_not_called()
        mock_managers["resource_manager"].get_resource.assert_awaited_once_with(
            uri=uri, client_id=CLIENT_C
        )
        assert result == mock_resource_def

    @pytest.mark.asyncio
    async def test_read_resource_filter_direct_fail_excluded(
        self, host_for_filtering: MCPHost, mock_managers: Dict[str, Mock]
    ):
        """Specified client_name is excluded by the filter -> raises ValueError."""
        uri = "resource://on_b"
        filter_list = [CLIENT_A, CLIENT_C]  # Excludes B

        with pytest.raises(ValueError, match="not in the allowed filter list"):
            await host_for_filtering.read_resource(
                uri=uri, client_name=CLIENT_B, filter_client_ids=filter_list
            )
        # Discovery via router should NOT be called
        mock_managers["message_router"].get_clients_for_resource.assert_not_called()
        mock_managers["resource_manager"].get_resource.assert_not_awaited()
