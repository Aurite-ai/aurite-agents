"""
Reusable mocks for the Anthropic client library.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Provides a mock for the Anthropic API client."""
    mock_client = MagicMock()
    # Mock the messages.create method (which is async)
    # Default response: simple text, no tool use, end turn
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Default Mock LLM response")]
    mock_response.stop_reason = "end_turn"
    mock_client.messages = MagicMock()  # Ensure messages attribute exists
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    return mock_client


# Add other Anthropic related mocks here if needed
