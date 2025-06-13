"""
Unit tests for the CustomWorkflowExecutor.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

# Mark all tests in this module
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from aurite.components.workflows.custom_workflow import CustomWorkflowExecutor
from aurite.config.config_models import CustomWorkflowConfig
from aurite.execution.facade import ExecutionFacade  # Needed for type hint

# Import shared fixtures

# --- Fixtures ---

# Removed local sample_custom_workflow_config - using shared fixture

# --- Test Class ---


class TestCustomWorkflowExecutorUnit:
    """Unit tests for the CustomWorkflowExecutor."""

    def test_custom_executor_init_success(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """Test successful initialization of CustomWorkflowExecutor."""
        print("\n--- Running Test: test_custom_executor_init_success ---")

        # Mock successful method loading
        mock_methods = {
            "execute_workflow": AsyncMock(),
            "get_input_type": Mock(),
            "get_output_type": Mock(),
        }

        with patch.object(
            CustomWorkflowExecutor, "_load_methods", return_value=mock_methods
        ) as mock_load:
            executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)

            assert executor.config == sample_custom_workflow_config
            assert executor.methods == mock_methods
            mock_load.assert_called_once()
            print("Assertions passed.")

    @pytest.mark.asyncio
    async def test_custom_executor_execute_success(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """Test successful execution of a custom workflow."""
        print("\n--- Running Test: test_custom_executor_execute_success ---")

        initial_input = {"start": "data"}
        session_id = "custom_unit_session_1"
        expected_result = {"final_status": "custom_completed"}
        mock_facade = Mock(spec=ExecutionFacade)

        # Create mock execute_workflow method
        mock_execute = AsyncMock(return_value=expected_result)
        mock_methods = {
            "execute_workflow": mock_execute,
            "get_input_type": Mock(),
            "get_output_type": Mock(),
        }

        with patch.object(
            CustomWorkflowExecutor, "_load_methods", return_value=mock_methods
        ):
            executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)

            result = await executor.execute(
                initial_input=initial_input,
                executor=mock_facade,
                session_id=session_id,
            )

            mock_execute.assert_awaited_once_with(
                initial_input=initial_input,
                executor=mock_facade,
                session_id=session_id,
            )
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_custom_executor_module_not_found(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """Test execution fails when the module file does not exist."""
        print("\n--- Running Test: test_custom_executor_module_not_found ---")

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError) as excinfo:
                executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)

            assert "Custom workflow module file not found" in str(excinfo.value)
            assert str(sample_custom_workflow_config.module_path) in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_custom_executor_class_not_found(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        print("\n--- Running Test: test_custom_executor_class_not_found ---")

        mock_module = Mock()
        # Instead of __getattr__, set the class attribute to None
        setattr(mock_module, sample_custom_workflow_config.class_name, None)

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.resolve", return_value="/valid/path"),
            patch("importlib.util.spec_from_file_location") as mock_spec,
            patch("importlib.util.module_from_spec", return_value=mock_module),
        ):
            mock_spec.return_value = Mock(loader=Mock())

            with pytest.raises(AttributeError) as excinfo:
                executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)

            assert (
                f"Class '{sample_custom_workflow_config.class_name}' not found in module"
                in str(excinfo.value)
            )
            assert str(sample_custom_workflow_config.module_path) in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_custom_executor_execute_method_not_found(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        print("\n--- Running Test: test_custom_executor_execute_method_not_found ---")

        mock_class = Mock()
        mock_instance = Mock()
        mock_instance.execute_workflow = None
        mock_class.return_value = mock_instance

        mock_module = Mock()
        setattr(mock_module, sample_custom_workflow_config.class_name, mock_class)

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.resolve", return_value="/valid/path"),
            patch("importlib.util.spec_from_file_location") as mock_spec,
            patch("importlib.util.module_from_spec", return_value=mock_module),
        ):
            mock_spec.return_value = Mock(loader=Mock())

            with pytest.raises(AttributeError) as excinfo:
                executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)

            assert (
                "Attribute 'execute_workflow' is not callable in class 'MyCustomWorkflow'"
                in str(excinfo.value)
            )
            assert sample_custom_workflow_config.class_name in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_custom_executor_execute_method_not_async(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        print("\n--- Running Test: test_custom_executor_execute_method_not_async ---")

        def sync_execute_workflow(*args, **kwargs):
            return {"result": "sync"}

        mock_class = Mock()
        mock_instance = Mock()
        mock_instance.execute_workflow = sync_execute_workflow
        mock_class.return_value = mock_instance

        mock_module = Mock()
        setattr(mock_module, sample_custom_workflow_config.class_name, mock_class)

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.resolve", return_value="/valid/path"),
            patch("importlib.util.spec_from_file_location") as mock_spec,
            patch("importlib.util.module_from_spec", return_value=mock_module),
        ):
            mock_spec.return_value = Mock(loader=Mock())

            with pytest.raises(TypeError) as excinfo:
                executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)

            assert "Method 'execute_workflow' must be async" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_input_type(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """Test get_input_type with defined method."""
        expected_type = dict
        mock_get_input = Mock(return_value=expected_type)
        mock_methods = {
            "execute_workflow": AsyncMock(),
            "get_input_type": mock_get_input,
            "get_output_type": Mock(),
        }

        with patch.object(
            CustomWorkflowExecutor, "_load_methods", return_value=mock_methods
        ):
            executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)
            result = await executor.get_input_type()
            assert result == expected_type
            mock_get_input.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_output_type(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """Test get_output_type with defined method."""
        expected_type = str
        mock_get_output = Mock(return_value=expected_type)
        mock_methods = {
            "execute_workflow": AsyncMock(),
            "get_input_type": Mock(),
            "get_output_type": mock_get_output,
        }

        with patch.object(
            CustomWorkflowExecutor, "_load_methods", return_value=mock_methods
        ):
            executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)
            result = await executor.get_output_type()
            assert result == expected_type
            mock_get_output.assert_called_once()
