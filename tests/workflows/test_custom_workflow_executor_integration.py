"""
Integration tests for the CustomWorkflowExecutor.
"""

import pytest

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

import logging  # Add logging import

"""
These tests verify the executor's ability to dynamically load and execute
custom workflow classes, interacting with a real MCPHost.
"""

import pytest
import os  # Import os for environment variable check

# Assuming models and executors are importable
from src.host.models import CustomWorkflowConfig
from src.workflows.custom_workflow import CustomWorkflowExecutor
from src.host_manager import HostManager  # For host_manager fixture
from src.config import PROJECT_ROOT_DIR

# Setup logger for this test module
logger = logging.getLogger(__name__)

# Define path to a valid example custom workflow for testing
# Using the one from fixtures as per the plan
VALID_WORKFLOW_PATH = (
    PROJECT_ROOT_DIR / "tests/fixtures/custom_workflows/example_workflow.py"
)
VALID_WORKFLOW_CLASS = "ExampleCustomWorkflow"

# Ensure the example workflow file exists before running tests
if not VALID_WORKFLOW_PATH.exists():
    pytest.skip(
        f"Required test fixture workflow not found at {VALID_WORKFLOW_PATH}",
        allow_module_level=True,
    )


# @pytest.mark.asyncio # Removed - covered by module-level pytestmark
async def test_custom_executor_init(host_manager: HostManager):
    """
    Test Case 1: Verify CustomWorkflowExecutor initializes correctly.
    """
    print("\n--- Running Test: test_custom_executor_init ---")
    host_instance = host_manager.host
    assert host_instance is not None, "Host instance not found in HostManager"

    workflow_config = CustomWorkflowConfig(
        name="TestCustomInit",
        module_path=VALID_WORKFLOW_PATH,
        class_name=VALID_WORKFLOW_CLASS,
        description="Test workflow for init",
    )
    print(f"Host instance type: {type(host_instance)}")
    print(f"Workflow config: {workflow_config}")

    try:
        # Updated: __init__ no longer takes host_instance
        executor = CustomWorkflowExecutor(
            config=workflow_config,
            # host_instance=host_instance, # Removed
        )
        print(f"Executor initialized: {executor}")
        assert executor is not None
        assert executor.config == workflow_config
        # assert executor._host == host_instance # Removed internal check
        print("Assertions passed.")

    except Exception as e:
        print(f"Error during initialization: {e}")
        pytest.fail(f"CustomWorkflowExecutor initialization failed: {e}")

    print("--- Test Finished: test_custom_executor_init ---")


async def test_custom_executor_basic_execution(host_manager: HostManager):
    """
    Test Case 2: Verify basic execution of a custom workflow via the executor.
    Requires ANTHROPIC_API_KEY for the agent called within the example workflow.
    """
    print("\n--- Running Test: test_custom_executor_basic_execution ---")
    assert host_manager.execution is not None, (
        "ExecutionFacade not initialized in HostManager"
    )
    facade = host_manager.execution  # Get the facade instance

    workflow_config = CustomWorkflowConfig(
        name="TestCustomExecute",
        module_path=VALID_WORKFLOW_PATH,
        class_name=VALID_WORKFLOW_CLASS,
        description="Test workflow for execution",
    )
    initial_input = {"city": "Paris"}  # Example input for the workflow
    print(f"Workflow Config: {workflow_config}")
    print(f"Initial Input: {initial_input}")

    # Requires ANTHROPIC_API_KEY for the agent called within the custom workflow
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

    try:
        # Instantiate the executor
        executor = CustomWorkflowExecutor(
            config=workflow_config,
            # host_instance is no longer needed here
        )
        print(f"Executor initialized: {executor}")

        # Execute using the facade's host instance and passing the facade itself
        result = await executor.execute(
            initial_input=initial_input,
            executor=facade,  # Pass the facade instance
        )
        print(f"Execution Result: {result}")

        # Assertions based on the expected output of ExampleCustomWorkflow
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("status") == "completed"  # Check outer status
        assert result.get("error") is None
        assert "result" in result
        inner_result = result["result"]
        assert inner_result.get("status") == "success"  # Check inner status
        assert inner_result.get("input_received") == initial_input
        assert "agent_result_text" in inner_result
        assert isinstance(inner_result["agent_result_text"], str)
        assert len(inner_result["agent_result_text"]) > 0
        assert "Paris" in inner_result["agent_result_text"]  # Check if city was used

        print("Assertions passed.")

    except Exception as e:
        print(f"Error during execution: {e}")
        pytest.fail(f"CustomWorkflowExecutor execution failed: {e}")

    print("--- Test Finished: test_custom_executor_basic_execution ---")


# Other CustomWorkflowExecutor tests (module not found, class not found, etc.)
# can be added here later or during Phase B testing as needed.

# Add more tests here following the plan (one by one)
