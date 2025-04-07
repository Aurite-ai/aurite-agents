"""
Unit tests for CustomWorkflowManager methods.
(Adapted from tests/host/test_host_custom_workflows.py)
"""

import pytest
import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Use relative imports assuming tests run from aurite-mcp root
from src.workflows.manager import CustomWorkflowManager
from src.host.models import CustomWorkflowConfig
from src.host.host import MCPHost  # Needed for type hint in execute method
from src.config import PROJECT_ROOT_DIR  # Import project root for path checks

# --- Test Data (Copied and adapted from original host test) ---

MOCK_CUSTOM_WF_NAME = "MyTestCustomWF"
MOCK_CUSTOM_WF_CONFIG = CustomWorkflowConfig(
    name=MOCK_CUSTOM_WF_NAME,
    module_path=PROJECT_ROOT_DIR / "tests/fixtures/custom_workflows/valid_workflow.py",
    class_name="ValidWorkflowClass",
    description="A valid custom workflow for testing",
)

MOCK_CUSTOM_WF_CONFIG_NONEXISTENT_PATH = CustomWorkflowConfig(
    name="NonExistentPathWF",
    module_path=PROJECT_ROOT_DIR / "tests/fixtures/custom_workflows/non_existent.py",
    class_name="NonExistentClass",
)

MOCK_CUSTOM_WF_CONFIG_OUTSIDE_PROJECT = CustomWorkflowConfig(
    name="OutsideProjectWF",
    module_path=Path("/etc/passwd"),  # Example outside project
    class_name="MaliciousClass",
)


MOCK_CUSTOM_WF_CONFIG_NO_CLASS = CustomWorkflowConfig(
    name="NoClassWF",
    module_path=PROJECT_ROOT_DIR / "tests/fixtures/custom_workflows/valid_workflow.py",
    class_name="NonExistentClass",  # Class not in the file
)

MOCK_CUSTOM_WF_CONFIG_NO_METHOD = CustomWorkflowConfig(
    name="NoMethodWF",
    module_path=PROJECT_ROOT_DIR
    / "tests/fixtures/custom_workflows/no_method_workflow.py",
    class_name="NoMethodWorkflowClass",  # Class exists, method doesn't
)

MOCK_CUSTOM_WF_CONFIG_SYNC_METHOD = CustomWorkflowConfig(
    name="SyncMethodWF",
    module_path=PROJECT_ROOT_DIR / "tests/fixtures/custom_workflows/sync_workflow.py",
    class_name="SyncWorkflowClass",  # Class exists, method is sync
)


MOCK_CUSTOM_WORKFLOW_CONFIGS = {
    MOCK_CUSTOM_WF_NAME: MOCK_CUSTOM_WF_CONFIG,
    "NonExistentPathWF": MOCK_CUSTOM_WF_CONFIG_NONEXISTENT_PATH,
    "OutsideProjectWF": MOCK_CUSTOM_WF_CONFIG_OUTSIDE_PROJECT,
    "NoClassWF": MOCK_CUSTOM_WF_CONFIG_NO_CLASS,
    "NoMethodWF": MOCK_CUSTOM_WF_CONFIG_NO_METHOD,
    "SyncMethodWF": MOCK_CUSTOM_WF_CONFIG_SYNC_METHOD,
}

# --- Fixtures ---


@pytest.fixture
def workflow_manager() -> CustomWorkflowManager:
    """Provides a CustomWorkflowManager instance initialized with mock configs."""
    return CustomWorkflowManager(custom_workflow_configs=MOCK_CUSTOM_WORKFLOW_CONFIGS)


@pytest.fixture
def mock_mcp_host_for_manager() -> MagicMock:
    """Provides a basic mock MCPHost instance for passing to execute_custom_workflow."""
    return MagicMock(spec=MCPHost)


# --- Test Class ---


@pytest.mark.unit
class TestWorkflowManager:
    """Tests CustomWorkflowManager methods."""

    def test_get_custom_workflow_config_success(self, workflow_manager):
        """Test retrieving an existing custom workflow config."""
        config = workflow_manager.get_custom_workflow_config(MOCK_CUSTOM_WF_NAME)
        assert config == MOCK_CUSTOM_WF_CONFIG

    def test_get_custom_workflow_config_not_found(self, workflow_manager):
        """Test retrieving a non-existent custom workflow config raises KeyError."""
        with pytest.raises(KeyError, match="Custom workflow configuration not found"):
            workflow_manager.get_custom_workflow_config("NotFoundWF")

    @pytest.mark.asyncio
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.exists", return_value=True)  # Mock path exists
    async def test_execute_custom_workflow_success(
        self,
        mock_path_exists,
        mock_module_from_spec,
        mock_spec_from_file_location,
        workflow_manager,
        mock_mcp_host_for_manager,
    ):
        """Test successful execution of a custom workflow."""
        workflow_name = MOCK_CUSTOM_WF_NAME
        initial_input = {"data": "test"}
        expected_result = {"status": "ok", "received": initial_input}

        # Mock the dynamic import process
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec.loader.exec_module = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_module = MagicMock()
        mock_workflow_instance = MagicMock()
        # Mock the async execute_workflow method
        mock_execute_method = AsyncMock(return_value=expected_result)
        mock_workflow_instance.execute_workflow = mock_execute_method

        # Mock the class instantiation
        MockWorkflowClass = MagicMock(return_value=mock_workflow_instance)
        setattr(mock_module, MOCK_CUSTOM_WF_CONFIG.class_name, MockWorkflowClass)
        mock_module_from_spec.return_value = mock_module

        # Execute using the manager
        result = await workflow_manager.execute_custom_workflow(
            workflow_name, initial_input, mock_mcp_host_for_manager
        )

        # Assertions
        assert result == expected_result
        mock_spec_from_file_location.assert_called_once_with(
            MOCK_CUSTOM_WF_CONFIG.module_path.stem, MOCK_CUSTOM_WF_CONFIG.module_path
        )
        mock_module_from_spec.assert_called_once_with(mock_spec)
        mock_spec.loader.exec_module.assert_called_once_with(mock_module)
        MockWorkflowClass.assert_called_once_with()  # Check instantiation
        # Check execute_workflow was called with the mock host instance
        mock_execute_method.assert_awaited_once_with(
            initial_input=initial_input, host_instance=mock_mcp_host_for_manager
        )
        mock_path_exists.assert_called_once()  # Path existence checked

    @pytest.mark.asyncio
    async def test_execute_custom_workflow_config_not_found(
        self, workflow_manager, mock_mcp_host_for_manager
    ):
        """Test execution fails if workflow config doesn't exist."""
        # Expect KeyError directly from get_custom_workflow_config
        with pytest.raises(KeyError, match="Custom workflow configuration not found"):
            await workflow_manager.execute_custom_workflow(
                "NotFoundWF", {}, mock_mcp_host_for_manager
            )

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists", return_value=False)  # Mock path *not* existing
    async def test_execute_custom_workflow_file_not_found(
        self, mock_path_exists, workflow_manager, mock_mcp_host_for_manager
    ):
        """Test execution fails if module file doesn't exist."""
        workflow_name = (
            "NonExistentPathWF"  # Uses MOCK_CUSTOM_WF_CONFIG_NONEXISTENT_PATH
        )
        with pytest.raises(
            FileNotFoundError, match="Custom workflow module file not found"
        ):
            await workflow_manager.execute_custom_workflow(
                workflow_name, {}, mock_mcp_host_for_manager
            )
        mock_path_exists.assert_called_once()

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists", return_value=True)
    async def test_execute_custom_workflow_outside_project(
        self, mock_path_exists, workflow_manager, mock_mcp_host_for_manager
    ):
        """Test execution fails if module path is outside project directory."""
        workflow_name = "OutsideProjectWF"  # Uses MOCK_CUSTOM_WF_CONFIG_OUTSIDE_PROJECT
        with pytest.raises(
            PermissionError,
            match="Custom workflow path is outside the project directory",
        ):
            await workflow_manager.execute_custom_workflow(
                workflow_name, {}, mock_mcp_host_for_manager
            )
        # Path.exists should not be called if the initial security check fails
        # mock_path_exists.assert_not_called() # This depends on implementation order

    @pytest.mark.asyncio
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.exists", return_value=True)
    async def test_execute_custom_workflow_class_not_found(
        self,
        mock_path_exists,
        mock_module_from_spec,
        mock_spec_from_file_location,
        workflow_manager,
        mock_mcp_host_for_manager,
    ):
        """Test execution fails if the specified class is not in the module."""
        workflow_name = "NoClassWF"  # Uses MOCK_CUSTOM_WF_CONFIG_NO_CLASS

        # Mock import process up to module loading
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec.loader.exec_module = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec
        mock_module = MagicMock()
        # Explicitly set the attribute for the non-existent class to None
        # so that hasattr(module, class_name) returns False.
        setattr(mock_module, MOCK_CUSTOM_WF_CONFIG_NO_CLASS.class_name, None)
        mock_module_from_spec.return_value = mock_module

        with pytest.raises(AttributeError, match="Class 'NonExistentClass' not found"):
            await workflow_manager.execute_custom_workflow(
                workflow_name, {}, mock_mcp_host_for_manager
            )

    @pytest.mark.asyncio
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.exists", return_value=True)
    async def test_execute_custom_workflow_method_not_found(
        self,
        mock_path_exists,
        mock_module_from_spec,
        mock_spec_from_file_location,
        workflow_manager,
        mock_mcp_host_for_manager,
    ):
        """Test execution fails if the instance doesn't have an 'execute_workflow' method."""
        workflow_name = "NoMethodWF"  # Uses MOCK_CUSTOM_WF_CONFIG_NO_METHOD

        # Mock import and instantiation
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec.loader.exec_module = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec
        mock_module = MagicMock()
        mock_workflow_instance = MagicMock()
        # Ensure the method is missing
        del mock_workflow_instance.execute_workflow
        MockWorkflowClass = MagicMock(return_value=mock_workflow_instance)
        setattr(
            mock_module, MOCK_CUSTOM_WF_CONFIG_NO_METHOD.class_name, MockWorkflowClass
        )
        mock_module_from_spec.return_value = mock_module

        with pytest.raises(AttributeError, match="Method 'execute_workflow' not found"):
            await workflow_manager.execute_custom_workflow(
                workflow_name, {}, mock_mcp_host_for_manager
            )

    @pytest.mark.asyncio
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.exists", return_value=True)
    async def test_execute_custom_workflow_method_not_async(
        self,
        mock_path_exists,
        mock_module_from_spec,
        mock_spec_from_file_location,
        workflow_manager,
        mock_mcp_host_for_manager,
    ):
        """Test execution fails if 'execute_workflow' is not async."""
        workflow_name = "SyncMethodWF"  # Uses MOCK_CUSTOM_WF_CONFIG_SYNC_METHOD

        # Mock import and instantiation
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec.loader.exec_module = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec
        mock_module = MagicMock()
        mock_workflow_instance = MagicMock()
        # Set execute_workflow as a *sync* function
        mock_workflow_instance.execute_workflow = (
            lambda initial_input, host_instance: "sync result"
        )
        MockWorkflowClass = MagicMock(return_value=mock_workflow_instance)
        setattr(
            mock_module, MOCK_CUSTOM_WF_CONFIG_SYNC_METHOD.class_name, MockWorkflowClass
        )
        mock_module_from_spec.return_value = mock_module

        with pytest.raises(TypeError, match="Method 'execute_workflow' must be async"):
            await workflow_manager.execute_custom_workflow(
                workflow_name, {}, mock_mcp_host_for_manager
            )

    @pytest.mark.asyncio
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.exists", return_value=True)
    async def test_execute_custom_workflow_internal_exception(
        self,
        mock_path_exists,
        mock_module_from_spec,
        mock_spec_from_file_location,
        workflow_manager,
        mock_mcp_host_for_manager,
    ):
        """Test that exceptions *within* the custom workflow's execute method are caught and wrapped."""
        workflow_name = MOCK_CUSTOM_WF_NAME
        initial_input = {"data": "trigger error"}

        # Mock import and instantiation
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec.loader.exec_module = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec
        mock_module = MagicMock()
        mock_workflow_instance = MagicMock()
        # Mock execute_workflow to raise an exception
        mock_execute_method = AsyncMock(
            side_effect=ValueError("Workflow internal error")
        )
        mock_workflow_instance.execute_workflow = mock_execute_method
        MockWorkflowClass = MagicMock(return_value=mock_workflow_instance)
        setattr(mock_module, MOCK_CUSTOM_WF_CONFIG.class_name, MockWorkflowClass)
        mock_module_from_spec.return_value = mock_module

        # Expect a RuntimeError wrapping the internal ValueError
        with pytest.raises(
            RuntimeError,
            match="Exception during custom workflow execution: Workflow internal error",
        ):
            await workflow_manager.execute_custom_workflow(
                workflow_name, initial_input, mock_mcp_host_for_manager
            )

        mock_execute_method.assert_awaited_once()
