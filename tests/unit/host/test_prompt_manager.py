"""
Unit tests for the PromptManager class.
"""

import mcp.types as types
import pytest

from src.aurite.host.resources.prompts import PromptManager

# Mark all tests in this file as 'unit' and 'host'
pytestmark = [pytest.mark.unit, pytest.mark.host]


@pytest.mark.anyio
async def test_prompt_manager_initialization(mock_message_router, mock_client_session_group):
    """
    Test that the PromptManager can be initialized successfully and registers prompts.
    """
    # 1. Arrange
    prompt = types.Prompt(name="test_prompt", description="A test prompt")
    prompt.client_id = "test_client"
    mock_client_session_group.prompts = {"test_prompt": prompt}

    # 2. Act
    prompt_manager = PromptManager(message_router=mock_message_router, session_group=mock_client_session_group)
    await prompt_manager.initialize()

    # 3. Assert
    assert isinstance(prompt_manager, PromptManager)
    mock_message_router.register_prompt.assert_awaited_once_with(prompt_name="test_prompt", client_id="test_client")


@pytest.mark.anyio
async def test_get_prompt(mock_message_router, mock_client_session_group):
    """
    Test that get_prompt retrieves a prompt from the session group.
    """
    # 1. Arrange
    prompt = types.Prompt(name="test_prompt", description="A test prompt")
    mock_client_session_group.prompts = {"test_prompt": prompt}
    prompt_manager = PromptManager(message_router=mock_message_router, session_group=mock_client_session_group)

    # 2. Act
    retrieved_prompt = await prompt_manager.get_prompt("test_prompt")

    # 3. Assert
    assert retrieved_prompt == prompt


@pytest.mark.anyio
async def test_list_prompts(mock_message_router, mock_client_session_group):
    """
    Test that list_prompts returns all prompts from the session group.
    """
    # 1. Arrange
    prompt1 = types.Prompt(name="prompt1", description="A test prompt")
    prompt2 = types.Prompt(name="prompt2", description="Another test prompt")
    mock_client_session_group.prompts = {"prompt1": prompt1, "prompt2": prompt2}
    prompt_manager = PromptManager(message_router=mock_message_router, session_group=mock_client_session_group)

    # 2. Act
    all_prompts = await prompt_manager.list_prompts()

    # 3. Assert
    assert len(all_prompts) == 2
    assert prompt1 in all_prompts
    assert prompt2 in all_prompts
