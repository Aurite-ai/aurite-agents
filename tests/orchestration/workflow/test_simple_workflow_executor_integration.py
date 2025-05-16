"""
Integration tests for the SimpleWorkflowExecutor.
"""

import pytest

# Mark all tests in this module as belonging to the Orchestration layer and use anyio
pytestmark = [pytest.mark.orchestration, pytest.mark.anyio]

from typing import Dict

"""
These tests verify the executor's interaction with real Agent instances
and an initialized MCPHost, focusing on the sequential execution logic.
Mocks are avoided for core components (Executor, Agent, Host).
"""

import pytest

# Assuming models and executors are importable
from aurite.config.config_models import WorkflowConfig, AgentConfig
from aurite.workflows.simple_workflow import SimpleWorkflowExecutor

# Placeholder configurations - replace with actual fixture/data later if needed
SAMPLE_AGENT_CONFIGS: Dict[str, AgentConfig] = {
    "Agent1": AgentConfig(name="Agent1", model="claude-3-haiku-20240307"),
    "Agent2": AgentConfig(name="Agent2", model="claude-3-haiku-20240307"),
}

# SAMPLE_WORKFLOW_CONFIG constant removed - using fixture now

from aurite.host_manager import HostManager  # Import HostManager
# Import the shared fixture


# @pytest.mark.asyncio # Removed - covered by module-level pytestmark
@pytest.mark.xfail(
    reason="Known ExceptionGroup error during host_manager fixture teardown"
)
async def test_simple_executor_init(
    host_manager: HostManager,
    sample_workflow_config: WorkflowConfig,  # Add fixture argument
):
    """
    Test Case 1: Verify SimpleWorkflowExecutor initializes correctly.
    (Marked xfail due to known ExceptionGroup issue in fixture teardown)
    """
    print("\n--- Running Test: test_simple_executor_init ---")
    host_instance = host_manager.host  # Get host from manager
    assert host_instance is not None, "Host instance not found in HostManager"
    print(f"Host instance type: {type(host_instance)}")
    print(f"Agent configs: {SAMPLE_AGENT_CONFIGS}")
    print(f"Workflow config: {sample_workflow_config}")  # Use fixture

    try:
        executor = SimpleWorkflowExecutor(
            config=sample_workflow_config,  # Use fixture
            agent_configs=SAMPLE_AGENT_CONFIGS,
            host_instance=host_instance,  # Pass the retrieved host instance
        )
        print(f"Executor initialized: {executor}")
        assert executor is not None
        assert executor.config == sample_workflow_config  # Use fixture
        assert executor._agent_configs == SAMPLE_AGENT_CONFIGS
        assert executor._host == host_instance
        print("Assertions passed.")

    except Exception as e:
        print(f"Error during initialization: {e}")
        pytest.fail(f"SimpleWorkflowExecutor initialization failed: {e}")

    print("--- Test Finished: test_simple_executor_init ---")


# @pytest.mark.asyncio # Removed - covered by module-level pytestmark
@pytest.mark.xfail(
    reason="Known 'Event loop is closed' error during host_manager fixture setup/teardown"
)
async def test_simple_executor_basic_execution(host_manager: HostManager):
    """
    Test Case 2: Verify basic execution of a simple workflow.
    Uses agents defined in the testing_config.json loaded by the host_manager fixture.
    Requires ANTHROPIC_API_KEY to be set in the environment.
    """
    print("\n--- Running Test: test_simple_executor_basic_execution ---")
    host_instance = host_manager.host
    assert host_instance is not None, "Host instance not found in HostManager"

    # Use agents defined in testing_config.json (e.g., Weather Agent)
    # Ensure these agent names exist in host_manager.agent_configs
    agent_name_1 = "Weather Agent"
    agent_name_2 = "Planning Agent"  # Assuming this exists and can take text input

    assert agent_name_1 in host_manager.agent_configs, (
        f"'{agent_name_1}' not found in loaded agent configs."
    )
    # assert agent_name_2 in host_manager.agent_configs, f"'{agent_name_2}' not found in loaded agent configs." # Planning agent might not exist or take simple text

    # Define a workflow config using these agents
    workflow_config = WorkflowConfig(
        name="TestBasicExecutionWorkflow",
        steps=[agent_name_1],  # Use only Weather Agent for simplicity first
        # steps=[agent_name_1, agent_name_2] # Can add more steps later
    )

    # Get all agent configs from the manager
    all_agent_configs = host_manager.agent_configs

    initial_message = "What is the weather like in London?"
    print(f"Workflow Config: {workflow_config}")
    print(f"Initial Message: {initial_message}")

    try:
        executor = SimpleWorkflowExecutor(
            config=workflow_config,
            agent_configs=all_agent_configs,
            host_instance=host_instance,
        )
        print(f"Executor initialized: {executor}")

        # Execute the workflow
        result = await executor.execute(initial_input=initial_message)
        print(f"Execution Result: {result}")

        # Assertions (focus on completion, not exact content due to LLM variability)
        assert result is not None
        assert result.get("status") == "completed"
        assert result.get("error") is None
        assert result.get("final_message") is not None
        assert isinstance(result.get("final_message"), str)
        assert len(result.get("final_message")) > 0
        # Add more specific checks if possible, e.g., keyword in response
        assert "London" in result.get("final_message", "") or "cloudy" in result.get(
            "final_message", ""
        )  # Example check

        print("Assertions passed.")

    except Exception as e:
        print(f"Error during execution: {e}")
        pytest.fail(f"SimpleWorkflowExecutor execution failed: {e}")

    print("--- Test Finished: test_simple_executor_basic_execution ---")


# @pytest.mark.asyncio # Removed - covered by module-level pytestmark
@pytest.mark.xfail(
    reason="Known ExceptionGroup error during host_manager fixture teardown"
)
async def test_simple_executor_agent_not_found(host_manager: HostManager):
    """
    Test Case 3: Verify execution fails gracefully when an agent in steps is not found.
    (Marked xfail due to known ExceptionGroup issue in fixture teardown)
    """
    print("\n--- Running Test: test_simple_executor_agent_not_found ---")
    host_instance = host_manager.host
    assert host_instance is not None, "Host instance not found in HostManager"

    # Use only an invalid agent name
    invalid_agent_name = "NonExistentAgent"

    assert invalid_agent_name not in host_manager.agent_configs, (
        f"'{invalid_agent_name}' should not exist for this test."
    )

    # Define a workflow config referencing only the invalid agent
    workflow_config = WorkflowConfig(
        name="TestAgentNotFoundWorkflow",
        steps=[invalid_agent_name],  # Only include the invalid agent
    )

    # Pass all available agent configs from the manager, even though the target one is missing
    all_agent_configs = host_manager.agent_configs
    initial_message = "This message doesn't matter for this test"
    print(f"Workflow Config: {workflow_config}")

    try:
        executor = SimpleWorkflowExecutor(
            config=workflow_config,
            agent_configs=all_agent_configs,
            host_instance=host_instance,
        )
        print(f"Executor initialized: {executor}")

        # Execute the workflow - expect it to fail immediately on the first (invalid) step
        result = await executor.execute(initial_input=initial_message)
        print(f"Execution Result: {result}")

        # Assertions: Check for failed status and appropriate error message
        assert result is not None
        assert result.get("status") == "failed"
        assert result.get("final_message") is None  # Should be None on failure
        assert result.get("error") is not None
        assert isinstance(result.get("error"), str)
        # Check for the specific error message when agent config is missing, including workflow context
        expected_error_msg = f"Configuration error in workflow '{workflow_config.name}': Agent '{invalid_agent_name}' (step 1) not found in provided agent configurations."
        assert result.get("error") == expected_error_msg

        print("Assertions passed.")

    except Exception as e:
        # We expect the executor to handle the KeyError internally and return a 'failed' status
        print(f"Unexpected error during execution: {e}")
        pytest.fail(
            f"SimpleWorkflowExecutor execution raised unexpected exception: {e}"
        )

    print("--- Test Finished: test_simple_executor_agent_not_found ---")


# Add more tests here following the plan (one by one)
