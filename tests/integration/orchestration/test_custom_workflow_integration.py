import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import tempfile

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
            ],
            "llms": [{"name": "test_llm", "provider": "test", "model": "test"}],
            "custom_workflows": [
                {
                    "name": "TestRefactoredWorkflow",
                    "module_path": "tests/fixtures/fixture_custom_workflow.py",
                    "class_name": "TestRefactoredAgentWorkflow",
                    "description": "A workflow for testing the refactored agent.",
                }
            ],
        }
        with open(project_root / "config" / "custom_workflow_project.json", "w") as f:
            json.dump(config_data, f)

        yield project_root


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
@patch("importlib.resources.files")
async def test_custom_workflow_with_refactored_agent_run(mock_files, temp_project_root):
    """
    Tests that a custom workflow can successfully call the refactored run_agent method
    and handle the AgentRunResult.
    """
    # Arrange
    mock_files.return_value.joinpath.return_value.is_dir.return_value = False

    async with Aurite(project_root=temp_project_root) as aurite:
        execution_facade = aurite.execution

        mock_run_agent = patch.object(
            execution_facade,
            "run_agent",
            new_callable=AsyncMock,
            return_value=AgentRunResult(
                status="success",
                final_response=ChatCompletionMessage(
                    role="assistant", content="It is sunny."
                ),
                conversation_history=[],
                error_message=None,
            ),
        ).start()

        # Act
        result = await execution_facade.run_custom_workflow(
            workflow_name="TestRefactoredWorkflow", initial_input="What is the weather?"
        )

        # Assert
        assert result == {"status": "ok", "response": "It is sunny."}
        mock_run_agent.assert_called_once_with(
            agent_name="Weather Agent",
            user_message="What is the weather?",
            session_id=None,
        )
        patch.stopall()
