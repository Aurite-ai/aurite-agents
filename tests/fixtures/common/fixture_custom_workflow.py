from pathlib import Path

import pytest

from aurite.execution.aurite_engine import AuriteEngine
from aurite.lib.models import AgentRunResult
from aurite.lib.models.config.components import CustomWorkflowConfig


class TestRefactoredAgentWorkflow:
    async def execute_workflow(
        self,
        initial_input: str,
        executor: AuriteEngine,
        session_id: str | None = None,
    ):
        """
        This workflow is for testing purposes. It runs an agent and verifies
        that the result is the expected AgentRunResult object.
        """
        agent_result = await executor.run_agent(
            agent_name="Weather Agent",
            user_message=initial_input,
            session_id=session_id,
        )

        assert isinstance(agent_result, AgentRunResult), f"Expected AgentRunResult, but got {type(agent_result)}"

        if agent_result.status == "success":
            if agent_result.final_response:
                return {"status": "ok", "response": agent_result.final_response.content}
            else:
                return {
                    "status": "error",
                    "message": "Agent succeeded but returned no response.",
                }
        else:
            return {"status": "error", "message": agent_result.error_message}


@pytest.fixture
def example_workflow_config():
    return CustomWorkflowConfig(
        name="test_refactored_agent_workflow",
        module_path=Path("tests/fixtures/fixture_custom_workflow.py"),
        class_name="TestRefactoredAgentWorkflow",
        description="A test workflow that runs an agent and checks the result.",
    )
