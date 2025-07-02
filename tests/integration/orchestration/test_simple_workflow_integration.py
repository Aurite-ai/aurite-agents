import pytest
import json
from unittest.mock import AsyncMock

from aurite.config.config_models import ProjectConfig, HostConfig
from aurite.host.host import MCPHost
from aurite.execution.facade import ExecutionFacade
from aurite.components.workflows.simple_workflow import SimpleWorkflowExecutor
from aurite.components.agents.agent_models import AgentRunResult
from openai.types.chat import ChatCompletionMessage


@pytest.fixture
def project_config() -> ProjectConfig:
    """Loads the project configuration from the test fixture."""
    with open("tests/fixtures/project_fixture.json", "r") as f:
        config_data = json.load(f)
    return ProjectConfig(**config_data)


@pytest.fixture
def mcp_host(project_config: ProjectConfig) -> MCPHost:
    """Creates a mockable MCPHost instance."""
    # The MCPHost expects a HostConfig, which is a subset of the ProjectConfig.
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
    return ExecutionFacade(host_instance=mcp_host, current_project=project_config)


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
async def test_simple_workflow_success(
    execution_facade: ExecutionFacade, project_config: ProjectConfig, mocker
):
    """
    Tests a successful execution of a simple workflow where each agent step succeeds.
    """
    # Arrange
    # Convert list to dict for test lookup
    workflows_dict = {w.name: w for w in project_config.simple_workflows}
    workflow_config = workflows_dict.get("Weather Planning Workflow")
    assert workflow_config is not None, "Test workflow not found in fixture"

    # Mock the facade's run_agent method to simulate successful agent runs
    mock_run_agent = mocker.patch.object(
        execution_facade, "run_agent", new_callable=AsyncMock
    )

    # Define the sequential return values for each agent call in the workflow
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
    # Convert agent list to dict for executor initialization, filtering out nameless agents
    agents_dict = {a.name: a for a in project_config.agents if a.name}
    workflow_executor = SimpleWorkflowExecutor(
        config=workflow_config,
        agent_configs=agents_dict,
        facade=execution_facade,
    )
    result = await workflow_executor.execute(
        initial_input="What's the weather in Boston?"
    )

    # Assert
    assert result.status == "completed"
    assert result.error is None
    assert len(result.step_results) == 2
    assert result.final_output == "It's a beautiful sunny day at 72 degrees!"

    # Verify step 1 (Weather Agent) result is logged correctly
    assert result.step_results[0].step_name == "Weather Agent"
    assert result.step_results[0].result["status"] == "success"
    assert (
        result.step_results[0].result["final_response"]["content"]
        == '{"temperature": 72, "conditions": "Sunny"}'
    )

    # Verify step 2 (Weather Reporter) result is logged correctly
    assert result.step_results[1].step_name == "Weather Reporter"
    assert result.step_results[1].result["status"] == "success"
    assert (
        result.step_results[1].result["final_response"]["content"]
        == "It's a beautiful sunny day at 72 degrees!"
    )

    # Verify run_agent was called correctly for both steps
    assert mock_run_agent.call_count == 2
    mock_run_agent.assert_any_call(
        agent_name="Weather Agent", user_message="What's the weather in Boston?"
    )
    mock_run_agent.assert_any_call(
        agent_name="Weather Reporter",
        user_message='{"temperature": 72, "conditions": "Sunny"}',
    )


@pytest.mark.anyio
@pytest.mark.orchestration
@pytest.mark.integration
async def test_simple_workflow_agent_failure(
    execution_facade: ExecutionFacade, project_config: ProjectConfig, mocker
):
    """
    Tests that the workflow correctly handles a failure from one of its agents
    and terminates gracefully.
    """
    # Arrange
    workflows_dict = {w.name: w for w in project_config.simple_workflows}
    workflow_config = workflows_dict.get("Weather Planning Workflow")
    assert workflow_config is not None, "Test workflow not found in fixture"

    # Mock the facade's run_agent method to simulate a failure on the first call
    mock_run_agent = mocker.patch.object(
        execution_facade,
        "run_agent",
        new_callable=AsyncMock,
        return_value=AgentRunResult(
            status="error",
            final_response=None,
            conversation_history=[],
            error_message="API key is invalid",
        ),
    )

    # Act
    agents_dict = {a.name: a for a in project_config.agents if a.name}
    workflow_executor = SimpleWorkflowExecutor(
        config=workflow_config,
        agent_configs=agents_dict,
        facade=execution_facade,
    )
    result = await workflow_executor.execute(
        initial_input="What's the weather in Boston?"
    )

    # Assert
    assert result.status == "failed"
    assert (
        result.final_output == "What's the weather in Boston?"
    ), "Final output should be the input that caused the failure"
    assert result.error is not None
    assert "Agent 'Weather Agent' failed to execute successfully" in result.error
    assert "API key is invalid" in result.error
    assert len(result.step_results) == 0, "No steps should be successfully completed"

    # Verify run_agent was called only once before failing
    mock_run_agent.assert_called_once_with(
        agent_name="Weather Agent", user_message="What's the weather in Boston?"
    )
