"""
Integration tests for the ExecutionFacade.
"""

import pytest
import os

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

# Assuming models and executors are importable
from src.host_manager import HostManager  # For host_manager fixture

# Test Cases


async def test_facade_run_agent(host_manager: HostManager):
    """
    Test Case 4.2: Verify ExecutionFacade.run_agent executes a basic agent.
    Requires ANTHROPIC_API_KEY.
    """
    print("\n--- Running Test: test_facade_run_agent ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution

    agent_name = "Weather Agent"  # Agent defined in testing_config.json
    user_message = "What's the weather in Boston?"

    assert agent_name in host_manager.agent_configs, (
        f"'{agent_name}' not found for test setup."
    )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

    try:
        result = await facade.run_agent(
            agent_name=agent_name, user_message=user_message
        )
        print(f"Facade run_agent Result: {result}")

        # Assertions (focus on completion and basic structure)
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("error") is None
        assert "final_response" in result
        assert result["final_response"] is not None
        # Check for stop reason (e.g., 'end_turn' or 'tool_use' if tools were called)
        assert result["final_response"].stop_reason in ["end_turn", "tool_use"]
        # Basic content check
        assert "Boston" in str(result["final_response"].content)

        print("Assertions passed.")

    except Exception as e:
        print(f"Error during facade.run_agent execution: {e}")
        pytest.fail(f"facade.run_agent execution failed: {e}")

    print("--- Test Finished: test_facade_run_agent ---")


async def test_facade_run_simple_workflow(host_manager: HostManager):
    """
    Test Case 4.3: Verify ExecutionFacade.run_simple_workflow executes a workflow.
    Requires ANTHROPIC_API_KEY.
    """
    print("\n--- Running Test: test_facade_run_simple_workflow ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution

    # Use the workflow defined in testing_config.json
    workflow_name = "Example workflow using weather and planning servers"
    initial_message = "Check weather in Chicago and make a plan."

    assert workflow_name in host_manager.workflow_configs, (
        f"'{workflow_name}' not found for test setup."
    )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

    try:
        result = await facade.run_simple_workflow(
            workflow_name=workflow_name, initial_input=initial_message
        )
        print(f"Facade run_simple_workflow Result: {result}")

        # Assertions (similar to simple workflow executor tests)
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("status") == "completed"
        assert result.get("error") is None
        assert result.get("final_message") is not None
        assert isinstance(result.get("final_message"), str)
        # Check if output contains something related to the last step (planning)
        assert "plan" in result.get("final_message", "").lower()

        print("Assertions passed.")

    except Exception as e:
        print(f"Error during facade.run_simple_workflow execution: {e}")
        pytest.fail(f"facade.run_simple_workflow execution failed: {e}")

    print("--- Test Finished: test_facade_run_simple_workflow ---")


async def test_facade_run_custom_workflow(host_manager: HostManager):
    """
    Test Case 4.4: Verify ExecutionFacade.run_custom_workflow executes and passes facade.
    Requires ANTHROPIC_API_KEY.
    """
    print("\n--- Running Test: test_facade_run_custom_workflow ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution

    # Use the custom workflow defined in testing_config.json
    workflow_name = "ExampleCustom"
    initial_input = {"city": "Tokyo"}

    assert workflow_name in host_manager.custom_workflow_configs, (
        f"'{workflow_name}' not found for test setup."
    )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

    try:
        result = await facade.run_custom_workflow(
            workflow_name=workflow_name, initial_input=initial_input
        )
        print(f"Facade run_custom_workflow Result: {result}")

        # Assertions (similar to custom workflow executor tests)
        assert result is not None
        assert isinstance(result, dict)
        # Check the structure returned by the example custom workflow
        assert result.get("status") == "success"
        assert result.get("input_received") == initial_input
        assert "agent_result_text" in result
        assert isinstance(result["agent_result_text"], str)
        assert "Tokyo" in result["agent_result_text"]

        print("Assertions passed.")

    except Exception as e:
        print(f"Error during facade.run_custom_workflow execution: {e}")
        pytest.fail(f"facade.run_custom_workflow execution failed: {e}")

    print("--- Test Finished: test_facade_run_custom_workflow ---")


async def test_facade_run_agent_not_found(host_manager: HostManager):
    """
    Test Case 4.5a: Verify facade handles non-existent agent name gracefully.
    """
    print("\n--- Running Test: test_facade_run_agent_not_found ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution
    agent_name = "NonExistentAgent"
    user_message = "This should fail."

    assert agent_name not in host_manager.agent_configs, (
        f"'{agent_name}' should not exist for this test."
    )

    try:
        result = await facade.run_agent(
            agent_name=agent_name, user_message=user_message
        )
        print(f"Facade run_agent Result (Not Found): {result}")

        # Assertions: Check for error structure
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("error") is not None
        assert agent_name in result.get("error", "")
        assert "not found" in result.get("error", "").lower()
        assert result.get("final_response") is None

        print("Assertions passed.")

    except Exception as e:
        print(f"Unexpected error during facade.run_agent (not found) execution: {e}")
        pytest.fail(f"facade.run_agent (not found) raised unexpected exception: {e}")

    print("--- Test Finished: test_facade_run_agent_not_found ---")


async def test_facade_run_simple_workflow_not_found(host_manager: HostManager):
    """
    Test Case 4.5b: Verify facade handles non-existent simple workflow name gracefully.
    """
    print("\n--- Running Test: test_facade_run_simple_workflow_not_found ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution
    workflow_name = "NonExistentSimpleWorkflow"
    initial_input = "This should fail."

    assert workflow_name not in host_manager.workflow_configs, (
        f"'{workflow_name}' should not exist for this test."
    )

    try:
        result = await facade.run_simple_workflow(
            workflow_name=workflow_name, initial_input=initial_input
        )
        print(f"Facade run_simple_workflow Result (Not Found): {result}")

        # Assertions: Check for error structure
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("status") == "failed"
        assert result.get("error") is not None
        assert workflow_name in result.get("error", "")
        assert "not found" in result.get("error", "").lower()
        assert result.get("final_message") is None

        print("Assertions passed.")

    except Exception as e:
        print(
            f"Unexpected error during facade.run_simple_workflow (not found) execution: {e}"
        )
        pytest.fail(
            f"facade.run_simple_workflow (not found) raised unexpected exception: {e}"
        )

    print("--- Test Finished: test_facade_run_simple_workflow_not_found ---")


async def test_facade_run_custom_workflow_not_found(host_manager: HostManager):
    """
    Test Case 4.5c: Verify facade handles non-existent custom workflow name gracefully.
    """
    print("\n--- Running Test: test_facade_run_custom_workflow_not_found ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution
    workflow_name = "NonExistentCustomWorkflow"
    initial_input = {"data": "This should fail."}

    assert workflow_name not in host_manager.custom_workflow_configs, (
        f"'{workflow_name}' should not exist for this test."
    )

    try:
        result = await facade.run_custom_workflow(
            workflow_name=workflow_name, initial_input=initial_input
        )
        print(f"Facade run_custom_workflow Result (Not Found): {result}")

        # Assertions: Check for error structure
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("status") == "failed"
        assert result.get("error") is not None
        assert workflow_name in result.get("error", "")
        assert "not found" in result.get("error", "").lower()
        assert result.get("result") is None

        print("Assertions passed.")

    except Exception as e:
        print(
            f"Unexpected error during facade.run_custom_workflow (not found) execution: {e}"
        )
        pytest.fail(
            f"facade.run_custom_workflow (not found) raised unexpected exception: {e}"
        )

    print("--- Test Finished: test_facade_run_custom_workflow_not_found ---")
