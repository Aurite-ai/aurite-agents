"""
Unit tests for the CustomWorkflowExecutor.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

# Mark all tests in this module
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from src.workflows.custom_workflow import CustomWorkflowExecutor
from src.host.models import CustomWorkflowConfig
from src.execution.facade import ExecutionFacade  # Needed for type hint

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
        """
        Test successful initialization of CustomWorkflowExecutor.
        """
        print("\n--- Running Test: test_custom_executor_init_success ---")
        try:
            # Initialization doesn't require host instance anymore
            executor = CustomWorkflowExecutor(
                config=sample_custom_workflow_config,
            )
            assert executor.config == sample_custom_workflow_config
            print("Assertions passed.")
        except Exception as e:
            pytest.fail(f"CustomWorkflowExecutor initialization failed: {e}")

        print("--- Test Finished: test_custom_executor_init_success ---")

    @pytest.mark.asyncio
    async def test_custom_executor_execute_success(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """
        Test successful execution of a custom workflow.
        Mocks file existence, module import, class instantiation, and method execution.
        """
        print("\n--- Running Test: test_custom_executor_execute_success ---")
        initial_input = {"start": "data"}
        expected_result = {"final_status": "custom_completed"}
        mock_facade = Mock(spec=ExecutionFacade)  # Facade is passed to execute_workflow

        # --- Mock dynamic loading and execution ---
        # 1. Mock Path.exists
        with patch("pathlib.Path.exists", return_value=True) as mock_exists:
            # 2. Mock importlib functions
            mock_spec = Mock()
            mock_module = Mock()
            # Mock the class within the module
            mock_workflow_class = Mock()
            # Mock the instance of the class
            mock_workflow_instance = Mock()
            # Mock the execute_workflow method on the instance (needs to be async)
            mock_workflow_instance.execute_workflow = AsyncMock(
                return_value=expected_result
            )
            # Set the mocked class on the mocked module
            setattr(
                mock_module,
                sample_custom_workflow_config.class_name,
                mock_workflow_class,
            )
            # Configure the mocked class to return the mocked instance
            mock_workflow_class.return_value = mock_workflow_instance

            with (
                patch(
                    "importlib.util.spec_from_file_location", return_value=mock_spec
                ) as mock_spec_from_file,
                patch(
                    "importlib.util.module_from_spec", return_value=mock_module
                ) as mock_module_from_spec,
                patch.object(mock_spec.loader, "exec_module") as mock_exec_module,
            ):  # Need to patch exec_module
                executor = CustomWorkflowExecutor(
                    config=sample_custom_workflow_config,
                )

                # --- Execute the workflow ---
                # Pass the mock facade instance
                result = await executor.execute(
                    initial_input=initial_input, executor=mock_facade
                )

                print(f"Execution Result: {result}")

                # --- Assertions ---
                mock_exists.assert_called_once()
                # Module name should be the file stem
                expected_module_name = sample_custom_workflow_config.module_path.stem
                mock_spec_from_file.assert_called_once_with(
                    expected_module_name, sample_custom_workflow_config.module_path
                )
                mock_module_from_spec.assert_called_once_with(mock_spec)
                mock_exec_module.assert_called_once_with(mock_module)
                # Check class instantiation
                mock_workflow_class.assert_called_once_with()
                # Check execute_workflow call
                mock_workflow_instance.execute_workflow.assert_awaited_once_with(
                    initial_input=initial_input,
                    executor=mock_facade,  # Check facade was passed
                )

                # Check final result
                assert result == expected_result

                print("Assertions passed.")

        print("--- Test Finished: test_custom_executor_execute_success ---")

    @pytest.mark.asyncio
    async def test_custom_executor_module_not_found(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """Test execution fails when the module file does not exist."""
        print("\n--- Running Test: test_custom_executor_module_not_found ---")
        initial_input = {"start": "data"}
        mock_facade = Mock(spec=ExecutionFacade)

        # Mock Path.exists to return False
        with patch("pathlib.Path.exists", return_value=False) as mock_exists:
            executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)
            # Assert that FileNotFoundError is raised
            with pytest.raises(FileNotFoundError) as excinfo:
                await executor.execute(
                    initial_input=initial_input, executor=mock_facade
                )

            # Assertions
            mock_exists.assert_called_once()
            # Correct the assertion string to match the actual error message
            assert "Custom workflow module file not found" in str(excinfo.value)
            assert str(sample_custom_workflow_config.module_path) in str(excinfo.value)
            print(f"Caught expected exception: {excinfo.value}")

        print("--- Test Finished: test_custom_executor_module_not_found ---")

    @pytest.mark.asyncio
    async def test_custom_executor_class_not_found(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """Test execution fails when the class is not found in the loaded module."""
        print("\n--- Running Test: test_custom_executor_class_not_found ---")
        initial_input = {"start": "data"}
        mock_facade = Mock(spec=ExecutionFacade)

        with patch("pathlib.Path.exists", return_value=True):
            mock_spec = Mock()
            # Ensure the mock module does *not* have the class attribute
            mock_module = Mock(spec=[])  # spec=[] ensures it has no attributes
            with (
                patch("importlib.util.spec_from_file_location", return_value=mock_spec),
                patch("importlib.util.module_from_spec", return_value=mock_module),
                patch.object(mock_spec.loader, "exec_module"),
            ):
                executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)
                # Assert that AttributeError is raised because the class is missing
                with pytest.raises(AttributeError) as excinfo:
                    await executor.execute(
                        initial_input=initial_input, executor=mock_facade
                    )

                # Assertions on the exception
                # Correct the assertion string to match the actual error message format
                assert (
                    f"Class '{sample_custom_workflow_config.class_name}' not found in module"
                    in str(excinfo.value)
                )
                assert str(sample_custom_workflow_config.module_path) in str(
                    excinfo.value
                )
                print(f"Caught expected exception: {excinfo.value}")

        print("--- Test Finished: test_custom_executor_class_not_found ---")

    @pytest.mark.asyncio
    async def test_custom_executor_execute_workflow_error(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """Test execution fails when the execute_workflow method raises an exception."""
        print("\n--- Running Test: test_custom_executor_execute_workflow_error ---")
        initial_input = {"start": "data"}
        mock_facade = Mock(spec=ExecutionFacade)
        execution_error = ValueError("Error inside custom workflow logic")

        with patch("pathlib.Path.exists", return_value=True):
            mock_spec = Mock()
            mock_module = Mock()
            mock_workflow_class = Mock()
            mock_workflow_instance = Mock()
            # Mock execute_workflow to raise an error
            mock_workflow_instance.execute_workflow = AsyncMock(
                side_effect=execution_error
            )
            setattr(
                mock_module,
                sample_custom_workflow_config.class_name,
                mock_workflow_class,
            )
            mock_workflow_class.return_value = mock_workflow_instance

            with (
                patch("importlib.util.spec_from_file_location", return_value=mock_spec),
                patch("importlib.util.module_from_spec", return_value=mock_module),
                patch.object(mock_spec.loader, "exec_module"),
            ):
                executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)
                # Assert that RuntimeError is raised (wrapping the original error)
                with pytest.raises(RuntimeError) as excinfo:
                    await executor.execute(
                        initial_input=initial_input, executor=mock_facade
                    )

                # Assertions on the exception
                mock_workflow_instance.execute_workflow.assert_awaited_once()  # Ensure it was called
                assert "Exception during custom workflow" in str(excinfo.value)
                assert sample_custom_workflow_config.name in str(excinfo.value)
                assert str(execution_error) in str(
                    excinfo.value
                )  # Check original error is mentioned
                print(f"Caught expected exception: {excinfo.value}")

        print("--- Test Finished: test_custom_executor_execute_workflow_error ---")

    @pytest.mark.asyncio
    async def test_custom_executor_execute_method_not_found(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """Test execution fails when the execute_workflow method is not found on the instance."""
        print("\n--- Running Test: test_custom_executor_execute_method_not_found ---")
        initial_input = {"start": "data"}
        mock_facade = Mock(spec=ExecutionFacade)

        with patch("pathlib.Path.exists", return_value=True):
            mock_spec = Mock()
            mock_module = Mock()
            mock_workflow_class = Mock()
            # Create an instance that *lacks* the execute_workflow method
            mock_workflow_instance = Mock(
                spec=[]
            )  # spec=[] ensures no methods initially
            setattr(
                mock_module,
                sample_custom_workflow_config.class_name,
                mock_workflow_class,
            )
            mock_workflow_class.return_value = mock_workflow_instance

            with (
                patch("importlib.util.spec_from_file_location", return_value=mock_spec),
                patch("importlib.util.module_from_spec", return_value=mock_module),
                patch.object(mock_spec.loader, "exec_module"),
            ):
                executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)
                # Assert that AttributeError is raised
                with pytest.raises(AttributeError) as excinfo:
                    await executor.execute(
                        initial_input=initial_input, executor=mock_facade
                    )

                # Assertions on the exception
                assert "Method 'execute_workflow' not found" in str(excinfo.value)
                assert sample_custom_workflow_config.class_name in str(excinfo.value)
                print(f"Caught expected exception: {excinfo.value}")

        print("--- Test Finished: test_custom_executor_execute_method_not_found ---")

    @pytest.mark.asyncio
    async def test_custom_executor_execute_method_not_async(
        self,
        sample_custom_workflow_config: CustomWorkflowConfig,
    ):
        """Test execution fails when the execute_workflow method is not async."""
        print("\n--- Running Test: test_custom_executor_execute_method_not_async ---")
        initial_input = {"start": "data"}
        mock_facade = Mock(spec=ExecutionFacade)

        with patch("pathlib.Path.exists", return_value=True):
            mock_spec = Mock()
            mock_module = Mock()
            mock_workflow_class = Mock()
            mock_workflow_instance = Mock()

            # Define execute_workflow as a regular function, not async
            def sync_execute_workflow(initial_input, executor):
                return {"result": "sync"}

            mock_workflow_instance.execute_workflow = sync_execute_workflow
            setattr(
                mock_module,
                sample_custom_workflow_config.class_name,
                mock_workflow_class,
            )
            mock_workflow_class.return_value = mock_workflow_instance

            with (
                patch("importlib.util.spec_from_file_location", return_value=mock_spec),
                patch("importlib.util.module_from_spec", return_value=mock_module),
                patch.object(mock_spec.loader, "exec_module"),
            ):
                executor = CustomWorkflowExecutor(config=sample_custom_workflow_config)
                # Assert that TypeError is raised
                with pytest.raises(TypeError) as excinfo:
                    await executor.execute(
                        initial_input=initial_input, executor=mock_facade
                    )

                # Assertions on the exception
                assert "Method 'execute_workflow' must be async" in str(excinfo.value)
                print(f"Caught expected exception: {excinfo.value}")

        print("--- Test Finished: test_custom_executor_execute_method_not_async ---")
