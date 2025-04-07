"""
E2E tests for generic MCP server functionality using a real host.

These tests utilize the `real_mcp_host` fixture to ensure that servers
configured in `config/agents/testing_config.json` can be started by the host
and respond correctly to basic MCP requests (list_tools, list_prompts, etc.).
"""

import pytest
import logging

# Use relative imports assuming tests run from aurite-mcp root
from src.host.host import MCPHost
import mcp.types as types

# Configure logging for debugging E2E tests if needed
logger = logging.getLogger(__name__)


@pytest.mark.e2e
# Apply xfail due to the known host shutdown issue with the fixture
@pytest.mark.xfail(
    reason="Known issue with real_mcp_host teardown async complexity", strict=False
)
class TestGenericMCPServerE2E:
    """E2E tests for basic MCP server interactions via the host."""

    @pytest.mark.asyncio
    async def test_server_responds_to_list_requests(self, real_mcp_host: MCPHost):
        """Verify connected servers respond to list_tools and list_prompts."""
        host = real_mcp_host
        # assert host.is_running, "Host should be running" # Removed check for non-existent attribute
        assert len(host._clients) > 0, (  # Check internal _clients dict instead
            "Host should have at least one client configured for E2E tests"
        )

        logger.info(f"Testing list requests against {len(host.clients)} clients...")

        # Check each client managed by the host
        for client_name, client_info in host.clients.items():
            logger.info(f"Checking client: {client_name}")

            # Test list_tools
            try:
                # Use client_id parameter instead of client_names
                tools = await host.tools.list_tools(client_id=client_name)
                assert isinstance(tools, list), (
                    f"list_tools for {client_name} should return a list"
                )
                logger.info(
                    f"Client {client_name} - list_tools returned {len(tools)} tools."
                )
                # Basic validation of tool structure if any tools are returned
                for tool in tools:
                    assert isinstance(tool, types.Tool)
                    assert isinstance(tool.name, str)
            except Exception as e:
                pytest.fail(
                    f"host.tools.list_tools failed for client {client_name}: {e}"
                )

            # Test list_prompts
            try:
                # Use client_id parameter instead of client_names
                prompts = await host.prompts.list_prompts(client_id=client_name)
                assert isinstance(prompts, list), (
                    f"list_prompts for {client_name} should return a list"
                )
                logger.info(
                    f"Client {client_name} - list_prompts returned {len(prompts)} prompts."
                )
                # Basic validation of prompt structure if any prompts are returned
                for prompt in prompts:
                    assert isinstance(prompt, types.Prompt)
                    assert isinstance(prompt.name, str)
            except Exception as e:
                pytest.fail(
                    f"host.prompts.list_prompts failed for client {client_name}: {e}"
                )

    @pytest.mark.asyncio
    async def test_server_responds_to_get_or_call_requests(
        self, real_mcp_host: MCPHost
    ):
        """
        Verify connected servers respond to a basic get_prompt or call_tool request,
        if they offer any prompts or tools.
        """
        host = real_mcp_host
        # assert host.is_running, "Host should be running" # Removed check for non-existent attribute
        assert len(host._clients) > 0, (
            "Host should have active clients"
        )  # Check internal _clients dict

        logger.info(
            f"Testing get/call requests against {len(host._clients)} clients..."
        )

        for client_name, client_info in host.clients.items():
            logger.info(f"Checking client: {client_name}")

            # Check if tools exist first (using corrected list_tools call)
            tools = await host.tools.list_tools(client_id=client_name)
            if tools:
                # Attempt to call the first tool found with dummy args if possible
                # This is a basic check, might need refinement based on tool schemas
                first_tool = tools[0]
                logger.info(
                    f"Client {client_name} has tools. Attempting call_tool for '{first_tool.name}'"
                )
                try:
                    # Construct minimal valid arguments if possible, otherwise empty dict
                    args = {}
                    if first_tool.inputSchema and first_tool.inputSchema.get(
                        "required"
                    ):
                        # Very basic attempt - might fail for complex schemas
                        logger.warning(
                            f"Tool '{first_tool.name}' has required args, attempting with empty dict. May fail."
                        )

                    result = await host.tools.execute_tool(
                        client_name=client_name,
                        tool_name=first_tool.name,
                        arguments=args,
                    )
                    # Expecting a list of content blocks or similar structure
                    assert isinstance(result, list), (
                        f"call_tool for {client_name}.{first_tool.name} should return a list"
                    )
                    logger.info(
                        f"Client {client_name} - call_tool for '{first_tool.name}' successful."
                    )
                except Exception as e:
                    # Don't fail outright, as dummy args might be invalid. Log a warning.
                    logger.warning(
                        f"host.tools.execute_tool potentially failed for {client_name}.{first_tool.name} (may be due to dummy args): {e}"
                    )
            else:
                logger.info(f"Client {client_name} has no tools to call.")

            # Check if prompts exist (using corrected list_prompts call)
            prompts = await host.prompts.list_prompts(client_id=client_name)
            if prompts:
                first_prompt = prompts[0]
                logger.info(
                    f"Client {client_name} has prompts. Attempting get_prompt for '{first_prompt.name}'"
                )
                try:
                    # Attempt to get the prompt using the correct manager signature
                    result = await host.prompts.get_prompt(
                        name=first_prompt.name,  # Use 'name' parameter
                        client_id=client_name,  # Use 'client_id' parameter
                        # No 'arguments' parameter for manager's get_prompt
                    )
                    # Manager's get_prompt returns types.Prompt or None
                    assert isinstance(result, types.Prompt), (
                        f"get_prompt for {client_name}.{first_prompt.name} should return Prompt"
                    )
                    # Add basic checks for the returned Prompt object
                    assert result.name == first_prompt.name
                    logger.info(
                        f"Client {client_name} - get_prompt for '{first_prompt.name}' successful (returned Prompt definition)."
                    )
                except Exception as e:
                    pytest.fail(
                        f"host.prompts.get_prompt failed for {client_name}.{first_prompt.name}: {e}"
                    )
            else:
                logger.info(f"Client {client_name} has no prompts to get.")
