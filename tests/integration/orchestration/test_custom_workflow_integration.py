import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock

from aurite.config.config_models import ProjectConfig, HostConfig
from aurite.host.host import MCPHost
from aurite.execution.facade import ExecutionFacade
from aurite.components.agents.agent_models import AgentRunResult
from openai.types.chat import ChatCompletionMessage


@pytest.fixture
def project_config() -> ProjectConfig:
    """Loads the project configuration from the test fixture."""
    with open("tests/fixtures/project_fixture.json", "r") as f:
        config_data = json.load(f)

    # Add the test custom workflow to the project config
    test_workflow_config = {
        "name": "TestRefactoredWorkflow",
        "module_path": "tests/fixtures/custom_workflows/test_refactored_agent_workflow.py",
        "class_name": "TestRefactoredAgentWorkflow",
        "description": "A workflow for testing the refactored agent.",
    }
    config_data["custom_workflows"].append(test_workflow_config)

    return ProjectConfig(**config_data)


@pytest.fixture
def mcp_host(project_config: ProjectConfig) -> MCPHost:
    """Creates a mockable MCPHost instance."""
    host_config = HostConfig(
        name=project_config.name,
        description=project_config.description,
        mcp_servers=project_config.mcp_servers,
    )
    return MCPHost(host_config)


@pytest.fixture
def execution_facade(
    mcp_host: MCPHost, project_config: ProjectConfig
) -> ExecutionFacade:
    """Creates an ExecutionFacade instance with a real project config but a mockable host."""
    # Resolve the module_path to an absolute path before creating the facade
    for wf in project_config.custom_workflows:
        if isinstance(wf.module_path, str):
            wf.module_path = Path(wf.module_path).resolve()

    return ExecutionFacade(host_instance=mcp_host, current_project=project_config)


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
async def test_custom_workflow_with_refactored_agent_run(
    execution_facade: ExecutionFacade, mocker
):
    """
    Tests that a custom workflow can successfully call the refactored run_agent method
    and handle the AgentRunResult.
    """
    # Arrange
    mock_run_agent = mocker.patch.object(
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
    )

    # Act
    result = await execution_facade.run_custom_workflow(
        workflow_name="TestRefactoredWorkflow", initial_input="What is the weather?"
    )

    # Assert
    assert result == {"status": "ok", "response": "It is sunny."}
    mock_run_agent.assert_called_once_with(
        agent_name="Weather Agent", user_message="What is the weather?", session_id=None
    )
