"""
Unit tests for the ExecutionFacade class.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, call
from typing import Any, Dict, Callable, Coroutine

# Mark all tests in this module as belonging to the Orchestration layer and unit tests
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from src.execution.facade import ExecutionFacade
from src.host_manager import HostManager
from src.host.host import MCPHost
from src.host.models import AgentConfig  # For creating dummy configs

# --- Fixtures ---


@pytest.fixture
def mock_facade_host_manager() -> MagicMock:
    """Provides a MagicMock HostManager suitable for facade unit tests."""
    manager = MagicMock(spec=HostManager)
    manager.host = MagicMock(spec=MCPHost)  # Mock the host instance
    # Populate dummy configs for lookup tests
    manager.agent_configs = {"TestAgent": AgentConfig(name="TestAgent")}
    manager.workflow_configs = {"TestWorkflow": MagicMock()}
    manager.custom_workflow_configs = {"TestCustom": MagicMock()}
    return manager


@pytest.fixture
def facade_instance(mock_facade_host_manager: MagicMock) -> ExecutionFacade:
    """Provides an ExecutionFacade instance initialized with a mock HostManager."""
    return ExecutionFacade(host_manager=mock_facade_host_manager)


# --- Test Class ---


class TestExecutionFacadeUnit:
    """Unit tests for ExecutionFacade methods, especially _execute_component."""

    # --- Mocks for _execute_component arguments ---

    @staticmethod
    def mock_config_lookup(component_name: str) -> Any:
        if component_name == "NotFound":
            raise KeyError("Component not found")
        elif component_name == "LookupError":
            raise ValueError("Some lookup error")
        return {"name": component_name, "config_data": "dummy"}

    @staticmethod
    def mock_executor_setup(config: Any) -> Any:
        if config.get("name") == "SetupFail":
            raise TypeError("Executor setup failed")
        executor = MagicMock()
        executor.config = config
        return executor

    @staticmethod
    async def mock_execution_func(instance: Any, **kwargs: Any) -> Any:
        if instance.config.get("name") == "ExecFailKnown":
            raise FileNotFoundError("Known execution error")
        elif instance.config.get("name") == "ExecFailUnknown":
            raise InterruptedError(
                "Some other unexpected error"
            )  # Use a less common exception
        return {"result": "success", "details": kwargs}

    @staticmethod
    def mock_error_factory(name: str, msg: str) -> Dict[str, Any]:
        return {"error_for": name, "message": msg, "status": "failed"}

    # --- Tests for _execute_component ---

    # @pytest.mark.asyncio # Removed
    async def test_execute_component_success(self, facade_instance: ExecutionFacade):
        """Test successful execution path of _execute_component."""
        result = await facade_instance._execute_component(
            component_type="TestComponent",
            component_name="Success",
            config_lookup=self.mock_config_lookup,
            executor_setup=self.mock_executor_setup,
            execution_func=self.mock_execution_func,
            error_structure_factory=self.mock_error_factory,
            arg1="value1",
            arg2=123,
        )

        assert result == {
            "result": "success",
            "details": {"arg1": "value1", "arg2": 123},
        }

    # @pytest.mark.asyncio # Removed
    async def test_execute_component_config_not_found(
        self, facade_instance: ExecutionFacade
    ):
        """Test _execute_component when config lookup raises KeyError."""
        result = await facade_instance._execute_component(
            component_type="TestComponent",
            component_name="NotFound",  # Triggers KeyError in mock_config_lookup
            config_lookup=self.mock_config_lookup,
            executor_setup=self.mock_executor_setup,
            execution_func=self.mock_execution_func,
            error_structure_factory=self.mock_error_factory,
        )

        assert result == {
            "error_for": "NotFound",
            "message": "Configuration error: TestComponent 'NotFound' not found.",
            "status": "failed",
        }

    # @pytest.mark.asyncio # Removed
    async def test_execute_component_config_lookup_error(
        self, facade_instance: ExecutionFacade
    ):
        """Test _execute_component handling unexpected config lookup errors."""
        result = await facade_instance._execute_component(
            component_type="TestComponent",
            component_name="LookupError",  # Triggers ValueError in mock_config_lookup
            config_lookup=self.mock_config_lookup,
            executor_setup=self.mock_executor_setup,
            execution_func=self.mock_execution_func,
            error_structure_factory=self.mock_error_factory,
        )

        assert result == {
            "error_for": "LookupError",
            "message": "Unexpected error retrieving config for TestComponent 'LookupError': Some lookup error",
            "status": "failed",
        }

    # @pytest.mark.asyncio # Removed
    async def test_execute_component_setup_error(
        self, facade_instance: ExecutionFacade
    ):
        """Test _execute_component when executor setup fails."""
        result = await facade_instance._execute_component(
            component_type="TestComponent",
            component_name="SetupFail",  # Triggers TypeError in mock_executor_setup
            config_lookup=self.mock_config_lookup,
            executor_setup=self.mock_executor_setup,
            execution_func=self.mock_execution_func,
            error_structure_factory=self.mock_error_factory,
        )

        assert result == {
            "error_for": "SetupFail",
            "message": "Initialization error for TestComponent 'SetupFail': Executor setup failed",
            "status": "failed",
        }

    # @pytest.mark.asyncio # Removed
    async def test_execute_component_execution_known_error(
        self, facade_instance: ExecutionFacade
    ):
        """Test _execute_component when execution raises a known, re-raised error."""
        with pytest.raises(FileNotFoundError, match="Known execution error"):
            await facade_instance._execute_component(
                component_type="TestComponent",
                component_name="ExecFailKnown",  # Triggers FileNotFoundError in mock_execution_func
                config_lookup=self.mock_config_lookup,
                executor_setup=self.mock_executor_setup,
                execution_func=self.mock_execution_func,
                error_structure_factory=self.mock_error_factory,
            )

    # @pytest.mark.asyncio # Removed
    async def test_execute_component_execution_unknown_error(
        self, facade_instance: ExecutionFacade
    ):
        """Test _execute_component when execution raises an unexpected error."""
        result = await facade_instance._execute_component(
            component_type="TestComponent",
            component_name="ExecFailUnknown",  # Triggers InterruptedError in mock_execution_func
            config_lookup=self.mock_config_lookup,
            executor_setup=self.mock_executor_setup,
            execution_func=self.mock_execution_func,
            error_structure_factory=self.mock_error_factory,
        )

        assert result == {
            "error_for": "ExecFailUnknown",
            "message": "Unexpected runtime error during TestComponent 'ExecFailUnknown' execution: Some other unexpected error",
            "status": "failed",
        }

    # TODO: Add tests for the public run_agent, run_simple_workflow, run_custom_workflow
    # These tests would mainly verify that the correct arguments are passed down
    # to _execute_component.
