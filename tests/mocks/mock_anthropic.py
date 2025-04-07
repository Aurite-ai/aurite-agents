"""
Provides mock objects simulating the anthropic client for testing.
"""

from unittest.mock import Mock


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
            mock_tool_use_block = Mock(
                name=f"MockToolUseBlock_{call.get('name', 'unknown')}"
            )
            mock_tool_use_block.type = "tool_use"
            mock_tool_use_block.id = call.get("id", "mock_tool_id")
            mock_tool_use_block.name = call.get("name", "mock_tool_name")
            mock_tool_use_block.input = call.get("input", {})
            mock_response.content.append(mock_tool_use_block)
        mock_response.stop_reason = "tool_use"
    else:
        # Simulate a simple text response
        mock_text_block = Mock(name="MockTextBlock")
        mock_text_block.type = "text"
        mock_text_block.text = response_text
        mock_response.content = [mock_text_block]
        mock_response.stop_reason = stop_reason

    # Configure the mock messages.create method
    mock_messages = Mock(name="MockMessages")
    mock_messages.create.return_value = mock_response
    mock_client_instance.messages = mock_messages

    return mock_client_instance
