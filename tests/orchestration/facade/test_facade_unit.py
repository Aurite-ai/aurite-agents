"""
Unit tests for the ExecutionFacade.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch  # Add patch

# Mark all tests in this module as belonging to the Orchestration layer and use anyio
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from aurite.execution.facade import ExecutionFacade
from aurite.config.config_models import (
    AgentConfig,
    LLMConfig,
    ProjectConfig,
)  # Added ProjectConfig
from aurite.host_manager import HostManager
from aurite.agents.agent import Agent

# from aurite.agents.conversation_manager import ( # Removed ConversationManager import
#     ConversationManager,
# )
from aurite.agents.agent_models import (
    AgentExecutionResult,
)  # Import result models
from aurite.llm.base_client import BaseLLM  # Import BaseLLM for type hint
from aurite.host.host import MCPHost  # Needed for type hinting if used

# --- Fixtures ---


@pytest.fixture
def mock_host_manager() -> Mock:
    """Provides a mock HostManager."""
    manager = Mock(spec=HostManager)
    manager.host = AsyncMock(spec=MCPHost)  # Mock the host instance within the manager
    manager.agent_configs = {}
    manager.llm_configs = {}  # Add llm_configs dict
    manager.workflow_configs = {}
    manager.custom_workflow_configs = {}
    manager._storage_manager = None  # Assume no storage by default for facade tests
    return manager


@pytest.fixture
def execution_facade(mock_host_manager: Mock) -> ExecutionFacade:
    """
    Provides an ExecutionFacade instance initialized with a mock HostManager,
    from which we derive a mock MCPHost and a mock ProjectConfig.
    """
    # Mock the necessary attributes and methods that ExecutionFacade will expect
    # from the objects it receives in its __init__ method.

    mock_mcphost_instance = AsyncMock(spec=MCPHost)

    # Create a mock ProjectConfig object
    mock_project_config = Mock(spec=ProjectConfig)
    mock_project_config.name = (
        "MockProject"  # For the logger in ExecutionFacade.__init__
    )
    mock_project_config.agents = (
        mock_host_manager.agent_configs
    )  # Use from mock_host_manager for consistency in tests
    mock_project_config.llms = mock_host_manager.llm_configs
    mock_project_config.simple_workflows = (
        mock_host_manager.workflow_configs
    )
    mock_project_config.custom_workflows = (
        mock_host_manager.custom_workflow_configs
    )

    # Ensure the mock_host_manager's host attribute is the mock_mcphost_instance
    # This isn't strictly needed for the new ExecutionFacade init if we pass host_instance directly,
    # but good for consistency if any test still tries to access mock_host_manager.host
    mock_host_manager.host = mock_mcphost_instance

    # Instantiate ExecutionFacade with the new signature
    facade = ExecutionFacade(
        host_instance=mock_mcphost_instance,
        current_project=mock_project_config,
        storage_manager=mock_host_manager._storage_manager,  # Accessing protected for fixture setup
    )
    return facade


# --- Test Class ---


class TestExecutionFacadeUnit:
    """Unit tests for ExecutionFacade public methods."""

    @pytest.mark.asyncio
    @patch("src.execution.facade.Agent")
    async def test_run_agent_success_and_caching(
        self,
        MockAgent: MagicMock,
        execution_facade: ExecutionFacade, # Removed mock_host_manager as it's part of facade
    ):
        """
        Test run_agent successfully executes, uses _create_llm_client for new clients,
        and reuses cached clients for subsequent calls with the same LLMConfig ID.
        """
        print("\n--- Running Test: test_run_agent_success_and_caching ---")
        agent1_name = "AgentOne"
        agent2_name = "AgentTwoSameLLM"
        agent3_name = "AgentThreeDifferentLLM"
        user_message = "Hello Agent"

        # --- Mock Project Configs ---
        llm_config1 = LLMConfig(llm_id="llm_id_1", provider="anthropic", model_name="model-1")
        llm_config2 = LLMConfig(llm_id="llm_id_2", provider="anthropic", model_name="model-2")

        agent_config1 = AgentConfig(name=agent1_name, llm_config_id="llm_id_1")
        agent_config2 = AgentConfig(name=agent2_name, llm_config_id="llm_id_1") # Uses same LLMConfig
        agent_config3 = AgentConfig(name=agent3_name, llm_config_id="llm_id_2") # Uses different LLMConfig

        execution_facade._current_project.agents = {
            agent1_name: agent_config1,
            agent2_name: agent_config2,
            agent3_name: agent_config3,
        }
        execution_facade._current_project.llms = {
            "llm_id_1": llm_config1,
            "llm_id_2": llm_config2,
        }

        # --- Mock _create_llm_client ---
        # This method is now part of ExecutionFacade, so we patch it there.
        mock_llm_client_instance1 = AsyncMock(spec=BaseLLM)
        mock_llm_client_instance2 = AsyncMock(spec=BaseLLM)
        # Configure side_effect to return different mocks for different LLMConfigs
        def create_llm_client_side_effect(llm_config_arg: LLMConfig):
            if llm_config_arg.llm_id == "llm_id_1":
                return mock_llm_client_instance1
            elif llm_config_arg.llm_id == "llm_id_2":
                return mock_llm_client_instance2
            raise ValueError("Unexpected LLMConfig in mock _create_llm_client")

        execution_facade._create_llm_client = MagicMock(side_effect=create_llm_client_side_effect)


        # --- Mock Agent ---
        mock_agent_instance = MagicMock(spec=Agent)
        mock_agent_result = AgentExecutionResult(
            conversation=[], final_response=None, tool_uses_in_final_turn=[], error=None
        )
        mock_agent_instance.run_conversation = AsyncMock(return_value=mock_agent_result)
        MockAgent.return_value = mock_agent_instance

        # --- Act & Assert: AgentOne (first call for llm_id_1) ---
        print("Running AgentOne...")
        await execution_facade.run_agent(agent_name=agent1_name, user_message=user_message)
        execution_facade._create_llm_client.assert_called_once_with(llm_config1)
        MockAgent.assert_called_with(
            config=agent_config1,
            llm_client=mock_llm_client_instance1,
            host_instance=execution_facade._host,
            initial_messages=[{"role": "user", "content": [{"type": "text", "text": user_message}]}],
            system_prompt_override=None,
            llm_config_for_override=llm_config1
        )
        assert execution_facade._llm_client_cache.get("llm_id_1") == mock_llm_client_instance1

        # --- Act & Assert: AgentTwoSameLLM (should use cached client for llm_id_1) ---
        print("Running AgentTwoSameLLM...")
        execution_facade._create_llm_client.reset_mock() # Reset before next call
        MockAgent.reset_mock()
        await execution_facade.run_agent(agent_name=agent2_name, user_message=user_message)
        execution_facade._create_llm_client.assert_not_called() # Should use cache
        MockAgent.assert_called_with(
            config=agent_config2,
            llm_client=mock_llm_client_instance1, # Reused instance
            host_instance=execution_facade._host,
            initial_messages=[{"role": "user", "content": [{"type": "text", "text": user_message}]}],
            system_prompt_override=None,
            llm_config_for_override=llm_config1
        )

        # --- Act & Assert: AgentThreeDifferentLLM (should create new client for llm_id_2) ---
        print("Running AgentThreeDifferentLLM...")
        execution_facade._create_llm_client.reset_mock()
        MockAgent.reset_mock()
        await execution_facade.run_agent(agent_name=agent3_name, user_message=user_message)
        execution_facade._create_llm_client.assert_called_once_with(llm_config2)
        MockAgent.assert_called_with(
            config=agent_config3,
            llm_client=mock_llm_client_instance2, # New instance
            host_instance=execution_facade._host,
            initial_messages=[{"role": "user", "content": [{"type": "text", "text": user_message}]}],
            system_prompt_override=None,
            llm_config_for_override=llm_config2
        )
        assert execution_facade._llm_client_cache.get("llm_id_2") == mock_llm_client_instance2

        print("Assertions passed for caching.")
        print("--- Test Finished: test_run_agent_success_and_caching ---")


    @pytest.mark.asyncio
    @patch("src.execution.facade.Agent")
    async def test_run_agent_no_llm_config_id(
        self,
        MockAgent: MagicMock,
        execution_facade: ExecutionFacade,
    ):
        """
        Test run_agent when AgentConfig has no llm_config_id.
        It should create a temporary, non-cached LLM client based on agent overrides.
        """
        print("\n--- Running Test: test_run_agent_no_llm_config_id ---")
        agent_name = "AgentNoLLMID"
        user_message = "Hello"

        agent_config_no_id = AgentConfig(
            name=agent_name,
            model="agent-direct-model", # Direct override
            temperature=0.6,
            system_prompt="Agent direct system prompt"
            # No llm_config_id
        )
        execution_facade._current_project.agents = {agent_name: agent_config_no_id}
        execution_facade._current_project.llms = {} # No LLMConfigs defined

        mock_temp_llm_client = AsyncMock(spec=BaseLLM)
        execution_facade._create_llm_client = MagicMock(return_value=mock_temp_llm_client)

        mock_agent_instance = MagicMock(spec=Agent)
        mock_agent_result = AgentExecutionResult(conversation=[], final_response=None, tool_uses_in_final_turn=[], error=None)
        mock_agent_instance.run_conversation = AsyncMock(return_value=mock_agent_result)
        MockAgent.return_value = mock_agent_instance

        # --- Act ---
        await execution_facade.run_agent(agent_name=agent_name, user_message=user_message)

        # --- Assertions ---
        # 1. _create_llm_client was called
        execution_facade._create_llm_client.assert_called_once()
        created_llm_config_arg = execution_facade._create_llm_client.call_args.args[0]
        assert isinstance(created_llm_config_arg, LLMConfig)
        assert created_llm_config_arg.llm_id == f"temp_{agent_name}"
        assert created_llm_config_arg.provider == "anthropic" # Default from factory logic
        assert created_llm_config_arg.model_name == "agent-direct-model"
        assert created_llm_config_arg.temperature == 0.6
        assert created_llm_config_arg.default_system_prompt == "Agent direct system prompt"

        # 2. Client was NOT cached
        assert not execution_facade._llm_client_cache

        # 3. Agent was instantiated correctly
        MockAgent.assert_called_with(
            config=agent_config_no_id,
            llm_client=mock_temp_llm_client,
            host_instance=execution_facade._host,
            initial_messages=[{"role": "user", "content": [{"type": "text", "text": user_message}]}],
            system_prompt_override=None,
            llm_config_for_override=None # No LLMConfig object to pass
        )
        print("Assertions passed for no_llm_config_id.")
        print("--- Test Finished: test_run_agent_no_llm_config_id ---")


    @patch("src.execution.facade.AnthropicLLM") # Patch the concrete class
    def test_create_llm_client_factory(
        self,
        MockAnthropicLLMConstructor: MagicMock,
        execution_facade: ExecutionFacade
    ):
        """Test the _create_llm_client factory method directly."""
        print("\n--- Running Test: test_create_llm_client_factory ---")

        # Test Anthropic
        anthropic_config = LLMConfig(llm_id="anthropic_test", provider="anthropic", model_name="claude-model", temperature=0.7, max_tokens=100, default_system_prompt="Anthropic System")
        mock_anthropic_instance = MagicMock(spec=BaseLLM)
        MockAnthropicLLMConstructor.return_value = mock_anthropic_instance

        client = execution_facade._create_llm_client(anthropic_config)
        MockAnthropicLLMConstructor.assert_called_once_with(
            model_name="claude-model",
            temperature=0.7,
            max_tokens=100,
            system_prompt="Anthropic System"
        )
        assert client == mock_anthropic_instance

        # Test Unsupported Provider
        unsupported_config = LLMConfig(llm_id="unsupported_test", provider="unobtainium", model_name="future-model")
        with pytest.raises(NotImplementedError, match="LLM provider 'unobtainium' is not currently supported."):
            execution_facade._create_llm_client(unsupported_config)

        # Test Default Model Name
        MockAnthropicLLMConstructor.reset_mock()
        anthropic_no_model_config = LLMConfig(llm_id="anthropic_no_model", provider="anthropic")
        execution_facade._create_llm_client(anthropic_no_model_config)
        MockAnthropicLLMConstructor.assert_called_once_with(
            model_name="claude-3-haiku-20240307", # Default from factory
            temperature=None,
            max_tokens=None,
            system_prompt=None
        )
        print("Assertions passed for _create_llm_client factory.")
        print("--- Test Finished: test_create_llm_client_factory ---")


    @pytest.mark.asyncio
    async def test_run_simple_workflow_success(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock # mock_host_manager still used by this test's old structure
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
        assert (
            "config_lookup" in call_kwargs
        )  # Check that the lookup function is passed
        assert "executor_setup" in call_kwargs
        assert "execution_func" in call_kwargs
        assert "error_structure_factory" in call_kwargs
        # Check args specific to the executor type that are passed through
        assert (
            call_kwargs.get("initial_input") == initial_input
        )  # Passed directly for workflows
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
        session_id = "unit_test_session_custom"  # Define session ID
        expected_result = {"status": "completed", "result": "Custom Done"}

        # Mock the internal _execute_component method
        execution_facade._execute_component = AsyncMock(return_value=expected_result)

        # Call the public method
        result = await execution_facade.run_custom_workflow(
            workflow_name=workflow_name,
            initial_input=initial_input,
            session_id=session_id,  # Pass session ID
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
        assert (
            call_kwargs.get("executor") == execution_facade
        )  # CustomWorkflow specific arg
        assert call_kwargs.get("session_id") == session_id  # Verify session_id passed

        # Check the final result
        assert result == expected_result
        print("Assertions passed.")

        print("--- Test Finished: test_run_custom_workflow_success ---")

    @pytest.mark.asyncio
    async def test_run_agent_not_found(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test run_agent returns an error structure when the agent config is not found.
        """
        print("\n--- Running Test: test_run_agent_not_found ---")
        agent_name = "NonExistentAgent"
        user_message = "Hello?"

        # Ensure the agent config does not exist in the facade's current_project
        execution_facade._current_project.agents = {}
        execution_facade._current_project.llms = {}

        # Expected error structure from run_agent's internal error_factory
        expected_error_dict = AgentExecutionResult(
            conversation=[],
            final_response=None,
            tool_uses_in_final_turn=[],
            error=f"Configuration error: \"Agent configurations not found in current project for agent '{agent_name}'.\"",
        ).model_dump(mode="json")

        # Call the public method - no need to mock _execute_component
        result = await execution_facade.run_agent(
            agent_name=agent_name,
            user_message=user_message,
        )

        print(f"Execution Result: {result}")

        # Assertions
        # Verify the result matches the expected error structure
        assert result == expected_error_dict
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

        execution_facade._execute_component = AsyncMock(
            return_value=expected_error_result
        )

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

        execution_facade._execute_component = AsyncMock(
            return_value=expected_error_result
        )

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
        Test run_agent returns an error structure when the LLM client fails to instantiate.
        """
        print("\n--- Running Test: test_run_agent_instantiation_error ---")
        agent_name = "TestAgent"
        user_message = "Hello Agent"
        instantiation_error = ValueError("LLM Client Init Failed")

        # --- Mock HostManager Configs ---
        # Need valid configs up to the point of LLM instantiation
        mock_agent_config = AgentConfig(name=agent_name, llm_config_id="test_llm")
        mock_llm_config = LLMConfig(
            llm_id="test_llm", provider="anthropic", model_name="test-model"
        )
        # Populate configs directly on the facade's current_project mock
        execution_facade._current_project.agents = {
            agent_name: mock_agent_config
        }
        execution_facade._current_project.llms = {"test_llm": mock_llm_config}

        # --- Mock LLM Client Instantiation to raise error ---
        with patch(
            "src.execution.facade.AnthropicLLM", side_effect=instantiation_error
        ) as MockLLM:
            # --- Act ---
            result = await execution_facade.run_agent(
                agent_name=agent_name,
                user_message=user_message,
            )

            print(f"Execution Result: {result}")

            # --- Assertions ---
            # 1. Check LLM was attempted to be instantiated
            MockLLM.assert_called_once()

            # 2. Verify the result matches the expected error structure from error_factory
            expected_error_dict = AgentExecutionResult(
                conversation=[],
                final_response=None,
                tool_uses_in_final_turn=[],
                error=f"Initialization error for Agent '{agent_name}': Failed to create Anthropic client: {instantiation_error}",
            ).model_dump(mode="json")
            assert result == expected_error_dict
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

        execution_facade._execute_component = AsyncMock(
            return_value=expected_error_result
        )

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

        execution_facade._execute_component = AsyncMock(
            return_value=expected_error_result
        )

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
        Test run_agent returns an error structure when conversation_manager.run_conversation fails.
        """
        print("\n--- Running Test: test_run_agent_execution_error ---")
        agent_name = "TestAgent"
        user_message = "Hello Agent"
        execution_error = RuntimeError("Conversation failed")

        # --- Mock HostManager Configs ---
        mock_agent_config = AgentConfig(name=agent_name, llm_config_id="test_llm")
        mock_llm_config = LLMConfig(
            llm_id="test_llm", provider="anthropic", model_name="test-model"
        )
        # Populate configs directly on the facade's current_project mock
        execution_facade._current_project.agents = {
            agent_name: mock_agent_config
        }
        execution_facade._current_project.llms = {"test_llm": mock_llm_config}

        # --- Mock LLM Client Instantiation (should succeed) ---
        with patch("src.execution.facade.AnthropicLLM") as MockLLM:
            mock_llm_instance = MagicMock(spec=BaseLLM)
            MockLLM.return_value = mock_llm_instance

            # --- Mock Agent to raise error on run_conversation ---
            with patch("src.execution.facade.Agent") as MockAgent:  # Changed to Agent
                mock_agent_instance = MagicMock(spec=Agent)  # Changed to Agent
                mock_agent_instance.run_conversation = AsyncMock(
                    side_effect=execution_error
                )
                MockAgent.return_value = mock_agent_instance  # Changed to Agent

                # --- Act ---
                result = await execution_facade.run_agent(
                    agent_name=agent_name,
                    user_message=user_message,
                )

                print(f"Execution Result: {result}")

                # --- Assertions ---
                # 1. Check LLM and Agent were instantiated
                MockLLM.assert_called_once()
                MockAgent.assert_called_once()  # Changed to Agent
                # 2. Check run_conversation was called
                mock_agent_instance.run_conversation.assert_awaited_once()  # Changed to Agent instance

                # 3. Verify the result matches the expected error structure
                expected_error_dict = AgentExecutionResult(
                    conversation=[],
                    final_response=None,
                    tool_uses_in_final_turn=[],
                    error=f"Unexpected error running Agent '{agent_name}': {type(execution_error).__name__}: {execution_error}",
                ).model_dump(mode="json")
                assert result == expected_error_dict
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

        execution_facade._execute_component = AsyncMock(
            return_value=expected_error_result
        )

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

        execution_facade._execute_component = AsyncMock(
            return_value=expected_error_result
        )

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
        session_id = "internal_test_session"  # Define session ID
        expected_result = {
            "status": "completed",
            "final_response": "Mocked agent response",
        }

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
        mock_error_factory = Mock()  # Not expected to be called

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
            session_id=session_id,  # Pass session_id
        )
        print(f"Execution Result: {result}")

        # --- Assertions ---
        # 1. Config lookup was called
        mock_config_lookup.assert_called_once_with(component_name)

        # 2. Executor setup was called with the found config
        mock_executor_setup.assert_called_once_with(mock_config)

        # 3. Execution function was called correctly
        mock_execution_func.assert_awaited_once()
        positional_args, keyword_args = mock_execution_func.call_args
        # Check the 'instance' positional argument
        assert len(positional_args) == 1
        assert positional_args[0] == mock_agent_instance
        # Check the other arguments passed via **kwargs
        assert keyword_args.get("host_instance") == mock_host_manager.host
        assert keyword_args.get("user_message") == initial_input
        assert keyword_args.get("session_id") == session_id  # Verify session_id

        # 4. Error factory was NOT called
        mock_error_factory.assert_not_called()

        # 5. Final result is correct
        assert result == expected_result
        print("Assertions passed.")

        print("--- Test Finished: test_execute_component_success_internal ---")

    @pytest.mark.asyncio
    async def test_execute_component_config_not_found(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test _execute_component returns error when config_lookup returns None.
        """
        print("\\n--- Running Test: test_execute_component_config_not_found ---")
        component_name = "MissingComponent"
        component_type = "Agent"

        # --- Mock dependencies ---
        # --- Mock dependencies ---
        # 1. Config Lookup: Use a lambda that returns None
        config_lookup_lambda = lambda name: None  # noqa: E731
        # 2. Executor Setup: Not needed/expected to be called in this path
        # 3. Execution Function: Not needed/expected to be called in this path
        # 4. Error Structure Factory: Mock to check it's called correctly
        expected_error = {
            "status": "error",
            "component_type": component_type,
            "component_name": component_name,
            "error": f"{component_type} '{component_name}' not found.",
            "details": None,
        }
        mock_error_factory = Mock(return_value=expected_error)

        # --- Call the internal method ---
        result = await execution_facade._execute_component(
            component_type=component_type,
            component_name=component_name,
            config_lookup=config_lookup_lambda,  # Pass the lambda
            executor_setup=None,  # Pass None, shouldn't be called
            execution_func=None,  # Pass None, shouldn't be called
            error_structure_factory=mock_error_factory,
            # Pass dummy args for kwargs, they shouldn't be used in this error path
            host_instance=mock_host_manager.host,
            user_message="irrelevant",
        )
        print(f"Execution Result: {result}")

        # --- Assertions ---
        # 1. Config lookup was called (We can't easily assert calls on the lambda,
        #    but the subsequent assertions implicitly test its effect)
        # Check the actual return value from the lambda (optional sanity check)
        assert config_lookup_lambda(component_name) is None

        # 2. Executor setup was NOT called (No mock to assert on)
        # 3. Execution function was NOT called (No mock to assert on)
        # 4. Error factory WAS called with correct positional arguments
        expected_error_msg = (
            f"{component_type} '{component_name}' not found (lookup returned None)."
        )
        mock_error_factory.assert_called_once_with(component_name, expected_error_msg)
        # 5. Final result is the error structure
        assert result == expected_error
        print("Assertions passed.")

        print("--- Test Finished: test_execute_component_config_not_found ---")

    @pytest.mark.asyncio
    async def test_execute_component_setup_error(
        self, execution_facade: ExecutionFacade, mock_host_manager: Mock
    ):
        """
        Test _execute_component returns error when executor_setup raises an exception.
        """
        print("\\n--- Running Test: test_execute_component_setup_error ---")
        component_name = "TestAgent"
        component_type = "Agent"
        setup_error = ValueError("Failed to setup executor")

        # --- Mock dependencies ---
        # 1. Config Lookup: Mock to return a valid config
        mock_config = MagicMock(spec=AgentConfig)
        mock_config_lookup = Mock(return_value=mock_config)
        # 2. Executor Setup: Mock to raise an error
        mock_executor_setup = Mock(side_effect=setup_error)
        # 3. Execution Function: Not expected to be called
        mock_execution_func = AsyncMock()
        # 4. Error Structure Factory: Mock to check it's called correctly
        expected_error = {
            "status": "error",
            "component_type": component_type,
            "component_name": component_name,
            "error": f"Failed to instantiate {component_type}.",
            "details": str(setup_error),
        }
        mock_error_factory = Mock(return_value=expected_error)

        # --- Call the internal method ---
        result = await execution_facade._execute_component(
            component_type=component_type,
            component_name=component_name,
            config_lookup=mock_config_lookup,
            executor_setup=mock_executor_setup,
            execution_func=mock_execution_func,
            error_structure_factory=mock_error_factory,
            # Pass dummy args for kwargs, they shouldn't be used in this error path
            host_instance=mock_host_manager.host,
            user_message="irrelevant",
        )
        print(f"Execution Result: {result}")

        # --- Assertions ---
        # 1. Config lookup was called
        mock_config_lookup.assert_called_once_with(component_name)
        # 2. Executor setup was called
        mock_executor_setup.assert_called_once_with(mock_config)
        # 3. Execution function was NOT called
        mock_execution_func.assert_not_awaited()
        # 4. Error factory WAS called with correct positional arguments
        expected_error_msg = f"Initialization error for {component_type} '{component_name}': {setup_error}"
        mock_error_factory.assert_called_once_with(component_name, expected_error_msg)
        # 5. Final result is the error structure
        assert result == expected_error
        print("Assertions passed.")

        print("--- Test Finished: test_execute_component_setup_error ---")
