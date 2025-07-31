from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from openai.types.chat import ChatCompletionMessage

from aurite.aurite import Aurite
from aurite.components.agents.agent_models import AgentRunResult


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
async def test_aurite_initialization_and_agent_run():
    """
    Tests that the main Aurite class initializes correctly and can run an agent,
    triggering the JIT registration process.
    """
    # Arrange
    # Use the packaged example project for testing
    example_project_path = Path("src/aurite/init_templates").resolve()

    # Mock the dependencies that perform external actions
    with (
        patch("aurite.components.agents.agent.Agent.run_conversation", new_callable=AsyncMock) as mock_run_conv,
        patch("aurite.aurite.MCPHost", autospec=True) as mock_host_class,
    ):
        # We mock the entire MCPHost class as used by the aurite
        # This ensures we are patching the correct instance.
        mock_host_instance = mock_host_class.return_value
        mock_host_instance.register_client = AsyncMock()
        mock_host_instance.unregister_client = AsyncMock()
        # We also need to mock the async context manager methods
        mock_host_instance.__aenter__ = AsyncMock(return_value=mock_host_instance)
        mock_host_instance.__aexit__ = AsyncMock()

        mock_run_conv.return_value = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(role="assistant", content="Success"),
            conversation_history=[],
            error_message=None,
        )

        # Act
        # Initialize Aurite with the path to the example project
        async with Aurite(start_dir=example_project_path) as aurite:
            # Use an agent defined in the example project
            result = await aurite.run_agent("Structured Output Weather Agent", "Hello")

            # Assert
            assert result.status == "success"
            assert result.final_response is not None
            assert result.final_response.content == "Success"

            # Verify the agent's run_conversation was called
            mock_run_conv.assert_awaited_once()

            # Verify that the host attempted to register the agent's required server
            # We check the call args to see if the 'weather_server' was passed.
            mock_host_instance.register_client.assert_awaited()
            registered_server_config = mock_host_instance.register_client.call_args[0][0]
            assert registered_server_config.name == "weather_server"
