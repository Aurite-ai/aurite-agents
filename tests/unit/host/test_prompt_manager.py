"""
Unit tests for the PromptManager class.
"""

import pytest
from unittest.mock import Mock
import mcp.types as types

from src.aurite.host.resources.prompts import PromptManager

# Mark all tests in this file as 'unit' and 'host'
pytestmark = [pytest.mark.unit, pytest.mark.host]


@pytest.mark.anyio
async def test_prompt_manager_initialization(mock_message_router):
    """
    Test that the PromptManager can be initialized successfully.
    """
    # 1. Arrange (Fixture is used)
    # 2. Act
    prompt_manager = PromptManager(message_router=mock_message_router)
    await prompt_manager.initialize()

    # 3. Assert
    assert isinstance(prompt_manager, PromptManager)
    assert prompt_manager._message_router == mock_message_router
    assert prompt_manager._prompts == {}


@pytest.mark.anyio
async def test_register_client_prompts_allowed(
    mock_message_router, mock_filtering_manager
):
    """
    Test that prompts are registered when allowed by the filtering manager.
    """
    # 1. Arrange
    prompt_manager = PromptManager(message_router=mock_message_router)
    mock_filtering_manager.is_registration_allowed.return_value = True

    client_id = "test_client"
    prompt_to_register = types.Prompt(name="test_prompt", description="A test prompt")
    mock_client_config = Mock()

    # 2. Act
    registered_prompts = await prompt_manager.register_client_prompts(
        client_id=client_id,
        prompts=[prompt_to_register],
        client_config=mock_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # 3. Assert
    assert registered_prompts == [prompt_to_register]
    assert client_id in prompt_manager._prompts
    assert "test_prompt" in prompt_manager._prompts[client_id]
    mock_filtering_manager.is_registration_allowed.assert_called_once_with(
        "test_prompt", mock_client_config
    )
    mock_message_router.register_prompt.assert_awaited_once_with(
        prompt_name="test_prompt", client_id=client_id
    )


@pytest.mark.anyio
async def test_register_client_prompts_denied(
    mock_message_router, mock_filtering_manager
):
    """
    Test that prompts are not registered when denied by the filtering manager.
    """
    # 1. Arrange
    prompt_manager = PromptManager(message_router=mock_message_router)
    mock_filtering_manager.is_registration_allowed.return_value = False

    client_id = "test_client"
    prompt_to_register = types.Prompt(name="test_prompt", description="A test prompt")
    mock_client_config = Mock()

    # 2. Act
    registered_prompts = await prompt_manager.register_client_prompts(
        client_id=client_id,
        prompts=[prompt_to_register],
        client_config=mock_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # 3. Assert
    assert registered_prompts == []
    # The current implementation creates an empty dict for the client even if no prompts are registered.
    # This test verifies that behavior.
    assert client_id in prompt_manager._prompts
    assert prompt_manager._prompts[client_id] == {}
    mock_filtering_manager.is_registration_allowed.assert_called_once_with(
        "test_prompt", mock_client_config
    )
    mock_message_router.register_prompt.assert_not_awaited()
