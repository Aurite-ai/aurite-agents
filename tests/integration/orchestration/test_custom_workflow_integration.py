from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from openai.types.chat import ChatCompletionMessage

from aurite.aurite import Aurite
from aurite.lib.models.api.responses import AgentRunResult


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
async def test_custom_workflow_with_refactored_agent_run():
    """
    Tests that a custom workflow can successfully call the refactored run_agent method
    and handle the AgentRunResult, using the packaged example project.
    """
    # Arrange
    example_project_path = Path("src/aurite/lib/init_templates").resolve()

    async with Aurite(start_dir=example_project_path) as aurite:
        execution_facade = aurite.kernel.execution

        # Mock the underlying run_agent call to isolate the workflow logic
        mock_run_agent = patch.object(
            execution_facade,
            "run_agent",
            new_callable=AsyncMock,
            return_value=AgentRunResult(
                status="success",
                final_response=ChatCompletionMessage(role="assistant", content="It is sunny."),
                conversation_history=[],
                error_message=None,
            ),
        ).start()

        # Act
        # Use the custom workflow from the example project
        result = await execution_facade.run_custom_workflow(
            workflow_name="Example Custom Workflow",
            initial_input={"city": "New York"},
        )

        # Assert
        # The example workflow is designed to return a dict
        assert result == {"status": "ok", "response": "It is sunny."}
        # The example workflow calls the "Weather Agent"
        mock_run_agent.assert_called_once_with(
            agent_name="Weather Agent",
            user_message="What is the weather in New York?",
            session_id=None,
        )
        patch.stopall()
