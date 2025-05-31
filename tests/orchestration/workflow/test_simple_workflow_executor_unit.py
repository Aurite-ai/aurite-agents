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
        mock_mcp_host: AsyncMock,  # Keep this
        mock_llm_client: MagicMock,  # Add new fixture
        mock_execution_facade: MagicMock,  # Add new fixture
    ):
        """
        Test successful execution of a simple workflow with multiple steps.
        Mocks Agent instantiation and execution.
        """
        print("\n--- Running Test: test_simple_executor_execute_success ---")
        initial_input = "Start the workflow"
        agent1_output_text = "Result from Agent1"
        agent2_output_text = "Final Result from Agent2"

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

        # --- Assertions ---
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
        assert (
            result["final_message"] == agent2_output_text
        )  # Final message is the text from last agent
        assert result["error"] is None
        # Removed assertions for step_results as it's not returned by the executor
        # assert "step_results" in result
        # assert len(result["step_results"]) == 2
        # assert result["step_results"]["Agent1"] == agent1_result
        # assert result["step_results"]["Agent2"] == agent2_result

        print("Assertions passed.")

        print("--- Test Finished: test_simple_executor_execute_success ---")

    @pytest.mark.asyncio
    async def test_simple_executor_agent_not_found(
        self,
        sample_workflow_config: WorkflowConfig,
        sample_agent_configs: dict[str, AgentConfig],
        mock_mcp_host: AsyncMock,  # Keep
        mock_llm_client: MagicMock,  # Add
        mock_execution_facade: MagicMock,  # Add
    ):
        """
        Test workflow execution fails when an agent in steps is not found in agent_configs.
        (This test might need adjustment if facade handles agent lookup failure)
        """
        print("\n--- Running Test: test_simple_executor_agent_not_found ---")
        initial_input = "Start the workflow"
        # Modify config to include a non-existent agent
        invalid_workflow_config = sample_workflow_config.copy(deep=True)
        invalid_workflow_config.steps.append("NonExistentAgent")

        # Mock facade.run_agent to simulate successful calls for existing agents
        # and then raise an error or return an error structure when NonExistentAgent is called.
        agent1_output_text = "Result from Agent1"
        agent2_output_text = "Result from Agent2"

        async def mock_run_agent_for_not_found(*args, **kwargs):
            agent_name = kwargs.get("agent_name")
            if agent_name == "Agent1":
                return {
                    "final_response": {
                        "content": [{"type": "text", "text": agent1_output_text}]
                    },
                    "error": None,
                }
            elif agent_name == "Agent2":
                return {
                    "final_response": {
                        "content": [{"type": "text", "text": agent2_output_text}]
                    },
                    "error": None,
                }
            elif agent_name == "NonExistentAgent":
                # Simulate facade indicating agent not found, which SimpleWorkflowExecutor should handle
                return {
                    "final_response": None,
                    "error": f"Agent '{agent_name}' configuration not found by facade.",
                }
            return {"final_response": None, "error": "Unknown agent in mock"}

        mock_execution_facade.run_agent = AsyncMock(
            side_effect=mock_run_agent_for_not_found
        )

        executor = SimpleWorkflowExecutor(
            config=invalid_workflow_config,
            agent_configs=sample_agent_configs,
            # host_instance=mock_mcp_host, # Removed
            # llm_client=mock_llm_client, # Removed
            facade=mock_execution_facade,
        )

        result = await executor.execute(initial_input=initial_input)
        print(f"Execution Result: {result}")

        # --- Assertions ---
        # facade.run_agent should be called for Agent1, Agent2, and then NonExistentAgent
        assert mock_execution_facade.run_agent.await_count == 3
        mock_execution_facade.run_agent.assert_has_awaits(
            [
                call(agent_name="Agent1", user_message=initial_input),
                call(agent_name="Agent2", user_message=agent1_output_text),
                call(agent_name="NonExistentAgent", user_message=agent2_output_text),
            ]
        )

        # Check the final result structure for failure
        assert result["status"] == "failed"
        assert result["final_message"] is None
        assert result["error"] is not None
        assert "NonExistentAgent" in result["error"]
        # The error message now comes from the facade mock or how SimpleWorkflowExecutor processes it
        assert (
            "configuration not found by facade" in result["error"]
        )  # Updated expected error message

        print("Assertions passed.")
        print("--- Test Finished: test_simple_executor_agent_not_found ---")

    @pytest.mark.asyncio
    async def test_simple_executor_agent_execution_failure(
        self,
        sample_workflow_config: WorkflowConfig,
        sample_agent_configs: dict[str, AgentConfig],
        mock_mcp_host: AsyncMock,  # Keep
        mock_llm_client: MagicMock,  # Add
        mock_execution_facade: MagicMock,  # Add
    ):
        """
        Test workflow execution fails when an agent step execution raises an error.
        """
        print("\n--- Running Test: test_simple_executor_agent_execution_failure ---")
        initial_input = "Start the workflow"
        agent_execution_error_text = "Agent failed internally via facade"

        # Mock facade.run_agent to return an error for the first agent
        mock_execution_facade.run_agent = AsyncMock(
            return_value={"final_response": None, "error": agent_execution_error_text}
        )

        executor = SimpleWorkflowExecutor(
            config=sample_workflow_config,
            agent_configs=sample_agent_configs,
            # host_instance=mock_mcp_host, # Removed
            # llm_client=mock_llm_client, # Removed
            facade=mock_execution_facade,
        )

        # --- Execute the workflow ---
        result = await executor.execute(initial_input=initial_input)

        print(f"Execution Result: {result}")

        # --- Assertions ---
        # facade.run_agent called once for Agent1
        mock_execution_facade.run_agent.assert_awaited_once_with(
            agent_name="Agent1", user_message=initial_input
        )

        # Check the final result structure for failure
        assert result["status"] == "failed"
        assert result["final_message"] is None
        assert result["error"] is not None
        # The error message should now reflect what SimpleWorkflowExecutor constructs
        # based on the error returned by the facade.
        expected_error_msg_from_executor = (
            f"Agent 'Agent1' (step 1) failed: {agent_execution_error_text}"
        )
        assert result["error"] == expected_error_msg_from_executor

        print("Assertions passed.")

        print("--- Test Finished: test_simple_executor_agent_execution_failure ---")
