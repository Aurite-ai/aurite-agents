"""
Unit tests for the SimpleWorkflowExecutor class.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, call, patch # Import patch
from typing import Dict, Any
# Mark all tests in this module
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from src.workflows.simple_workflow import SimpleWorkflowExecutor
from src.host.models import WorkflowConfig, AgentConfig
from src.agents.agent import Agent # Needed for mocking
from src.host.host import MCPHost # Needed for mocking

# --- Fixtures ---

@pytest.fixture
def mock_host() -> AsyncMock:
    """Provides a mock MCPHost instance."""
    return AsyncMock(spec=MCPHost)

@pytest.fixture
def mock_agent_configs() -> Dict[str, AgentConfig]:
    """Provides a dictionary of mock AgentConfigs."""
    return {
        "AgentA": AgentConfig(name="AgentA", model="model-a"),
        "AgentB": AgentConfig(name="AgentB", model="model-b"),
        "FailingAgent": AgentConfig(name="FailingAgent", model="model-fail"),
    }

@pytest.fixture
def simple_workflow_config() -> WorkflowConfig:
    """Provides a basic WorkflowConfig."""
    return WorkflowConfig(
        name="TestWorkflow",
        steps=["AgentA", "AgentB"],
        description="A simple test workflow."
    )

# --- Test Class ---

class TestSimpleWorkflowExecutorUnit:
    """Unit tests for SimpleWorkflowExecutor."""

    @pytest.mark.asyncio
    async def test_init_success(
        self,
        simple_workflow_config: WorkflowConfig,
        mock_agent_configs: Dict[str, AgentConfig],
        mock_host: AsyncMock,
    ):
        """Test successful initialization."""
        print("\n--- Running Test: test_init_success ---")
        try:
            executor = SimpleWorkflowExecutor(
                config=simple_workflow_config,
                agent_configs=mock_agent_configs,
                host_instance=mock_host,
            )
            assert executor.config == simple_workflow_config
            assert executor._agent_configs == mock_agent_configs
            assert executor._host == mock_host
            print("Initialization successful.")
        except Exception as e:
            pytest.fail(f"Initialization failed unexpectedly: {e}")
        print("--- Test Finished: test_init_success ---")

    # --- More tests to be added below ---

    @pytest.mark.asyncio
    @patch('src.workflows.simple_workflow.Agent', autospec=True) # Patch Agent where it's used by the executor
    async def test_execute_success_two_steps(
        self,
        mock_agent_class: MagicMock, # The patched Agent class
        simple_workflow_config: WorkflowConfig,
        mock_agent_configs: Dict[str, AgentConfig],
        mock_host: AsyncMock,
    ):
        """Test successful execution of a two-step workflow."""
        print("\n--- Running Test: test_execute_success_two_steps ---")
        initial_input = "Start workflow"

        # --- Mock Agent Outputs (reflecting real structure) ---
        # Agent A's output
        mock_response_a_content = MagicMock()
        mock_response_a_content.type = "text"
        mock_response_a_content.text = "Output from Agent A"
        mock_response_a = MagicMock()
        mock_response_a.content = [mock_response_a_content]
        agent_a_output = {"final_response": mock_response_a, "error": None} # Use mock object

        # Agent B's output
        mock_response_b_content = MagicMock()
        mock_response_b_content.type = "text"
        mock_response_b_content.text = "Final Output from Agent B"
        mock_response_b = MagicMock()
        mock_response_b.content = [mock_response_b_content]
        agent_b_output = {"final_response": mock_response_b, "error": None} # Use mock object

        # Mock the instances that will be created by the executor
        mock_agent_a_instance = AsyncMock(spec=Agent)
        mock_agent_b_instance = AsyncMock(spec=Agent)

        # Configure the execute_agent method on the instances
        mock_agent_a_instance.execute_agent.return_value = agent_a_output
        mock_agent_b_instance.execute_agent.return_value = agent_b_output

        # Configure the patched class to return the mocked instances sequentially
        mock_agent_class.side_effect = [mock_agent_a_instance, mock_agent_b_instance]

        # Instantiate the executor
        executor = SimpleWorkflowExecutor(
            config=simple_workflow_config,
            agent_configs=mock_agent_configs,
            host_instance=mock_host,
        )

        # Execute the workflow
        result = await executor.execute(initial_input=initial_input)

        # --- Assertions ---
        # 1. Agent Class Instantiation
        assert mock_agent_class.call_count == 2
        mock_agent_class.assert_has_calls([
            call(config=mock_agent_configs["AgentA"]),
            call(config=mock_agent_configs["AgentB"]),
        ])

        # 2. Agent Execution Calls
        # Agent A called with initial input
        mock_agent_a_instance.execute_agent.assert_awaited_once_with(
            user_message=initial_input,
            host_instance=mock_host,
            storage_manager=None # Assuming no storage manager passed by default
        )
        # Agent B called with Agent A's extracted text content
        mock_agent_b_instance.execute_agent.assert_awaited_once_with(
            user_message=mock_response_a_content.text, # Check input chaining uses extracted text
            host_instance=mock_host,
            storage_manager=None
        )

        # 3. Final Result
        assert result == {
            "workflow_name": simple_workflow_config.name,
            "status": "completed",
            "final_message": mock_response_b_content.text, # Final message should be extracted text
            "error": None,
            "step_results": [agent_a_output, agent_b_output], # Check step results are stored
        }
        print("Assertions passed.")
        print("--- Test Finished: test_execute_success_two_steps ---")
