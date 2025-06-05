"""
Unit tests for the PromptManager.
"""

import pytest
from unittest.mock import MagicMock, call

# Import the class to test and dependencies/models
from aurite.host.resources.prompts import PromptManager

# Import foundation classes for type hinting shared fixtures
# Import models
from aurite.config.config_models import ClientConfig  # Updated import path

# Import mcp types
import mcp.types as types

# Mark tests as host_unit and async
pytestmark = [pytest.mark.host_unit, pytest.mark.anyio]


# --- Fixtures ---

# Removed local mock_message_router and mock_filtering_manager fixtures
# They are now imported from tests.fixtures.host_fixtures


@pytest.fixture
def prompt_manager(mock_message_router: MagicMock) -> PromptManager:
    """Fixture to provide a clean PromptManager instance with a mocked router."""
    return PromptManager(message_router=mock_message_router)


@pytest.fixture
def sample_client_config() -> ClientConfig:
    """Fixture for a sample ClientConfig."""
    return ClientConfig(
        client_id="client_A",
        server_path="path/to/server_a.py",
        capabilities=["prompts"],
        roots=[],
    )


# --- Test Cases ---


async def test_prompt_manager_init(
    prompt_manager: PromptManager, mock_message_router: MagicMock
):
    """Test initial state of the PromptManager."""
    assert prompt_manager._prompts == {}
    assert prompt_manager._message_router == mock_message_router


async def test_register_client_prompts_success(
    prompt_manager: PromptManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test registering prompts successfully for a client."""
    client_id = sample_client_config.client_id
    prompt1 = types.Prompt(name="prompt1", description="Desc 1")
    prompt2 = types.Prompt(name="prompt2", description="Desc 2", arguments=[])
    prompts_to_register = [prompt1, prompt2]

    # Ensure filtering allows registration
    mock_filtering_manager.is_registration_allowed.return_value = True

    registered = await prompt_manager.register_client_prompts(
        client_id=client_id,
        prompts=prompts_to_register,
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    assert len(registered) == 2
    assert prompt1 in registered
    assert prompt2 in registered

    # Check internal state
    assert client_id in prompt_manager._prompts
    assert prompt_manager._prompts[client_id]["prompt1"] == prompt1
    assert prompt_manager._prompts[client_id]["prompt2"] == prompt2

    # Check calls to dependencies
    mock_filtering_manager.is_registration_allowed.assert_has_calls(
        [
            call("prompt1", sample_client_config),
            call("prompt2", sample_client_config),
        ],
        any_order=True,
    )
    mock_message_router.register_prompt.assert_has_calls(
        [
            call(prompt_name="prompt1", client_id=client_id),
            call(prompt_name="prompt2", client_id=client_id),
        ],
        any_order=True,
    )


async def test_register_client_prompts_filtered(
    prompt_manager: PromptManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test that prompts are filtered by FilteringManager during registration."""
    client_id = sample_client_config.client_id
    prompt1 = types.Prompt(name="allowed_prompt")
    prompt2 = types.Prompt(name="excluded_prompt")  # This one will be filtered
    prompts_to_register = [prompt1, prompt2]

    # Configure mock FilteringManager to exclude prompt2
    def filter_side_effect(name, config):
        return name != "excluded_prompt"

    mock_filtering_manager.is_registration_allowed.side_effect = filter_side_effect

    registered = await prompt_manager.register_client_prompts(
        client_id=client_id,
        prompts=prompts_to_register,
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # Assert only allowed prompt was registered and returned
    assert len(registered) == 1
    assert prompt1 in registered
    assert prompt2 not in registered

    # Check internal state
    assert client_id in prompt_manager._prompts
    assert "allowed_prompt" in prompt_manager._prompts[client_id]
    assert "excluded_prompt" not in prompt_manager._prompts[client_id]

    # Check calls to dependencies
    mock_filtering_manager.is_registration_allowed.assert_has_calls(
        [
            call("allowed_prompt", sample_client_config),
            call("excluded_prompt", sample_client_config),
        ],
        any_order=True,
    )
    # Ensure router was only called for the allowed prompt
    mock_message_router.register_prompt.assert_called_once_with(
        prompt_name="allowed_prompt", client_id=client_id
    )


async def test_register_client_prompts_empty(
    prompt_manager: PromptManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test registering an empty list of prompts."""
    client_id = sample_client_config.client_id
    registered = await prompt_manager.register_client_prompts(
        client_id=client_id,
        prompts=[],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    assert registered == []
    # Check that the client ID *was* added, but maps to an empty dict
    assert client_id in prompt_manager._prompts
    assert prompt_manager._prompts[client_id] == {}
    mock_filtering_manager.is_registration_allowed.assert_not_called()
    mock_message_router.register_prompt.assert_not_called()


# --- Tests for get_prompt ---


async def test_get_prompt_success(
    prompt_manager: PromptManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test retrieving an existing prompt successfully."""
    client_id = sample_client_config.client_id
    prompt1 = types.Prompt(name="prompt1", description="Desc 1")
    await prompt_manager.register_client_prompts(
        client_id=client_id,
        prompts=[prompt1],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    retrieved_prompt = await prompt_manager.get_prompt(
        client_id=client_id, name="prompt1"
    )  # await + name
    assert retrieved_prompt == prompt1


async def test_get_prompt_client_not_found(prompt_manager: PromptManager):
    """Test retrieving a prompt from a non-existent client."""
    retrieved_prompt = await prompt_manager.get_prompt(
        client_id="non_existent_client", name="prompt1"
    )  # await + name
    assert retrieved_prompt is None


async def test_get_prompt_prompt_not_found(
    prompt_manager: PromptManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test retrieving a non-existent prompt from an existing client."""
    client_id = sample_client_config.client_id
    prompt1 = types.Prompt(name="prompt1", description="Desc 1")
    await prompt_manager.register_client_prompts(
        client_id=client_id,
        prompts=[prompt1],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    retrieved_prompt = await prompt_manager.get_prompt(
        client_id=client_id, name="non_existent_prompt"
    )  # await + name
    assert retrieved_prompt is None


# --- Tests for list_prompts ---


async def test_list_prompts_empty(prompt_manager: PromptManager):
    """Test listing prompts when none are registered."""
    assert await prompt_manager.list_prompts() == []  # await + expect list


async def test_list_prompts_single_client(
    prompt_manager: PromptManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test listing prompts for a single registered client."""
    client_id = sample_client_config.client_id
    prompt1 = types.Prompt(name="prompt1")
    prompt2 = types.Prompt(name="prompt2")
    await prompt_manager.register_client_prompts(
        client_id=client_id,
        prompts=[prompt1, prompt2],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    expected_prompts = [prompt1, prompt2]  # Expect flat list
    listed_prompts = await prompt_manager.list_prompts()  # await
    # Sort for comparison stability as order isn't guaranteed
    listed_prompts.sort(key=lambda p: p.name)
    assert listed_prompts == expected_prompts


async def test_list_prompts_multiple_clients(
    prompt_manager: PromptManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,  # Use this as a base for client A
):
    """Test listing prompts for multiple registered clients."""
    client_id_a = sample_client_config.client_id
    prompt_a1 = types.Prompt(name="prompt_a1")
    await prompt_manager.register_client_prompts(
        client_id=client_id_a,
        prompts=[prompt_a1],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    client_id_b = "client_B"
    client_config_b = ClientConfig(
        client_id=client_id_b, server_path="path/b", capabilities=["prompts"], roots=[]
    )
    prompt_b1 = types.Prompt(name="prompt_b1")
    prompt_b2 = types.Prompt(name="prompt_b2")
    # Need to reset the mock for the second registration call if side_effect was used
    mock_filtering_manager.is_registration_allowed.side_effect = None
    mock_filtering_manager.is_registration_allowed.return_value = True
    await prompt_manager.register_client_prompts(
        client_id=client_id_b,
        prompts=[prompt_b1, prompt_b2],
        client_config=client_config_b,
        filtering_manager=mock_filtering_manager,
    )

    expected_prompts = [prompt_a1, prompt_b1, prompt_b2]  # Expect flat list
    listed_prompts = await prompt_manager.list_prompts()  # await
    # Sort for comparison stability
    listed_prompts.sort(key=lambda p: p.name)
    assert listed_prompts == expected_prompts


# --- Tests for get_clients_for_prompt ---


async def test_get_clients_for_prompt_found(
    prompt_manager: PromptManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,  # Client A
):
    """Test finding clients that provide a specific prompt."""
    client_id_a = sample_client_config.client_id
    client_id_b = "client_B"
    client_config_b = ClientConfig(
        client_id=client_id_b, server_path="path/b", capabilities=["prompts"], roots=[]
    )
    prompt_common = types.Prompt(name="common_prompt")
    prompt_a_only = types.Prompt(name="prompt_a_only")
    prompt_b_only = types.Prompt(name="prompt_b_only")

    # Register for Client A
    await prompt_manager.register_client_prompts(
        client_id=client_id_a,
        prompts=[prompt_common, prompt_a_only],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )
    # Register for Client B
    mock_filtering_manager.is_registration_allowed.side_effect = None
    mock_filtering_manager.is_registration_allowed.return_value = True
    await prompt_manager.register_client_prompts(
        client_id=client_id_b,
        prompts=[prompt_common, prompt_b_only],
        client_config=client_config_b,
        filtering_manager=mock_filtering_manager,
    )

    clients_common = prompt_manager.get_clients_for_prompt("common_prompt")
    clients_a = prompt_manager.get_clients_for_prompt("prompt_a_only")
    clients_b = prompt_manager.get_clients_for_prompt("prompt_b_only")

    assert sorted(clients_common) == sorted([client_id_a, client_id_b])
    assert clients_a == [client_id_a]
    assert clients_b == [client_id_b]


async def test_get_clients_for_prompt_not_found(prompt_manager: PromptManager):
    """Test finding clients for a prompt that no client provides."""
    clients = prompt_manager.get_clients_for_prompt("non_existent_prompt")
    assert clients == []


# --- Test for shutdown ---


async def test_shutdown(
    prompt_manager: PromptManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test the shutdown process."""
    client_id = sample_client_config.client_id
    prompt1 = types.Prompt(name="prompt1")
    await prompt_manager.register_client_prompts(
        client_id=client_id,
        prompts=[prompt1],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    assert client_id in prompt_manager._prompts

    await prompt_manager.shutdown()

    # Assert internal state is cleared
    assert prompt_manager._prompts == {}
    # No need to assert router calls, as shutdown doesn't interact with it


async def test_shutdown_multiple_clients(
    prompt_manager: PromptManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,  # Client A
):
    """Test shutdown with multiple clients registered."""
    client_id_a = sample_client_config.client_id
    client_id_b = "client_B"
    client_config_b = ClientConfig(
        client_id=client_id_b, server_path="path/b", capabilities=["prompts"], roots=[]
    )

    # Register Client A
    await prompt_manager.register_client_prompts(
        client_id=client_id_a,
        prompts=[types.Prompt(name="p_a")],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )
    # Register Client B
    mock_filtering_manager.is_registration_allowed.side_effect = None
    mock_filtering_manager.is_registration_allowed.return_value = True
    await prompt_manager.register_client_prompts(
        client_id=client_id_b,
        prompts=[types.Prompt(name="p_b")],
        client_config=client_config_b,
        filtering_manager=mock_filtering_manager,
    )

    assert client_id_a in prompt_manager._prompts
    assert client_id_b in prompt_manager._prompts

    await prompt_manager.shutdown()

    assert prompt_manager._prompts == {}
    # No need to assert router calls, as shutdown doesn't interact with it


async def test_unregister_client_prompts(
    prompt_manager: PromptManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test unregistering prompts for a specific client."""
    client_id_a = sample_client_config.client_id
    client_id_b = "client_B"
    client_config_b = ClientConfig(
        client_id=client_id_b, server_path="path/b", capabilities=["prompts"], roots=[]
    )

    prompt_a1 = types.Prompt(name="prompt_a1")
    prompt_b1 = types.Prompt(name="prompt_b1")

    # Register prompts for client A
    await prompt_manager.register_client_prompts(
        client_id=client_id_a,
        prompts=[prompt_a1],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )
    # Register prompts for client B
    mock_filtering_manager.is_registration_allowed.side_effect = (
        None  # Reset for next call
    )
    mock_filtering_manager.is_registration_allowed.return_value = True
    await prompt_manager.register_client_prompts(
        client_id=client_id_b,
        prompts=[prompt_b1],
        client_config=client_config_b,
        filtering_manager=mock_filtering_manager,
    )

    assert client_id_a in prompt_manager._prompts
    assert client_id_b in prompt_manager._prompts

    # Unregister prompts for client A
    await prompt_manager.unregister_client_prompts(client_id_a)

    assert client_id_a not in prompt_manager._prompts
    assert client_id_b in prompt_manager._prompts  # Client B should remain
    assert "prompt_a1" not in prompt_manager._prompts.get(client_id_b, {})

    # Unregister prompts for a non-existent client (should not error)
    await prompt_manager.unregister_client_prompts("non_existent_client")
    assert client_id_b in prompt_manager._prompts  # Client B should still remain
