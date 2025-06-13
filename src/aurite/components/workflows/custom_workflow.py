"""
Executor for Custom Python-based Workflows.
"""

import logging
import importlib.util
import inspect
from typing import Any, TYPE_CHECKING, Optional  # Added Optional

# Relative imports assuming this file is in src/workflows/
from ...config.config_models import CustomWorkflowConfig  # Updated import path

# MCPHost is still needed for the __init__ method
# from ..config import PROJECT_ROOT_DIR  # Import project root for path validation # Removed: Path validation handled by Aurite/ProjectManager

# Type hint for ExecutionFacade
if TYPE_CHECKING:
    from ...execution.facade import ExecutionFacade
    # MCPHost type hint is no longer needed here for the execute signature

logger = logging.getLogger(__name__)


class CustomWorkflowExecutor:
    """
    Executes a custom Python workflow defined by a CustomWorkflowConfig.
    Handles dynamic loading and execution of the workflow class.
    """

    # Removed host_instance from __init__ as it's passed via facade in execute
    def __init__(self, config: CustomWorkflowConfig):
        """
        Initializes the CustomWorkflowExecutor.

        Args:
            config: The configuration for the specific custom workflow to execute.
        """
        if not isinstance(config, CustomWorkflowConfig):
            raise TypeError("config must be an instance of CustomWorkflowConfig")

        self.config = config
        # self._host = host_instance # Removed host instance storage
        logger.debug(
            f"CustomWorkflowExecutor initialized for workflow: {self.config.name}"
        )

        methods_to_load = [
            {
                "name": "execute_workflow",
                "is_async": True,
                "optional": False,
            },
            {
                "name": "get_input_type",
                "is_async": False,
                "optional": True,
            },
            {
                "name": "get_output_type",
                "is_async": False,
                "optional": True,
            },
        ]

        self.methods = self._load_methods(methods_to_load)

    # Changed signature to accept executor (ExecutionFacade) and session_id
    async def execute(
        self,
        initial_input: Any,
        executor: "ExecutionFacade",
        session_id: Optional[str] = None,
    ) -> Any:  # Added session_id
        """
        Dynamically loads and executes the configured custom workflow.

        Args:
            initial_input: The input data to pass to the workflow's execute method.
            executor: The ExecutionFacade instance, passed to the custom workflow
                      to allow it to call other components.
            session_id: Optional session ID for context/history tracking.

        Returns:
            The result returned by the custom workflow's execute_workflow method.

        Raises:
            FileNotFoundError: If the configured module path does not exist.
            PermissionError: If the module path is outside the project directory.
            ImportError: If the module cannot be imported.
            AttributeError: If the specified class or 'execute_workflow' method is not found.
            TypeError: If the 'execute_workflow' method is not async or class instantiation fails.
            RuntimeError: Wraps exceptions raised during the workflow's execution.
        """
        try:
            workflow_name = self.config.name

            logger.debug(  # Already DEBUG
                "Calling 'execute_workflow', passing ExecutionFacade."
            )
            # Pass the ExecutionFacade instance as the 'executor' argument and session_id
            result = await self.methods.get("execute_workflow")(
                initial_input=initial_input,
                executor=executor,
                session_id=session_id,  # Pass session_id
            )

            logger.info(  # Keep final success as INFO
                f"Custom workflow '{workflow_name}' execution finished successfully."
            )
            return result

        except (
            FileNotFoundError,
            PermissionError,
            ImportError,
            AttributeError,
            TypeError,
        ) as e:
            # Catch specific setup/loading errors and re-raise
            logger.error(
                f"Error setting up or loading custom workflow '{workflow_name}': {e}",
                exc_info=True,  # Include traceback for setup errors
            )
            raise e
        except Exception as e:
            # Catch errors *during* the workflow's own execution
            logger.error(
                f"Exception raised within custom workflow '{workflow_name}' execution: {e}",
                exc_info=True,  # Include traceback for runtime errors within the workflow
            )
            # Wrap internal workflow errors in a RuntimeError for consistent handling upstream
            raise RuntimeError(
                f"Exception during custom workflow '{workflow_name}' execution: {e}"
            ) from e

    async def get_input_type(self):
        """Gets the input type of the custom workflow's execute method, if the get_input_type method is defined

        Returns:
            The type returned, or None"""

        if "get_input_type" in self.methods:
            return self.methods.get("get_input_type")()

        return None

    async def get_output_type(self):
        """Gets the output type of the custom workflow's execute method, if the get_output_type method is defined

        Returns:
            The type returned, or None"""

        if "get_output_type" in self.methods:
            return self.methods.get("get_output_type")()

        return None

    def _load_methods(self, methods_to_load):
        """
        Dynamically loads the methods

        Args:
            methods_to_load: List of method objects with "name", "is_async", and "optional" attributes

        Raises:
            FileNotFoundError: If the configured module path does not exist.
            PermissionError: If the module path is outside the project directory.
            ImportError: If the module cannot be imported.
            AttributeError: If the specified class or 'execute_workflow' method is not found.
            TypeError: If the 'execute_workflow' method is not async or class instantiation fails.
            RuntimeError: Wraps exceptions raised during the workflow's execution.
        """
        workflow_name = self.config.name
        module_path = self.config.module_path
        class_name = self.config.class_name
        logger.info(
            f"Loading methods for workflow: {workflow_name}"
        )  # Keep start as INFO
        logger.debug(f"Config: path={module_path}, class={class_name}")  # Already DEBUG

        try:
            # 1. Security Check & Path Validation
            # The PROJECT_ROOT_DIR check is removed.
            # module_path is expected to be an absolute path, validated by ProjectManager/Aurite
            # against current_project_root before this executor is called.

            if not module_path.exists():
                logger.error(f"Custom workflow module file not found: {module_path}")
                raise FileNotFoundError(
                    f"Custom workflow module file not found: {module_path}"
                )

            # 2. Dynamic Import
            spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not create module spec for {module_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.debug(f"Dynamically imported module: {module_path}")  # Already DEBUG

            # 3. Get Class
            WorkflowClass = getattr(module, class_name, None)
            if WorkflowClass is None:
                logger.error(f"Class '{class_name}' not found in module {module_path}")
                raise AttributeError(
                    f"Class '{class_name}' not found in module {module_path}"
                )

            # 4. Instantiate Workflow Class
            try:
                workflow_instance = WorkflowClass()
                logger.debug(
                    f"Instantiated workflow class '{class_name}'"
                )  # Already DEBUG
            except Exception as init_err:
                logger.error(
                    f"Error instantiating workflow class '{class_name}' from {module_path}: {init_err}",
                    exc_info=True,
                )
                raise TypeError(
                    f"Failed to instantiate workflow class '{class_name}': {init_err}"
                ) from init_err

            loaded_methods = {}
            for method in methods_to_load:
                method_name = method.get("name")
                # 5. Check for the method name and signature
                if not hasattr(workflow_instance, method_name):
                    if method.get("optional"):
                        logger.warning(
                            f"Method '{method_name}' not found in class '{class_name}' from {module_path}. Skipping"
                        )
                        continue
                    else:
                        logger.error(
                            f"Method '{method_name}' not found in class '{class_name}' from {module_path}"
                        )
                        raise AttributeError(
                            f"Method '{method_name}' not found in class '{class_name}'"
                        )

                execute_method = getattr(workflow_instance, method_name)
                if not callable(execute_method):
                    logger.error(
                        f"Attribute '{method_name}' is not callable in class '{class_name}' from {module_path}"
                    )
                    raise AttributeError(
                        f"Attribute '{method_name}' is not callable in class '{class_name}'"
                    )

                # Check if async
                is_async = method.get("is_async")
                is_coroutine = inspect.iscoroutinefunction(execute_method)
                if is_coroutine != is_async:
                    logger.error(
                        f"Method '{method_name}' in class '{class_name}' from {module_path} must {'not ' if is_coroutine else ''}be async."
                    )
                    raise TypeError(
                        f"Method '{method_name}' must {'not ' if is_coroutine else ''}be async."
                    )

                # 6. Store the method
                loaded_methods[method.get("name")] = execute_method

            logger.info(  # Keep final success as INFO
                f"Finished loading methods for workflow: {workflow_name}"
            )
            return loaded_methods

        except (
            FileNotFoundError,
            PermissionError,
            ImportError,
            AttributeError,
            TypeError,
        ) as e:
            # Catch specific setup/loading errors and re-raise
            logger.error(
                f"Error setting up or loading methods for custom workflow '{workflow_name}': {e}",
                exc_info=True,  # Include traceback for setup errors
            )
            raise e
        except Exception as e:
            # Catch errors *during* the workflow's own execution
            logger.error(
                f"Exception raised while loading methods for custom workflow '{workflow_name}': {e}",
                exc_info=True,  # Include traceback for runtime errors within the workflow
            )
            # Wrap internal workflow errors in a RuntimeError for consistent handling upstream
            raise RuntimeError(
                f"Exception raised while loading methods for custom workflow '{workflow_name}': {e}"
            ) from e
