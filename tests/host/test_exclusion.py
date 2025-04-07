"""
Tests for MCP component exclusion functionality in the MCPHost and its managers.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import mcp.types as types
from src.host.host import MCPHost
from src.host.models import HostConfig, ClientConfig
from pathlib import Path
from mcp import ClientSession

# --- Test Fixtures ---


@pytest.fixture
def mock_exclusion_client_session():
    """Creates a mock ClientSession that returns predefined components."""
    session = AsyncMock(spec=ClientSession)

    # Define the components this mock client "provides"
    mock_tools = [
        types.Tool(
            name="tool_allowed",
            description="This tool should be allowed",
            inputSchema={"type": "object"},
        ),
        types.Tool(
            name="tool_to_exclude",
            description="This tool should be excluded",
            inputSchema={"type": "object"},
        ),
        types.Tool(
            name="another_tool",
            description="Another allowed tool",
            inputSchema={"type": "object"},
        ),
    ]
    mock_prompts = [
        types.Prompt(name="prompt_allowed", description="Allowed prompt"),
        types.Prompt(name="prompt_to_exclude", description="Excluded prompt"),
    ]
    mock_resources = [
        types.Resource(uri="resource://allowed", name="resource_allowed"),
        types.Resource(uri="resource://to_exclude", name="resource_to_exclude"),
    ]

    # Mock the listing methods to return objects with the expected attributes
    mock_tools_response = MagicMock()
    mock_tools_response.tools = mock_tools
    session.list_tools = AsyncMock(return_value=mock_tools_response)

    mock_prompts_response = MagicMock()
    mock_prompts_response.prompts = mock_prompts
    session.list_prompts = AsyncMock(return_value=mock_prompts_response)

    mock_resources_response = MagicMock()
    mock_resources_response.resources = mock_resources
    session.list_resources = AsyncMock(return_value=mock_resources_response)

    # Mock other methods that might be called during initialization
    # Provide a valid InitializeResult including required fields
    mock_init_result = types.InitializeResult(
        protocolVersion="2024-11-05",  # Match host request
        serverInfo=types.Implementation(name="mock-server", version="0.1.0"),
        capabilities=types.ServerCapabilities(),  # Empty capabilities fine for this test
    )
    session.send_request = AsyncMock(return_value=mock_init_result)
    session.send_notification = AsyncMock()

    return session


@pytest.fixture
@pytest.mark.asyncio
async def initialized_host(mock_exclusion_client_session):
    """Creates and initializes an MCPHost with a mock client session and exclusions."""
    client_id = "test-exclusion-client"
    exclude_list = ["tool_to_exclude", "prompt_to_exclude", "resource_to_exclude"]

    client_config = ClientConfig(
        client_id=client_id,
        server_path=Path("dummy/path/to/server"),  # Path doesn't matter due to patching
        roots=[],
        capabilities=["tools", "prompts", "resources"],
        exclude=exclude_list,
    )
    # Add a name to satisfy HostConfig validation
    host_config = HostConfig(name="TestExclusionHost", clients=[client_config])

    # Patch the context managers used for client creation in MCPHost._initialize_client
    # Patch stdio_client to return mock transport handles
    mock_transport = (AsyncMock(), AsyncMock())  # reader, writer
    stdio_patch = patch(
        "src.host.host.stdio_client",
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_transport), __aexit__=AsyncMock()
        ),
    )

    # Patch ClientSession to return our mock session
    session_patch = patch(
        "src.host.host.ClientSession",
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_exclusion_client_session),
            __aexit__=AsyncMock(),
        ),
    )

    # Start the patches manually
    stdio_patch.start()
    session_patch.start()
    try:
        host = MCPHost(config=host_config)
        await host.initialize()  # This will now use the mocked session
        yield host  # Provide the initialized host to the test
    finally:
        # Ensure patches are stopped
        session_patch.stop()
        stdio_patch.stop()
        # No host.shutdown() needed as we didn't fully start real clients


# --- Exclusion Tests ---


# Since these tests involve initializing a host (even with mocks),
# they lean towards integration testing.
@pytest.mark.integration
class TestComponentExclusion:
    @pytest.mark.asyncio
    async def test_list_tools_exclusion(self, initialized_host: MCPHost):
        """Verify that excluded tools are not listed."""
        listed_tools = initialized_host.tools.list_tools()
        listed_tool_names = {tool["name"] for tool in listed_tools}

        assert "tool_allowed" in listed_tool_names
        assert "another_tool" in listed_tool_names
        assert "tool_to_exclude" not in listed_tool_names
        assert len(listed_tools) == 2

    @pytest.mark.asyncio
    async def test_list_prompts_exclusion(self, initialized_host: MCPHost):
        """Verify that excluded prompts are not listed."""
        listed_prompts = await initialized_host.prompts.list_prompts()
        listed_prompt_names = {prompt.name for prompt in listed_prompts}

        assert "prompt_allowed" in listed_prompt_names
        assert "prompt_to_exclude" not in listed_prompt_names
        assert len(listed_prompts) == 1

    @pytest.mark.asyncio
    async def test_list_resources_exclusion(self, initialized_host: MCPHost):
        """Verify that excluded resources are not listed."""
        listed_resources = await initialized_host.resources.list_resources()
        # Note: We exclude by name, so we check names here
        listed_resource_names = {
            resource.name for resource in listed_resources if resource.name
        }

        assert "resource_allowed" in listed_resource_names
        assert "resource_to_exclude" not in listed_resource_names
        assert len(listed_resources) == 1

    @pytest.mark.asyncio
    async def test_access_excluded_tool(self, initialized_host: MCPHost):
        """Verify attempting to get an excluded tool fails."""
        assert initialized_host.tools.get_tool("tool_to_exclude") is None
        # Also test execution attempt (should fail because tool is not registered)
        with pytest.raises(ValueError, match="Unknown tool: tool_to_exclude"):
            await initialized_host.tools.execute_tool("tool_to_exclude", {})

    @pytest.mark.asyncio
    async def test_access_excluded_prompt(self, initialized_host: MCPHost):
        """Verify attempting to get an excluded prompt fails."""
        client_id = "test-exclusion-client"  # From initialized_host fixture
        prompt = await initialized_host.prompts.get_prompt(
            "prompt_to_exclude", client_id
        )
        assert prompt is None

    @pytest.mark.asyncio
    async def test_access_excluded_resource(self, initialized_host: MCPHost):
        """Verify attempting to get an excluded resource fails."""
        client_id = "test-exclusion-client"  # From initialized_host fixture
        # We excluded by name 'resource_to_exclude', the URI was 'resource://to_exclude'
        resource = await initialized_host.resources.get_resource(
            "resource://to_exclude", client_id
        )
        assert resource is None
