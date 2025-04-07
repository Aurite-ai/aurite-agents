"""
Provides mock objects simulating the anthropic client for testing.
"""

from unittest.mock import Mock
from anthropic.types import ToolUseBlock, TextBlock  # Corrected import


def get_mock_anthropic_client(
    response_text: str = "Mock LLM response",
    stop_reason: str = "end_turn",
    tool_calls: list | None = None,
) -> Mock:
    """
    Creates and returns a mock Anthropic client instance.

    Allows specifying the response content, stop reason, and potential tool calls
    for the mock `messages.create` method.

    Args:
        response_text: The text content for the default mock response block.
        stop_reason: The stop reason for the default mock response.
        tool_calls: A list of dictionaries simulating ToolUseBlocks if the
                    response should request tool calls. Each dict should have
                    'id', 'name', 'input'.

    Returns:
        A unittest.mock.Mock instance simulating anthropic.Anthropic.
    """
    mock_client_instance = Mock(name="MockAnthropicClient")
    mock_response = Mock(name="MockAnthropicResponse")

    if tool_calls:
        # Simulate a response requesting tool calls
        mock_response.content = []
        for call in tool_calls:
            # Create actual ToolUseBlock instances
            tool_use_block = ToolUseBlock(
                type="tool_use",
                id=call.get("id", "mock_tool_id"),  # Use provided or default ID
                name=call.get("name", "mock_tool_name"),  # Use provided or default name
                input=call.get("input", {}),  # Use provided or default input
            )
            mock_response.content.append(tool_use_block)
        mock_response.stop_reason = "tool_use"
    else:
        # Simulate a simple text response
        # Create an actual TextBlock content block
        text_block = TextBlock(type="text", text=response_text)  # Use TextBlock
        mock_response.content = [text_block]
        mock_response.stop_reason = stop_reason

    # Configure the mock messages.create method
    mock_messages = Mock(name="MockMessages")
    mock_messages.create.return_value = mock_response
    mock_client_instance.messages = mock_messages

    return mock_client_instance
