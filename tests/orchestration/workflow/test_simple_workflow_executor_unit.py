"""
Unit tests for the SimpleWorkflowExecutor.
"""

import pytest
from unittest.mock import AsyncMock, patch, call, MagicMock  # Added MagicMock

# Mark all tests in this module
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from src.workflows.simple_workflow import SimpleWorkflowExecutor
from src.host.models import WorkflowConfig, AgentConfig
from src.agents.agent import Agent  # Needed for mocking
from anthropic.types import Message  # Added Message

# Import shared fixtures

# --- Fixtures ---

# Removed local mock_mcp_host fixture - using shared one


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
        mock_mcp_host: AsyncMock,
    ):
        """
        Test successful initialization of SimpleWorkflowExecutor.
        """
        print("\n--- Running Test: test_simple_executor_init_success ---")
        try:
            executor = SimpleWorkflowExecutor(
                config=sample_workflow_config,
                agent_configs=sample_agent_configs,
                host_instance=mock_mcp_host,
            )
            assert executor.config == sample_workflow_config
            assert executor._agent_configs == sample_agent_configs
            assert executor._host == mock_mcp_host
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

        # Use patch to mock the Agent class within the executor's module scope
        # We need side_effect to return different mocks for each call
        with patch(
            "src.workflows.simple_workflow.Agent",
            side_effect=[mock_agent_instance_1, mock_agent_instance_2],
        ) as mock_agent_class:
            executor = SimpleWorkflowExecutor(
                config=sample_workflow_config,
                agent_configs=sample_agent_configs,
                host_instance=mock_mcp_host,
            )

            # --- Execute the workflow ---
            result = await executor.execute(initial_input=initial_input)

            print(f"Execution Result: {result}")

            # --- Assertions ---
            # Check Agent class was instantiated twice with correct configs
            assert mock_agent_class.call_count == 2
            mock_agent_class.assert_has_calls(
                [
                    call(config=sample_agent_configs["Agent1"]),
                    call(config=sample_agent_configs["Agent2"]),
                ]
            )

            # Check execute_agent was called on each mock instance with correct inputs
            mock_agent_instance_1.execute_agent.assert_awaited_once_with(
                user_message=initial_input,  # First agent gets initial input
                host_instance=mock_mcp_host,
            )
            # Second agent gets the extracted text content from the first agent's result
            mock_agent_instance_2.execute_agent.assert_awaited_once_with(
                user_message=agent1_output_text,  # Expecting the extracted text
                host_instance=mock_mcp_host,
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
        mock_mcp_host: AsyncMock,
    ):
        """
        Test workflow execution fails when an agent in steps is not found in agent_configs.
        """
        print("\n--- Running Test: test_simple_executor_agent_not_found ---")
        initial_input = "Start the workflow"
        # Modify config to include a non-existent agent
        invalid_workflow_config = sample_workflow_config.copy(deep=True)
        invalid_workflow_config.steps.append("NonExistentAgent")

        executor = SimpleWorkflowExecutor(
            config=invalid_workflow_config,
            agent_configs=sample_agent_configs,  # Does not contain NonExistentAgent
            host_instance=mock_mcp_host,
        )

        # --- Execute the workflow ---
        # We only need to mock the first agent to let the workflow proceed to the invalid step
        agent1_output_text = "Result from Agent1"
        mock_agent1_message = MagicMock(spec=Message)
        mock_agent1_message.content = [MagicMock(type="text", text=agent1_output_text)]
        agent1_result = {"final_response": mock_agent1_message}
        mock_agent_instance_1 = AsyncMock(spec=Agent)
        mock_agent_instance_1.execute_agent = AsyncMock(return_value=agent1_result)

        # --- Mock Agent Instantiation and Execution for preceding steps ---
        agent1_output_text = "Result from Agent1"
        mock_agent1_message = MagicMock(spec=Message)
        mock_agent1_message.content = [MagicMock(type="text", text=agent1_output_text)]
        agent1_result = {"final_response": mock_agent1_message}
        mock_agent_instance_1 = AsyncMock(spec=Agent)
        mock_agent_instance_1.execute_agent = AsyncMock(return_value=agent1_result)

        agent2_output_text = "Result from Agent2"  # Need output for step 2 as well
        mock_agent2_message = MagicMock(spec=Message)
        mock_agent2_message.content = [MagicMock(type="text", text=agent2_output_text)]
        agent2_result = {"final_response": mock_agent2_message}
        mock_agent_instance_2 = AsyncMock(spec=Agent)
        mock_agent_instance_2.execute_agent = AsyncMock(return_value=agent2_result)

        # Patch Agent class to return mocks for Agent1 and Agent2
        with patch(
            "src.workflows.simple_workflow.Agent",
            side_effect=[mock_agent_instance_1, mock_agent_instance_2],
        ) as mock_agent_class:
            result = await executor.execute(initial_input=initial_input)

        print(f"Execution Result: {result}")

        # --- Assertions ---
        # Agent should be instantiated twice (for Agent1 & Agent2) before the KeyError
        assert mock_agent_class.call_count == 2
        mock_agent_class.assert_has_calls(
            [
                call(config=sample_agent_configs["Agent1"]),
                call(config=sample_agent_configs["Agent2"]),
            ]
        )
        mock_agent_instance_1.execute_agent.assert_awaited_once()
        mock_agent_instance_2.execute_agent.assert_awaited_once()

        # Check the final result structure for failure
        assert result["status"] == "failed"
        assert result["final_message"] is None
        assert result["error"] is not None
        assert "NonExistentAgent" in result["error"]
        assert "not found in provided agent configurations" in result["error"]

        print("Assertions passed.")
        print("--- Test Finished: test_simple_executor_agent_not_found ---")

    @pytest.mark.asyncio
    async def test_simple_executor_agent_execution_failure(
        self,
        sample_workflow_config: WorkflowConfig,
        sample_agent_configs: dict[str, AgentConfig],
        mock_mcp_host: AsyncMock,
    ):
        """
        Test workflow execution fails when an agent step execution raises an error.
        """
        print("\n--- Running Test: test_simple_executor_agent_execution_failure ---")
        initial_input = "Start the workflow"
        agent_execution_error = RuntimeError("Agent failed internally")

        # --- Mock Agent Instantiation and Execution ---
        mock_agent_instance_1 = AsyncMock(spec=Agent)
        # Make the first agent raise an error during execution
        mock_agent_instance_1.execute_agent = AsyncMock(
            side_effect=agent_execution_error
        )

        # We don't need the second mock instance as the workflow should fail on the first step

        with patch(
            "src.workflows.simple_workflow.Agent", return_value=mock_agent_instance_1
        ) as mock_agent_class:
            executor = SimpleWorkflowExecutor(
                config=sample_workflow_config,
                agent_configs=sample_agent_configs,
                host_instance=mock_mcp_host,
            )

            # --- Execute the workflow ---
            result = await executor.execute(initial_input=initial_input)

            print(f"Execution Result: {result}")

            # --- Assertions ---
            # Agent class instantiated once
            mock_agent_class.assert_called_once_with(
                config=sample_agent_configs["Agent1"]
            )
            # execute_agent called once (and raised error)
            mock_agent_instance_1.execute_agent.assert_awaited_once_with(
                user_message=initial_input,
                host_instance=mock_mcp_host,
            )

            # Check the final result structure for failure
            assert result["status"] == "failed"
            assert result["final_message"] is None
            assert result["error"] is not None
            # Check the exact error message constructed by the executor
            expected_error_msg = f"Unexpected error during agent 'Agent1' (step 1) execution within workflow '{sample_workflow_config.name}': {agent_execution_error}"
            assert result["error"] == expected_error_msg

            print("Assertions passed.")

        print("--- Test Finished: test_simple_executor_agent_execution_failure ---")
