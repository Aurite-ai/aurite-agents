import pytest
import json
from unittest.mock import AsyncMock, patch
from pathlib import Path
import tempfile
import os

from aurite.host_manager import Aurite
from aurite.components.agents.agent_models import AgentRunResult
from openai.types.chat import ChatCompletionMessage


@pytest.fixture
def temp_project_root():
    """Creates a temporary directory for a test project."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        (project_root / "config").mkdir()

        # Create a monolithic config file for the workflow test
        config_data = {
            "agents": [
                {"name": "Weather Agent", "llm_config_id": "test_llm"},
                {"name": "Weather Reporter", "llm_config_id": "test_llm"},
            ],
            "llms": [{"name": "test_llm", "provider": "test", "model": "test"}],
            "simple_workflows": [
                {
                    "name": "Weather Planning Workflow",
                    "steps": ["Weather Agent", "Weather Reporter"],
                }
            ],
        }
        with open(project_root / "config" / "workflow_project.json", "w") as f:
            json.dump(config_data, f)

        # Create the anchor file
        (project_root / ".aurite").touch()

        # Yield and change back directory
        original_cwd = Path.cwd()
        os.chdir(project_root)
        yield project_root
        os.chdir(original_cwd)


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
@patch("importlib.resources.files")
async def test_simple_workflow_success(mock_files, temp_project_root):
    """
    Tests a successful execution of a simple workflow where each agent step succeeds.
    """
    # Arrange
    mock_files.return_value.joinpath.return_value.is_dir.return_value = False

    async with Aurite() as aurite:
        execution_facade = aurite.execution

        # Mock the facade's run_agent method to simulate successful agent runs
        mock_run_agent = patch.object(
            execution_facade, "run_agent", new_callable=AsyncMock
        ).start()

        weather_agent_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(
                role="assistant", content='{"temperature": 72, "conditions": "Sunny"}'
            ),
            conversation_history=[],
            error_message=None,
        )
        weather_reporter_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(
                role="assistant", content="It's a beautiful sunny day at 72 degrees!"
            ),
            conversation_history=[],
            error_message=None,
        )
        mock_run_agent.side_effect = [weather_agent_result, weather_reporter_result]

        # Act
        result = await execution_facade.run_simple_workflow(
            workflow_name="Weather Planning Workflow",
            initial_input="What's the weather in Boston?",
        )

        # Assert
        assert result.status == "completed"
        assert result.error is None
        assert len(result.step_results) == 2
        assert result.final_output == "It's a beautiful sunny day at 72 degrees!"
        mock_run_agent.assert_any_call(
            agent_name="Weather Agent", user_message="What's the weather in Boston?"
        )
        mock_run_agent.assert_any_call(
            agent_name="Weather Reporter",
            user_message='{"temperature": 72, "conditions": "Sunny"}',
        )
        patch.stopall()


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
@patch("importlib.resources.files")
async def test_simple_workflow_agent_failure(mock_files, temp_project_root):
    """
    Tests that the workflow correctly handles a failure from one of its agents
    and terminates gracefully.
    """
    # Arrange
    mock_files.return_value.joinpath.return_value.is_dir.return_value = False

    async with Aurite() as aurite:
        execution_facade = aurite.execution

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
        result = await execution_facade.run_simple_workflow(
            workflow_name="Weather Planning Workflow",
            initial_input="What's the weather in Boston?",
        )

        # Assert
        assert result.status == "failed"
        assert result.error is not None
        assert "Agent 'Weather Agent' failed to execute successfully" in result.error
        mock_run_agent.assert_called_once_with(
            agent_name="Weather Agent", user_message="What's the weather in Boston?"
        )
        patch.stopall()
