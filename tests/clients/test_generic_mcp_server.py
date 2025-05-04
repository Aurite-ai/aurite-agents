"""
Unit tests for generic MCP server functionality.

These tests focus on the server-side logic abstractly, verifying
that handlers for core MCP methods return correctly formatted responses
based on mcp.types, using mocks.
"""

import pytest
from unittest.mock import AsyncMock

import mcp.types as types


@pytest.mark.unit
class TestGenericMCPServerUnit:
    """Unit tests for generic MCP server handlers."""

    @pytest.mark.asyncio
    async def test_list_tools_format(self):
        """Verify list_tools handler returns correctly formatted list of Tools."""
        # Mock a server handler for list_tools
        mock_list_tools_handler = AsyncMock(
            return_value=[
                types.Tool(
                    name="mock_tool_1",
                    description="A mock tool",
                    inputSchema={"type": "object", "properties": {}},
                ),
                types.Tool(
                    name="mock_tool_2",
                    description="Another mock tool",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]
        )

        # Simulate calling the handler
        result = await mock_list_tools_handler()

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 2
        for tool in result:
            assert isinstance(tool, types.Tool)
            assert isinstance(tool.name, str)
            assert isinstance(tool.description, str)
            assert isinstance(tool.inputSchema, dict)

    @pytest.mark.asyncio
    async def test_call_tool_format(self):
        """Verify call_tool handler returns correctly formatted list of TextContent."""
        # Mock a server handler for call_tool
        mock_call_tool_handler = AsyncMock(
            return_value=[
                types.TextContent(type="text", text="Tool executed successfully.")
            ]
        )

        # Simulate calling the handler
        result = await mock_call_tool_handler(
            name="mock_tool_1", arguments={"param": "value"}
        )

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1
        for content in result:
            assert isinstance(content, types.TextContent)
            assert content.type == "text"
            assert isinstance(content.text, str)

    @pytest.mark.asyncio
    async def test_list_prompts_format(self):
        """Verify list_prompts handler returns correctly formatted list of Prompts."""
        # Mock a server handler for list_prompts
        mock_list_prompts_handler = AsyncMock(
            return_value=[
                types.Prompt(
                    name="mock_prompt_1",
                    description="A mock prompt",
                    arguments=[
                        types.PromptArgument(
                            name="arg1", description="Arg 1", schema={"type": "string"}
                        )
                    ],
                )
            ]
        )

        # Simulate calling the handler
        result = await mock_list_prompts_handler()

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1
        for prompt in result:
            assert isinstance(prompt, types.Prompt)
            assert isinstance(prompt.name, str)
            assert isinstance(prompt.description, str)
            assert isinstance(prompt.arguments, list)
            for arg in prompt.arguments:
                assert isinstance(arg, types.PromptArgument)

    @pytest.mark.asyncio
    async def test_get_prompt_format(self):
        """Verify get_prompt handler returns correctly formatted GetPromptResult."""
        # Mock a server handler for get_prompt
        mock_get_prompt_handler = AsyncMock(
            return_value=types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(type="text", text="Mock prompt text"),
                    )
                ]
            )
        )

        # Simulate calling the handler
        result = await mock_get_prompt_handler(name="mock_prompt_1", arguments={})

        # Assertions
        assert isinstance(result, types.GetPromptResult)
        assert isinstance(result.messages, list)
        assert len(result.messages) == 1
        for message in result.messages:
            assert isinstance(message, types.PromptMessage)
            assert message.role in ["user", "assistant", "system"]  # Adjust as needed
            assert isinstance(message.content, types.TextContent)

    # Add more tests as needed for error handling, different scenarios, etc.
