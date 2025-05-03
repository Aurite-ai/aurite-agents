"""
Integration tests for the SimpleWorkflowExecutor.
"""

import pytest

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

from typing import Dict

"""
These tests verify the executor's interaction with real Agent instances
and an initialized MCPHost, focusing on the sequential execution logic.
Mocks are avoided for core components (Executor, Agent, Host).
"""

import pytest
from typing import Dict

# Assuming models and executors are importable
from src.host.models import WorkflowConfig, AgentConfig
from src.host.host import MCPHost
from src.workflows.simple_workflow import SimpleWorkflowExecutor

# Placeholder configurations - replace with actual fixture/data later if needed
SAMPLE_AGENT_CONFIGS: Dict[str, AgentConfig] = {
    "Agent1": AgentConfig(name="Agent1", model="claude-3-haiku-20240307"),
    "Agent2": AgentConfig(name="Agent2", model="claude-3-haiku-20240307"),
}

SAMPLE_WORKFLOW_CONFIG = WorkflowConfig(
    name="TestSimpleWorkflow", steps=["Agent1", "Agent2"]
)


from src.host_manager import HostManager  # Import HostManager


# @pytest.mark.asyncio # Removed - covered by module-level pytestmark
async def test_simple_executor_init(
    host_manager: HostManager,
):  # Use host_manager fixture
    """
    Test Case 1: Verify SimpleWorkflowExecutor initializes correctly.
    """
    print(f"\n--- Running Test: test_simple_executor_init ---")
    host_instance = host_manager.host  # Get host from manager
    assert host_instance is not None, "Host instance not found in HostManager"
    print(f"Host instance type: {type(host_instance)}")
    print(f"Agent configs: {SAMPLE_AGENT_CONFIGS}")
    print(f"Workflow config: {SAMPLE_WORKFLOW_CONFIG}")

    try:
        executor = SimpleWorkflowExecutor(
            config=SAMPLE_WORKFLOW_CONFIG,
            agent_configs=SAMPLE_AGENT_CONFIGS,
            host_instance=host_instance,  # Pass the retrieved host instance
        )
        print(f"Executor initialized: {executor}")
        assert executor is not None
        assert executor.config == SAMPLE_WORKFLOW_CONFIG
        assert executor._agent_configs == SAMPLE_AGENT_CONFIGS
        assert executor._host == host_instance
        print("Assertions passed.")

    except Exception as e:
        print(f"Error during initialization: {e}")
        pytest.fail(f"SimpleWorkflowExecutor initialization failed: {e}")

    print("--- Test Finished: test_simple_executor_init ---")


# @pytest.mark.asyncio # Removed - covered by module-level pytestmark
async def test_simple_executor_basic_execution(host_manager: HostManager):
    """
    Test Case 2: Verify basic execution of a simple workflow.
    Uses agents defined in the testing_config.json loaded by the host_manager fixture.
    Requires ANTHROPIC_API_KEY to be set in the environment.
    """
    print(f"\n--- Running Test: test_simple_executor_basic_execution ---")
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
async def test_simple_executor_agent_not_found(host_manager: HostManager):
    """
    Test Case 3: Verify execution fails gracefully when an agent in steps is not found.
    """
    print(f"\n--- Running Test: test_simple_executor_agent_not_found ---")
    host_instance = host_manager.host
    assert host_instance is not None, "Host instance not found in HostManager"

    # Use a valid agent and an invalid one
    valid_agent_name = "Weather Agent"
    invalid_agent_name = "NonExistentAgent"

    assert valid_agent_name in host_manager.agent_configs, (
        f"'{valid_agent_name}' not found for test setup."
    )
    assert invalid_agent_name not in host_manager.agent_configs, (
        f"'{invalid_agent_name}' should not exist for this test."
    )

    # Define a workflow config referencing the invalid agent
    workflow_config = WorkflowConfig(
        name="TestAgentNotFoundWorkflow",
        steps=[valid_agent_name, invalid_agent_name],  # Second step uses invalid agent
    )

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

        # Execute the workflow - expect it to fail during the second step
        result = await executor.execute(initial_input=initial_message)
        print(f"Execution Result: {result}")

        # Assertions: Check for failed status and appropriate error message
        assert result is not None
        assert result.get("status") == "failed"
        assert result.get("final_message") is None  # Should be None on failure
        assert result.get("error") is not None
        assert isinstance(result.get("error"), str)
        assert invalid_agent_name in result.get("error", "")
        assert "not found in provided agent configurations" in result.get("error", "")

        print("Assertions passed.")

    except Exception as e:
        # We expect the executor to handle the KeyError internally and return a 'failed' status
        print(f"Unexpected error during execution: {e}")
        pytest.fail(
            f"SimpleWorkflowExecutor execution raised unexpected exception: {e}"
        )

    print("--- Test Finished: test_simple_executor_agent_not_found ---")


# Add more tests here following the plan (one by one)
