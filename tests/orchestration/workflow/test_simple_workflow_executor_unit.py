"""
Unit tests for the SimpleWorkflowExecutor.
"""

from unittest.mock import AsyncMock, MagicMock, call  # Added MagicMock

import pytest

# Mark all tests in this module
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

from anthropic.types import Message  # Added Message

from aurite.agents.agent import Agent  # Needed for mocking
from aurite.config.config_models import AgentConfig, WorkflowConfig
from aurite.execution.facade import ExecutionFacade  # For mocking facade
from aurite.llm.base_client import BaseLLM  # For mocking llm_client

# Imports from the project
from aurite.workflows.simple_workflow import SimpleWorkflowExecutor

# Import shared fixtures

# --- Fixtures ---

# Removed local mock_mcp_host fixture - using shared one


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Provides a mock BaseLLM client."""
    return MagicMock(spec=BaseLLM)


@pytest.fixture
def mock_execution_facade() -> MagicMock:
    """Provides a mock ExecutionFacade."""
    mock_facade = MagicMock(spec=ExecutionFacade)
    # Configure any necessary default behaviors for the facade mock if needed by the executor
    # For example, if the executor calls facade.get_agent_config(), mock that.
    # For now, a basic MagicMock should suffice for the __init__ call.
    return mock_facade


@pytest.fixture
def sample_agent_configs() -> dict[str, AgentConfig]:
    """Provides sample agent configurations."""
    # Keeping this local as it's specific to the executor's input needs
    return {
        "Agent1": AgentConfig(name="Agent1", model="model-a"),
        "Agent2": AgentConfig(name="Agent2", model="model-b"),
    }


# Removed local sample_workflow_config definition if it existed

# --- Test Class ---


class TestSimpleWorkflowExecutorUnit:
    """Unit tests for the SimpleWorkflowExecutor."""

    def test_simple_executor_init_success(
        self,
        sample_workflow_config: WorkflowConfig,
        sample_agent_configs: dict[str, AgentConfig],
        mock_mcp_host: AsyncMock,  # Keep this if used by shared fixtures or other parts
        mock_llm_client: MagicMock,  # Add new fixture
        mock_execution_facade: MagicMock,  # Add new fixture
    ):
        """
        Test successful initialization of SimpleWorkflowExecutor.
        """
        print("\n--- Running Test: test_simple_executor_init_success ---")
        try:
            executor = SimpleWorkflowExecutor(
                config=sample_workflow_config,
                agent_configs=sample_agent_configs,
                # host_instance=mock_mcp_host, # Removed
                # llm_client=mock_llm_client,  # Removed
                facade=mock_execution_facade,
            )
            assert executor.config == sample_workflow_config
            assert executor._agent_configs == sample_agent_configs
            # assert executor._host == mock_mcp_host # Removed
            # assert executor._llm_client == mock_llm_client # Removed
            assert executor.facade == mock_execution_facade
            print("Assertions passed.")
        except Exception as e:
            pytest.fail(f"SimpleWorkflowExecutor initialization failed: {e}")

        print("--- Test Finished: test_simple_executor_init_success ---")

    @pytest.mark.asyncio
    async def test_simple_executor_execute_success(
        self,
        sample_workflow_config: WorkflowConfig,
        sample_agent_configs: dict[str, AgentConfig],
        mock_mcp_host: AsyncMock,
        mock_llm_client: MagicMock,
        mock_execution_facade: MagicMock,
    ):
        """
        Test successful execution of a simple workflow with multiple steps.
        Mocks Agent instantiation and execution.
        """
        print("\n--- Running Test: test_simple_executor_execute_success ---")
        initial_input = "Start the workflow"
        agent1_output_text = "Result from Agent1"
        agent2_output_text = "Final Result from Agent2"

        # Mock project config for component type inference
        mock_project_config = MagicMock(
            agents={"Agent1": {}, "Agent2": {}},
            simple_workflows={},
            custom_workflows={},
        )
        mock_execution_facade.get_project_config.return_value = mock_project_config

        # --- Mock Agent Results (Mimicking Agent structure) ---
        # Mock Message object for Agent 1's final_response
        mock_agent1_message = MagicMock(spec=Message)
        mock_agent1_message.content = [MagicMock(type="text", text=agent1_output_text)]
        agent1_result = {"final_response": mock_agent1_message}  # Contains mock Message

        # Mock Message object for Agent 2's final_response
        mock_agent2_message = MagicMock(spec=Message)
        mock_agent2_message.content = [MagicMock(type="text", text=agent2_output_text)]
        agent2_result = {"final_response": mock_agent2_message}  # Contains mock Message

        # --- Mock Agent Instantiation and Execution ---
        mock_agent_instance_1 = AsyncMock(spec=Agent)
        mock_agent_instance_1.execute_agent = AsyncMock(return_value=agent1_result)

        mock_agent_instance_2 = AsyncMock(spec=Agent)
        mock_agent_instance_2.execute_agent = AsyncMock(return_value=agent2_result)

        # The Agent class is no longer directly instantiated by SimpleWorkflowExecutor.
        # Instead, facade.run_agent is called, which is already mocked.
        # So, the patch for "workflows.simple_workflow.Agent" is removed.

        # Mock the facade's run_agent method
        # It should be an async method
        mock_execution_facade.run_agent = AsyncMock(
            side_effect=[
                {
                    "final_response": {
                        "content": [{"type": "text", "text": agent1_output_text}]
                    },
                    "error": None,
                },  # Result for Agent1
                {
                    "final_response": {
                        "content": [{"type": "text", "text": agent2_output_text}]
                    },
                    "error": None,
                },  # Result for Agent2
            ]
        )

        executor = SimpleWorkflowExecutor(
            config=sample_workflow_config,
            agent_configs=sample_agent_configs,
            facade=mock_execution_facade,
        )

        # --- Execute the workflow ---
        result = await executor.execute(initial_input=initial_input)

        print(f"Execution Result: {result}")

        # Verify get_project_config was called for type inference
        mock_execution_facade.get_project_config.assert_called()

        # Check facade.run_agent was called correctly
        assert mock_execution_facade.run_agent.await_count == 2
        mock_execution_facade.run_agent.assert_has_awaits(
            [
                call(agent_name="Agent1", user_message=initial_input),
                call(agent_name="Agent2", user_message=agent1_output_text),
            ]
        )

        # Check the final result structure
        assert result["status"] == "completed"
        assert result["workflow_name"] == sample_workflow_config.name
        assert result["final_message"] == agent2_output_text
        assert "error" not in result

        print("Assertions passed.")
        print("--- Test Finished: test_simple_executor_execute_success ---")

    @pytest.mark.asyncio
    async def test_simple_executor_agent_not_found(
        self,
        sample_workflow_config: WorkflowConfig,
        sample_agent_configs: dict[str, AgentConfig],
        mock_mcp_host: AsyncMock,
        mock_llm_client: MagicMock,
        mock_execution_facade: MagicMock,
    ):
        """
        Test workflow execution fails when a component is not found.
        (This test might need adjustment if facade handles agent lookup failure)
        """
        print("\n--- Running Test: test_simple_executor_agent_not_found ---")
        initial_input = "Start the workflow"

        # Mock project config to not include NonExistentAgent
        mock_project_config = MagicMock(
            agents={"Agent1": {}, "Agent2": {}},
            simple_workflows={},
            custom_workflows={},
        )
        mock_execution_facade.get_project_config.return_value = mock_project_config

        # Modify config to include a non-existent agent
        invalid_workflow_config = sample_workflow_config.copy(deep=True)
        invalid_workflow_config.steps.append("NonExistentAgent")

        executor = SimpleWorkflowExecutor(
            config=invalid_workflow_config,
            agent_configs=sample_agent_configs,
            facade=mock_execution_facade,
        )

        result = await executor.execute(initial_input=initial_input)
        print(f"Execution Result: {result}")

        # Verify the error is about component not found
        assert result["status"] == "failed"
        assert "No components found with name NonExistentAgent" in result["error"]
        assert result["workflow_name"] == invalid_workflow_config.name

        print("Assertions passed.")
        print("--- Test Finished: test_simple_executor_agent_not_found ---")

    @pytest.mark.asyncio
    async def test_simple_executor_agent_execution_failure(
        self,
        sample_workflow_config: WorkflowConfig,
        sample_agent_configs: dict[str, AgentConfig],
        mock_mcp_host: AsyncMock,
        mock_llm_client: MagicMock,
        mock_execution_facade: MagicMock,
    ):
        """
        Test workflow execution fails when an agent step execution raises an error.
        """
        print("\n--- Running Test: test_simple_executor_agent_execution_failure ---")
        initial_input = "Start the workflow"
        agent_execution_error_text = "Agent failed internally via facade"

        # Mock project config for component type inference
        mock_project_config = MagicMock(
            agents={"Agent1": {}, "Agent2": {}},
            simple_workflows={},
            custom_workflows={},
        )
        mock_execution_facade.get_project_config.return_value = mock_project_config

        # Mock facade.run_agent to return an error
        mock_execution_facade.run_agent = AsyncMock(
            return_value={"final_response": None, "error": agent_execution_error_text}
        )

        executor = SimpleWorkflowExecutor(
            config=sample_workflow_config,
            agent_configs=sample_agent_configs,
            facade=mock_execution_facade,
        )

        # --- Execute the workflow ---
        result = await executor.execute(initial_input=initial_input)
        print(f"Execution Result: {result}")

        # Verify get_project_config was called
        mock_execution_facade.get_project_config.assert_called()

        # Check facade.run_agent was called once
        mock_execution_facade.run_agent.assert_awaited_once_with(
            agent_name="Agent1", user_message=initial_input
        )

        # Check the final result structure
        assert result["status"] == "failed"
        assert result["workflow_name"] == sample_workflow_config.name
        assert "Error occured while processing component 'Agent1'" in result["error"]

        print("Assertions passed.")
        print("--- Test Finished: test_simple_executor_agent_execution_failure ---")
