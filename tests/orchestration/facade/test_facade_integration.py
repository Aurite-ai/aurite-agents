"""
Integration tests for the ExecutionFacade.
"""

import pytest
import os
import uuid  # Add uuid import
import json  # Add json import

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

# Assuming models and executors are importable
from aurite.host_manager import Aurite  # For host_manager fixture
from aurite.agents.agent_models import AgentExecutionResult # Import AgentExecutionResult

# Test Cases


async def test_facade_run_agent(host_manager: Aurite):
    """
    Test Case 4.2: Verify ExecutionFacade.run_agent executes a basic agent.
    Requires ANTHROPIC_API_KEY.
    """
    print("\n--- Running Test: test_facade_run_agent ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution

    agent_name = "Weather Agent"  # Agent defined in testing_config.json
    user_message = "What's the weather in Boston?"
    session_id = f"test_agent_session_{uuid.uuid4()}"  # Generate unique session ID

    assert host_manager.project_manager.active_project_config is not None, (
        "Active project not loaded"
    )
    assert agent_name in host_manager.project_manager.active_project_config.agents, (
        f"'{agent_name}' not found for test setup."
    )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

    try:
        agent_result: AgentExecutionResult = await facade.run_agent(
            agent_name=agent_name,
            user_message=user_message,
            session_id=session_id,  # Pass session_id
        )
        print(f"Facade run_agent Result: {agent_result}")

        # Assertions (focus on completion and basic structure)
        assert agent_result is not None
        assert isinstance(agent_result, AgentExecutionResult)
        assert agent_result.error is None
        assert agent_result.final_response is not None
        final_response_obj = agent_result.final_response
        assert final_response_obj is not None
        # Check for stop reason (e.g., 'end_turn' or 'tool_use' if tools were called)
        assert final_response_obj.stop_reason in ["end_turn", "tool_use"]

        # Content check for JSON response
        assert final_response_obj.content is not None
        final_content_blocks = final_response_obj.content # This is List[AgentOutputContentBlock]
        assert isinstance(final_content_blocks, list) and len(final_content_blocks) > 0
        # Assuming the JSON is in the first text block
        first_text_block = next(
            (
                block # block is AgentOutputContentBlock
                for block in final_content_blocks
                if block.type == "text"
            ),
            None,
        )
        assert first_text_block is not None, (
            "No text block found in final response content"
        )
        assert first_text_block.text is not None, "Text block missing text content"
        json_text = first_text_block.text
        try:
            parsed_json = json.loads(json_text)
            # Basic check for expected keys and types in the JSON response based on the schema
            assert "weather_summary" in parsed_json, (
                "JSON response missing 'weather_summary'"
            )
            assert "temperature" in parsed_json, "JSON response missing 'temperature'"
            assert isinstance(parsed_json.get("temperature"), dict), (
                "'temperature' should be an object"
            )
            assert "value" in parsed_json.get("temperature", {}), (
                "Temperature object missing 'value'"
            )
            assert isinstance(
                parsed_json.get("temperature", {}).get("value"), (int, float)
            ), "'temperature.value' should be a number"
            assert "recommendations" in parsed_json, (
                "JSON response missing 'recommendations'"
            )
            assert isinstance(parsed_json.get("recommendations"), list), (
                "'recommendations' should be a list"
            )
        except json.JSONDecodeError:
            pytest.fail(f"Final response text block was not valid JSON: {json_text}")

        print("Assertions passed.")

    except Exception as e:
        print(f"Error during facade.run_agent execution: {e}")
        pytest.fail(f"facade.run_agent execution failed: {e}")

    print("--- Test Finished: test_facade_run_agent ---")


async def test_facade_run_simple_workflow(host_manager: Aurite):
    """
    Test Case 4.3: Verify ExecutionFacade.run_simple_workflow executes a workflow.
    Requires ANTHROPIC_API_KEY.
    """
    print("\n--- Running Test: test_facade_run_simple_workflow ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution

    # Use the workflow defined in testing_config.json
    workflow_name = "main"  # Correct name from testing_config.json
    initial_message = "Check weather in Chicago and make a plan."

    assert host_manager.project_manager.active_project_config is not None, (
        "Active project not loaded"
    )
    assert (
        workflow_name
        in host_manager.project_manager.active_project_config.simple_workflows
    ), f"'{workflow_name}' not found for test setup."
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
        assert (
            result.get("final_message") is not None
        )  # Check that a final message exists
        assert isinstance(result.get("final_message"), str)  # Check type
        assert len(result.get("final_message", "")) > 0  # Check it's not empty

        print("Assertions passed.")

    except Exception as e:
        print(f"Error during facade.run_simple_workflow execution: {e}")
        pytest.fail(f"facade.run_simple_workflow execution failed: {e}")

    print("--- Test Finished: test_facade_run_simple_workflow ---")


@pytest.mark.xfail(
    reason="Known 'Event loop is closed' error during host_manager fixture teardown or httpx client aclose"
)
async def test_facade_run_custom_workflow(host_manager: Aurite):
    """
    Test Case 4.4: Verify ExecutionFacade.run_custom_workflow executes and passes facade.
    Requires ANTHROPIC_API_KEY.
    """
    print("\n--- Running Test: test_facade_run_custom_workflow ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution  # Corrected indentation

    # Use the custom workflow defined in testing_config.json
    workflow_name = "ExampleCustomWorkflow"  # Correct name from testing_config.json
    initial_input = {"city": "Tokyo"}
    session_id = f"test_custom_session_{uuid.uuid4()}"  # Generate unique session ID

    assert host_manager.project_manager.active_project_config is not None, (
        "Active project not loaded"
    )
    assert (
        workflow_name
        in host_manager.project_manager.active_project_config.custom_workflows
    ), f"'{workflow_name}' not found for test setup."
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

    try:
        result = await facade.run_custom_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
            session_id=session_id,  # Pass session_id
        )
        print(f"Facade run_custom_workflow Result: {result}")

        # Assertions
        assert result is not None
        assert isinstance(result, dict)

        # 1. Check Facade's outer structure
        assert result.get("status") == "completed", (
            f"Expected facade status 'completed', got '{result.get('status')}'"
        )
        assert result.get("error") is None, (
            f"Expected facade error to be None, got '{result.get('error')}'"
        )
        assert "result" in result, (
            "Facade result missing 'result' key for custom workflow output"
        )

        # 2. Check the nested result from the custom workflow itself
        custom_result = result.get(
            "result", {}
        )  # Default to empty dict if 'result' key is missing
        assert isinstance(custom_result, dict), (
            f"Expected nested result to be a dict, got {type(custom_result)}"
        )

        # Check the structure returned by the example custom workflow (inner layer)
        assert custom_result.get("status") == "success", (
            f"Expected inner status 'success', got '{custom_result.get('status')}'"
        )
        # Check the fields specific to the example_workflow.py return structure
        assert "message" in custom_result, "Inner result missing 'message' key"
        assert "input_received" in custom_result, (
            "Inner result missing 'input_received' key"
        )
        assert custom_result.get("input_received") == initial_input, (
            f"Expected input_received '{initial_input}', got '{custom_result.get('input_received')}'"
        )
        assert "agent_result_text" in custom_result, (
            "Inner result missing 'agent_result_text' key"
        )
        assert isinstance(custom_result["agent_result_text"], str), (
            f"Expected agent_result_text to be a string, got {type(custom_result.get('agent_result_text'))}"
        )
        # Check the nested agent result text is valid JSON
        agent_json_text = custom_result["agent_result_text"]
        try:  # Correct indentation for try block
            agent_parsed_json = json.loads(agent_json_text)
            # Basic check for expected keys in the nested JSON response
            assert "weather_summary" in agent_parsed_json, (
                "Nested JSON response missing 'weather_summary'"
            )
            assert "temperature" in agent_parsed_json, (
                "Nested JSON response missing 'temperature'"
            )
            assert "recommendations" in agent_parsed_json, (
                "Nested JSON response missing 'recommendations'"
            )
        except json.JSONDecodeError:  # Correct indentation for except block
            pytest.fail(
                f"Nested agent_result_text was not valid JSON: {agent_json_text}"
            )

        print("Assertions passed.")

    except Exception as e:
        print(f"Error during facade.run_custom_workflow execution: {e}")
        # Include the actual result in the failure message for better debugging
        pytest.fail(  # Corrected indentation
            f"facade.run_custom_workflow execution failed: {e}. Result: {result}"
        )

    print("--- Test Finished: test_facade_run_custom_workflow ---")


async def test_facade_run_agent_not_found(host_manager: Aurite):
    """
    Test Case 4.5a: Verify facade handles non-existent agent name gracefully.
    """
    print("\n--- Running Test: test_facade_run_agent_not_found ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution
    agent_name = "NonExistentAgent"
    user_message = "This should fail."

    assert host_manager.project_manager.active_project_config is not None, (
        "Active project not loaded"
    )
    assert (
        agent_name not in host_manager.project_manager.active_project_config.agents
    ), f"'{agent_name}' should not exist for this test."

    try:
        agent_result: AgentExecutionResult = await facade.run_agent(
            agent_name=agent_name, user_message=user_message
        )
        print(f"Facade run_agent Result (Not Found): {agent_result}")

        # Assertions: Check for error structure
        assert agent_result is not None
        assert isinstance(agent_result, AgentExecutionResult)
        assert agent_result.error is not None
        assert agent_name in agent_result.error
        assert "not found" in agent_result.error.lower()
        assert agent_result.final_response is None

        print("Assertions passed.")

    except Exception as e:
        print(f"Unexpected error during facade.run_agent (not found) execution: {e}")
        pytest.fail(f"facade.run_agent (not found) raised unexpected exception: {e}")

    print("--- Test Finished: test_facade_run_agent_not_found ---")


@pytest.mark.xfail(
    reason="Known 'Event loop is closed' error during host_manager fixture teardown"
)
async def test_facade_run_simple_workflow_not_found(host_manager: Aurite):
    """
    Test Case 4.5b: Verify facade handles non-existent simple workflow name gracefully.
    (Marked xfail due to known event loop issue in fixture teardown)
    """
    print("\n--- Running Test: test_facade_run_simple_workflow_not_found ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution
    workflow_name = "NonExistentSimpleWorkflow"
    initial_input = "This should fail."

    assert host_manager.project_manager.active_project_config is not None, (
        "Active project not loaded"
    )
    assert (
        workflow_name
        not in host_manager.project_manager.active_project_config.simple_workflows
    ), f"'{workflow_name}' should not exist for this test."

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


async def test_facade_run_custom_workflow_not_found(host_manager: Aurite):
    """
    Test Case 4.5c: Verify facade handles non-existent custom workflow name gracefully.
    """
    print("\n--- Running Test: test_facade_run_custom_workflow_not_found ---")
    assert host_manager.execution is not None, "ExecutionFacade not initialized"
    facade = host_manager.execution
    workflow_name = "NonExistentCustomWorkflow"
    initial_input = {"data": "This should fail."}

    assert host_manager.project_manager.active_project_config is not None, (
        "Active project not loaded"
    )
    assert (
        workflow_name
        not in host_manager.project_manager.active_project_config.custom_workflows
    ), f"'{workflow_name}' should not exist for this test."

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
