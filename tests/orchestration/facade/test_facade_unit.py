"""
Unit tests for the ExecutionFacade.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock # Add MagicMock import

# Mark all tests in this module as belonging to the Orchestration layer and use anyio
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from src.execution.facade import ExecutionFacade
from src.host.models import AgentConfig, WorkflowConfig, CustomWorkflowConfig
from src.host_manager import HostManager
from src.agents.agent import Agent
from src.workflows.simple_workflow import SimpleWorkflowExecutor
from src.workflows.custom_workflow import CustomWorkflowExecutor
from src.host.host import MCPHost  # Needed for type hinting if used

# --- Fixtures ---

@pytest.fixture
def mock_host_manager() -> Mock:
    """Provides a mock HostManager."""
    manager = Mock(spec=HostManager)
    manager.host = AsyncMock(spec=MCPHost) # Mock the host instance within the manager
    manager.agent_configs = {}
    manager.workflow_configs = {}
    manager.custom_workflow_configs = {}
    return manager

@pytest.fixture
def execution_facade(mock_host_manager: Mock) -> ExecutionFacade:
    """Provides an ExecutionFacade instance initialized with a mock HostManager."""
    # ExecutionFacade initialization requires the HostManager instance
    facade = ExecutionFacade(host_manager=mock_host_manager)
    return facade

# --- Test Class ---

class TestExecutionFacadeUnit:
    """Unit tests for ExecutionFacade public methods."""

    @pytest.mark.asyncio
    async def test_run_agent_success(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_agent successfully calls _execute_component with correct args.
        """
        print("\n--- Running Test: test_run_agent_success ---")
        agent_name = "TestAgent"
        initial_input = "Hello Agent"
        expected_result = {"status": "completed", "final_response": "Agent Response"}

        # Mock the internal _execute_component method for this unit test
        execution_facade._execute_component = AsyncMock(return_value=expected_result)

        # Call the public method
        result = await execution_facade.run_agent(
            agent_name=agent_name,
            user_message=initial_input,
        )

        print(f"Execution Result: {result}")

        # Assertions
        # Verify _execute_component was called with the arguments run_agent should provide
        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args

        # Check keyword arguments passed to _execute_component
        assert call_kwargs.get("component_type") == "Agent"
        assert call_kwargs.get("component_name") == agent_name
        # assert call_kwargs.get("config_dict") == mock_host_manager.agent_configs # Incorrect: Facade passes lookup functions
        assert "config_lookup" in call_kwargs # Check that the lookup function is passed
        assert "executor_setup" in call_kwargs
        assert "execution_func" in call_kwargs
        assert "error_structure_factory" in call_kwargs
        # Check args specific to the executor type that are passed through
        assert call_kwargs.get("host_instance") == mock_host_manager.host
        assert call_kwargs.get("user_message") == initial_input # Agent specific arg

        # Check the final result
        assert result == expected_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_agent_success ---")

    @pytest.mark.asyncio
    async def test_run_simple_workflow_success(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_simple_workflow successfully calls _execute_component with correct args.
        """
        print("\n--- Running Test: test_run_simple_workflow_success ---")
        workflow_name = "TestSimpleWorkflow"
        initial_input = "Run workflow"
        expected_result = {"status": "completed", "final_message": "Workflow Done"}

        # Mock the internal _execute_component method
        execution_facade._execute_component = AsyncMock(return_value=expected_result)

        # Call the public method
        result = await execution_facade.run_simple_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
        )

        print(f"Execution Result: {result}")

        # Assertions
        # Verify _execute_component was called with the arguments run_simple_workflow should provide
        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args

        # Check keyword arguments passed to _execute_component
        assert call_kwargs.get("component_type") == "Simple Workflow"
        assert call_kwargs.get("component_name") == workflow_name
        # assert call_kwargs.get("config_dict") == mock_host_manager.workflow_configs # Incorrect: Facade passes lookup functions
        assert "config_lookup" in call_kwargs # Check that the lookup function is passed
        assert "executor_setup" in call_kwargs
        assert "execution_func" in call_kwargs
        assert "error_structure_factory" in call_kwargs
        # Check args specific to the executor type that are passed through
        assert call_kwargs.get("initial_input") == initial_input # Passed directly for workflows
        # host_instance and agent_configs are used within the setup lambda, not passed directly here.

        # Check the final result
        assert result == expected_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_simple_workflow_success ---")

    @pytest.mark.asyncio
    async def test_run_custom_workflow_success(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_custom_workflow successfully calls _execute_component with correct args.
        """
        print("\n--- Running Test: test_run_custom_workflow_success ---")
        workflow_name = "TestCustomWorkflow"
        initial_input = {"data": "start"}
        expected_result = {"status": "completed", "result": "Custom Done"}

        # Mock the internal _execute_component method
        execution_facade._execute_component = AsyncMock(return_value=expected_result)

        # Call the public method
        result = await execution_facade.run_custom_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
        )

        print(f"Execution Result: {result}")

        # Assertions
        # Verify _execute_component was called with the arguments run_custom_workflow should provide
        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args

        # Check keyword arguments passed to _execute_component
        assert call_kwargs.get("component_type") == "Custom Workflow"
        assert call_kwargs.get("component_name") == workflow_name
        # assert call_kwargs.get("config_dict") == mock_host_manager.custom_workflow_configs # Incorrect
        assert "config_lookup" in call_kwargs
        assert "executor_setup" in call_kwargs
        assert "execution_func" in call_kwargs
        assert "error_structure_factory" in call_kwargs
        # Check args specific to the executor type that are passed through
        assert call_kwargs.get("initial_input") == initial_input
        assert call_kwargs.get("executor") == execution_facade # CustomWorkflow specific arg

        # Check the final result
        assert result == expected_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_custom_workflow_success ---")

    @pytest.mark.asyncio
    async def test_run_agent_not_found(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_agent returns an error structure when the agent is not found.
        (Simulated by having _execute_component return the error).
        """
        print("\n--- Running Test: test_run_agent_not_found ---")
        agent_name = "NonExistentAgent"
        initial_input = "Hello?"
        # This is the expected error structure returned by _execute_component's error_factory
        expected_error_result = {
            "status": "error",
            "component_type": "Agent",
            "component_name": agent_name,
            "error": f"Agent '{agent_name}' not found.",
            "details": None,
        }

        # Mock _execute_component to return the specific error structure
        execution_facade._execute_component = AsyncMock(return_value=expected_error_result)

        # Call the public method
        result = await execution_facade.run_agent(
            agent_name=agent_name,
            user_message=initial_input,
        )

        print(f"Execution Result: {result}")

        # Assertions
        # Verify _execute_component was called correctly
        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args
        assert call_kwargs.get("component_name") == agent_name
        assert call_kwargs.get("component_type") == "Agent"

        # Verify the result matches the expected error structure
        assert result == expected_error_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_agent_not_found ---")

    @pytest.mark.asyncio
    async def test_run_simple_workflow_not_found(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_simple_workflow returns an error structure when the workflow is not found.
        """
        print("\n--- Running Test: test_run_simple_workflow_not_found ---")
        workflow_name = "NonExistentWorkflow"
        initial_input = "Run?"
        expected_error_result = {
            "status": "error",
            "component_type": "Simple Workflow",
            "component_name": workflow_name,
            "error": f"Simple Workflow '{workflow_name}' not found.",
            "details": None,
        }

        execution_facade._execute_component = AsyncMock(return_value=expected_error_result)

        result = await execution_facade.run_simple_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
        )

        print(f"Execution Result: {result}")

        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args
        assert call_kwargs.get("component_name") == workflow_name
        assert call_kwargs.get("component_type") == "Simple Workflow"
        assert result == expected_error_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_simple_workflow_not_found ---")

    @pytest.mark.asyncio
    async def test_run_custom_workflow_not_found(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_custom_workflow returns an error structure when the workflow is not found.
        """
        print("\n--- Running Test: test_run_custom_workflow_not_found ---")
        workflow_name = "NonExistentCustomWorkflow"
        initial_input = {"data": "start?"}
        expected_error_result = {
            "status": "error",
            "component_type": "Custom Workflow",
            "component_name": workflow_name,
            "error": f"Custom Workflow '{workflow_name}' not found.",
            "details": None,
        }

        execution_facade._execute_component = AsyncMock(return_value=expected_error_result)

        result = await execution_facade.run_custom_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
        )

        print(f"Execution Result: {result}")

        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args
        assert call_kwargs.get("component_name") == workflow_name
        assert call_kwargs.get("component_type") == "Custom Workflow"
        assert result == expected_error_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_custom_workflow_not_found ---")

    @pytest.mark.asyncio
    async def test_run_agent_instantiation_error(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_agent returns an error structure when the Agent class fails to instantiate.
        (Simulated by having _execute_component raise an error during setup).
        """
        print("\n--- Running Test: test_run_agent_instantiation_error ---")
        agent_name = "TestAgent"
        initial_input = "Hello Agent"
        instantiation_error = TypeError("Failed to create Agent")
        # This is the expected error structure when instantiation fails inside _execute_component
        expected_error_result = {
            "status": "error",
            "component_type": "Agent",
            "component_name": agent_name,
            "error": "Failed to instantiate Agent.",
            "details": str(instantiation_error),
        }

        # Mock _execute_component to raise the error
        execution_facade._execute_component = AsyncMock(side_effect=instantiation_error)
        # We also need to mock the error factory specifically for this test case,
        # as the default one inside run_agent won't be called if _execute_component raises early.
        # However, the goal is to test that run_agent *calls* _execute_component and returns whatever
        # _execute_component returns or raises. Let's refine: _execute_component *should* catch
        # the instantiation error and return the structured error. So we mock _execute_component
        # to return the expected error structure directly, simulating its internal error handling.
        execution_facade._execute_component = AsyncMock(return_value=expected_error_result)


        # Call the public method
        result = await execution_facade.run_agent(
            agent_name=agent_name,
            user_message=initial_input,
        )

        print(f"Execution Result: {result}")

        # Assertions
        # Verify _execute_component was called correctly
        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args
        assert call_kwargs.get("component_name") == agent_name
        assert call_kwargs.get("component_type") == "Agent"

        # Verify the result matches the expected error structure
        assert result == expected_error_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_agent_instantiation_error ---")

    @pytest.mark.asyncio
    async def test_run_simple_workflow_instantiation_error(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_simple_workflow returns error when SimpleWorkflowExecutor fails to instantiate.
        """
        print("\n--- Running Test: test_run_simple_workflow_instantiation_error ---")
        workflow_name = "TestSimpleWorkflow"
        initial_input = "Run workflow"
        instantiation_error = ValueError("Bad config for SimpleWorkflow")
        expected_error_result = {
            "status": "error",
            "component_type": "Simple Workflow",
            "component_name": workflow_name,
            "error": "Failed to instantiate Simple Workflow.",
            "details": str(instantiation_error),
        }

        execution_facade._execute_component = AsyncMock(return_value=expected_error_result)

        result = await execution_facade.run_simple_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
        )

        print(f"Execution Result: {result}")

        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args
        assert call_kwargs.get("component_name") == workflow_name
        assert call_kwargs.get("component_type") == "Simple Workflow"
        assert result == expected_error_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_simple_workflow_instantiation_error ---")

    @pytest.mark.asyncio
    async def test_run_custom_workflow_instantiation_error(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_custom_workflow returns error when CustomWorkflowExecutor fails to instantiate.
        """
        print("\n--- Running Test: test_run_custom_workflow_instantiation_error ---")
        workflow_name = "TestCustomWorkflow"
        initial_input = {"data": "start"}
        instantiation_error = ImportError("Cannot import custom module")
        expected_error_result = {
            "status": "error",
            "component_type": "Custom Workflow",
            "component_name": workflow_name,
            "error": "Failed to instantiate Custom Workflow.",
            "details": str(instantiation_error),
        }

        execution_facade._execute_component = AsyncMock(return_value=expected_error_result)

        result = await execution_facade.run_custom_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
        )

        print(f"Execution Result: {result}")

        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args
        assert call_kwargs.get("component_name") == workflow_name
        assert call_kwargs.get("component_type") == "Custom Workflow"
        assert result == expected_error_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_custom_workflow_instantiation_error ---")

    @pytest.mark.asyncio
    async def test_run_agent_execution_error(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_agent returns an error structure when the agent's execute_agent method fails.
        (Simulated by having _execute_component return the error).
        """
        print("\n--- Running Test: test_run_agent_execution_error ---")
        agent_name = "TestAgent"
        initial_input = "Hello Agent"
        execution_error = RuntimeError("LLM API call failed")
        # This is the expected error structure when execution fails inside _execute_component
        expected_error_result = {
            "status": "error",
            "component_type": "Agent",
            "component_name": agent_name,
            "error": "Agent execution failed.",
            "details": str(execution_error),
        }

        # Mock _execute_component to return the error structure simulating an execution failure
        execution_facade._execute_component = AsyncMock(return_value=expected_error_result)

        # Call the public method
        result = await execution_facade.run_agent(
            agent_name=agent_name,
            user_message=initial_input,
        )

        print(f"Execution Result: {result}")

        # Assertions
        # Verify _execute_component was called correctly
        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args
        assert call_kwargs.get("component_name") == agent_name
        assert call_kwargs.get("component_type") == "Agent"

        # Verify the result matches the expected error structure
        assert result == expected_error_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_agent_execution_error ---")

    @pytest.mark.asyncio
    async def test_run_simple_workflow_execution_error(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_simple_workflow returns error when the workflow's execute method fails.
        """
        print("\n--- Running Test: test_run_simple_workflow_execution_error ---")
        workflow_name = "TestSimpleWorkflow"
        initial_input = "Run workflow"
        execution_error = Exception("Something broke mid-workflow")
        expected_error_result = {
            "status": "error",
            "component_type": "Simple Workflow",
            "component_name": workflow_name,
            "error": "Simple Workflow execution failed.",
            "details": str(execution_error),
        }

        execution_facade._execute_component = AsyncMock(return_value=expected_error_result)

        result = await execution_facade.run_simple_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
        )

        print(f"Execution Result: {result}")

        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args
        assert call_kwargs.get("component_name") == workflow_name
        assert call_kwargs.get("component_type") == "Simple Workflow"
        assert result == expected_error_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_simple_workflow_execution_error ---")

    @pytest.mark.asyncio
    async def test_run_custom_workflow_execution_error(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_custom_workflow returns error when the workflow's execute method fails.
        """
        print("\n--- Running Test: test_run_custom_workflow_execution_error ---")
        workflow_name = "TestCustomWorkflow"
        initial_input = {"data": "start"}
        execution_error = ValueError("Custom workflow logic error")
        expected_error_result = {
            "status": "error",
            "component_type": "Custom Workflow",
            "component_name": workflow_name,
            "error": "Custom Workflow execution failed.",
            "details": str(execution_error),
        }

        execution_facade._execute_component = AsyncMock(return_value=expected_error_result)

        result = await execution_facade.run_custom_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
        )

        print(f"Execution Result: {result}")

        execution_facade._execute_component.assert_awaited_once()
        call_args, call_kwargs = execution_facade._execute_component.call_args
        assert call_kwargs.get("component_name") == workflow_name
        assert call_kwargs.get("component_type") == "Custom Workflow"
        assert result == expected_error_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_custom_workflow_execution_error ---")


    # TODO: Add tests for _execute_component itself (more complex, lower priority?)


    # --- Tests for _execute_component ---

    @pytest.mark.asyncio
    async def test_execute_component_success_internal(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test the internal logic of _execute_component for a successful execution.
        This test does NOT mock _execute_component itself.
        Uses Agent execution as the example pathway.
        """
        print("\\n--- Running Test: test_execute_component_success_internal ---")
        component_name = "TestAgent"
        component_type = "Agent"
        initial_input = "Test message"
        expected_result = {"status": "completed", "final_response": "Mocked agent response"}

        # --- Mock dependencies ---
        # 1. Config Lookup: Mock the config_lookup function passed by run_agent
        mock_config = MagicMock(spec=AgentConfig)
        mock_config_lookup = Mock(return_value=mock_config)

        # 2. Executor Setup: Mock the executor_setup function passed by run_agent
        mock_agent_instance = AsyncMock(spec=Agent)
        mock_executor_setup = Mock(return_value=mock_agent_instance)

        # 3. Execution Function: Mock the execution_func passed by run_agent
        #    This represents the agent's execute_agent method
        mock_execution_func = AsyncMock(return_value=expected_result)

        # 4. Error Structure Factory: Mock the error factory
        mock_error_factory = Mock() # Not expected to be called

        # --- Call the internal method ---
        # We need to provide the arguments as they would be passed by run_agent
        result = await execution_facade._execute_component(
            component_type=component_type,
            component_name=component_name,
            config_lookup=mock_config_lookup,
            executor_setup=mock_executor_setup,
            execution_func=mock_execution_func,
            error_structure_factory=mock_error_factory,
            # Pass through specific args needed by the execution_func (execute_agent)
            host_instance=mock_host_manager.host,
            user_message=initial_input,
        )
        print(f"Execution Result: {result}")

        # --- Assertions ---
        # 1. Config lookup was called
        mock_config_lookup.assert_called_once_with(component_name)

        # 2. Executor setup was called with the found config
        mock_executor_setup.assert_called_once_with(mock_config)

        # 3. Execution function was called with the instance and specific args
        mock_execution_func.assert_awaited_once_with(
            instance=mock_agent_instance,
            host_instance=mock_host_manager.host,
            user_message=initial_input,
        )

        # 4. Error factory was NOT called
        mock_error_factory.assert_not_called()

        # 5. Final result is correct
        assert result == expected_result
        print("Assertions passed.")

        print("--- Test Finished: test_execute_component_success_internal ---")
