from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from openai.types.chat import ChatCompletionMessage

from aurite.components.agents.agent_models import AgentRunResult
from aurite.host_manager import Aurite


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
async def test_linear_workflow_success():
    """
    Tests a successful execution of a linear workflow using the packaged example project.
    """
    # Arrange
    example_project_path = Path("src/aurite/init_templates").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        execution_facade = aurite.kernel.execution

        # Mock the facade's run_agent method to simulate successful agent runs
        mock_run_agent = patch.object(execution_facade, "run_agent", new_callable=AsyncMock).start()

        # Define the mock return values for each agent in the workflow
        weather_agent_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(
                role="assistant", content='{"temperature": 72, "conditions": "Sunny"}'
            ),
            conversation_history=[],
            error_message=None,
        )
        planning_agent_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(role="assistant", content="It's a beautiful sunny day at 72 degrees!"),
            conversation_history=[],
            error_message=None,
        )
        mock_run_agent.side_effect = [weather_agent_result, planning_agent_result]

        # Act
        result = await execution_facade.run_linear_workflow(
            workflow_name="test_weather_workflow",
            initial_input="What's the weather in Boston?",
        )

        # Assert
        assert result.status == "completed"
        assert result.error is None
        assert len(result.step_results) == 2
        assert result.final_output == "It's a beautiful sunny day at 72 degrees!"

        # Check that the correct agents were called in order
        mock_run_agent.assert_any_call(
            agent_name="Weather Agent",
            user_message="What's the weather in Boston?",
        )
        mock_run_agent.assert_any_call(
            agent_name="Weather Planning Workflow Step 2",
            user_message='{"temperature": 72, "conditions": "Sunny"}',
        )
        patch.stopall()


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
async def test_linear_workflow_agent_failure():
    """
    Tests that the workflow correctly handles a failure from one of its agents.
    """
    # Arrange
    example_project_path = Path("src/aurite/init_templates").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        execution_facade = aurite.kernel.execution

        # Mock the facade's run_agent to simulate a failure on the first call
        mock_run_agent = patch.object(
            execution_facade,
            "run_agent",
            new_callable=AsyncMock,
            return_value=AgentRunResult(
                status="error",
                final_response=None,
                conversation_history=[],
                error_message="API key is invalid",
            ),
        ).start()

        # Act
        result = await execution_facade.run_linear_workflow(
            workflow_name="test_weather_workflow",
            initial_input="What's the weather in Boston?",
        )

        # Assert
        assert result.status == "failed"
        assert result.error is not None
        assert "Agent 'Weather Agent' failed to execute successfully" in result.error
        mock_run_agent.assert_called_once_with(
            agent_name="Weather Agent",
            user_message="What's the weather in Boston?",
        )
        patch.stopall()
