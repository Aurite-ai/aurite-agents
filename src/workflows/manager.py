"""
Manages the loading, validation, and execution of custom Python-based workflows.
"""

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any, Dict

# Use relative imports for models within the same top-level package
from ..host.models import CustomWorkflowConfig
from ..host.host import (
    MCPHost,
)  # Import MCPHost for type hint and potentially PROJECT_ROOT_DIR access

# Assuming PROJECT_ROOT_DIR is defined reliably elsewhere, e.g., in config
# If not, define it here based on this file's location.
# For robustness, let's define it relative to this file:
# src/workflows/manager.py -> src -> project root
PROJECT_ROOT_DIR = Path(__file__).parent.parent.parent.resolve()


logger = logging.getLogger(__name__)


class CustomWorkflowManager:
    """
    Handles the discovery, loading, and execution of custom workflows defined in Python files.
    """

    def __init__(self, custom_workflow_configs: Dict[str, CustomWorkflowConfig]):
        """
        Initializes the manager with loaded custom workflow configurations.

        Args:
            custom_workflow_configs: A dictionary mapping workflow names to their
                                     validated CustomWorkflowConfig objects.
        """
        self._custom_workflow_configs = custom_workflow_configs
        logger.info(
            f"CustomWorkflowManager initialized with {len(self._custom_workflow_configs)} workflow(s)."
        )

    def get_custom_workflow_config(self, workflow_name: str) -> CustomWorkflowConfig:
        """
        Retrieves the configuration for a specific custom workflow by name.

        Args:
            workflow_name: The name of the custom workflow.

        Returns:
            The CustomWorkflowConfig object.

        Raises:
            KeyError: If the workflow_name is not found.
        """
        if workflow_name not in self._custom_workflow_configs:
            logger.error(
                f"Custom workflow configuration not found for name: {workflow_name}"
            )
            raise KeyError(
                f"Custom workflow configuration not found for name: {workflow_name}"
            )
        return self._custom_workflow_configs[workflow_name]

    async def execute_custom_workflow(
        self, workflow_name: str, initial_input: Any, host_instance: MCPHost
    ) -> Any:
        """
        Dynamically loads and executes a configured custom workflow.

        Args:
            workflow_name: The name of the custom workflow to execute.
            initial_input: The input data to pass to the workflow's execute method.
            host_instance: The initialized MCPHost instance, provided to the workflow
                           for accessing agents, tools, etc.

        Returns:
            The result returned by the custom workflow's execute_workflow method.

        Raises:
            KeyError: If the workflow_name is not found in the configuration.
            FileNotFoundError: If the configured module path does not exist.
            PermissionError: If the module path is outside the project directory.
            ImportError: If the module cannot be imported.
            AttributeError: If the specified class or 'execute_workflow' method is not found.
            TypeError: If the 'execute_workflow' method is not async.
            RuntimeError: Wraps exceptions raised during the workflow's execution or
                          other setup/execution errors within the manager.
        """
        logger.info(f"Executing custom workflow: {workflow_name}")
        try:
            # 1. Get Config
            config = self.get_custom_workflow_config(workflow_name)
            module_path = config.module_path
            class_name = config.class_name

            # 2. Security Check (Basic): Ensure path is within project
            if not str(module_path.resolve()).startswith(
                str(PROJECT_ROOT_DIR.resolve())
            ):
                logger.error(
                    f"Custom workflow path '{module_path}' is outside the project directory. Aborting."
                )
                raise PermissionError(
                    "Custom workflow path is outside the project directory."
                )

            if not module_path.exists():
                logger.error(f"Custom workflow module file not found: {module_path}")
                raise FileNotFoundError(
                    f"Custom workflow module file not found: {module_path}"
                )

            # 3. Dynamic Import
            spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not create module spec for {module_path}")
            module = importlib.util.module_from_spec(spec)
            # Ensure the module's name is set for potential relative imports within the workflow
            # setattr(module, '__name__', module_path.stem) # Or a more robust name if needed
            spec.loader.exec_module(module)  # type: ignore

            # 4. Get Class
            if not hasattr(module, class_name):
                logger.error(f"Class '{class_name}' not found in module {module_path}")
                raise AttributeError(
                    f"Class '{class_name}' not found in module {module_path}"
                )
            # Ensure WorkflowClass is actually retrieved before proceeding
            WorkflowClass = getattr(module, class_name, None)  # Use default=None
            if WorkflowClass is None:
                # This should ideally be caught by hasattr, but double-check
                logger.error(
                    f"AttributeError: Class '{class_name}' could not be retrieved from module {module_path}."
                )
                raise AttributeError(
                    f"Class '{class_name}' not found in module {module_path}"
                )

            # 5. Instantiate
            # Consider if workflows need config or host during init? For now, assume no args.
            try:
                workflow_instance = WorkflowClass()
            except Exception as init_err:
                logger.error(
                    f"Error instantiating workflow class '{class_name}' from {module_path}: {init_err}",
                    exc_info=True,
                )
                raise RuntimeError(
                    f"Failed to instantiate workflow class '{class_name}': {init_err}"
                ) from init_err

            # 6. Check for execute_workflow method
            execute_method_name = "execute_workflow"  # Standard method name
            if not hasattr(workflow_instance, execute_method_name) or not callable(
                getattr(workflow_instance, execute_method_name)
            ):
                logger.error(
                    f"Method '{execute_method_name}' not found or not callable in class '{class_name}' from {module_path}"
                )
                raise AttributeError(
                    f"Method '{execute_method_name}' not found or not callable in class '{class_name}'"
                )

            execute_method = getattr(workflow_instance, execute_method_name)

            # 7. Execute (check if async)
            if not inspect.iscoroutinefunction(execute_method):
                logger.error(
                    f"Method '{execute_method_name}' in class '{class_name}' from {module_path} must be async."
                )
                raise TypeError(f"Method '{execute_method_name}' must be async.")

            # Execute the workflow's method, passing input and the host instance
            result = await execute_method(
                initial_input=initial_input, host_instance=host_instance
            )

            logger.info(
                f"Custom workflow '{workflow_name}' execution finished successfully."
            )
            return result

        except (
            KeyError,
            FileNotFoundError,
            ImportError,
            AttributeError,
            PermissionError,
            TypeError,
        ) as e:
            # Catch specific setup/loading errors
            logger.error(
                f"Error setting up or executing custom workflow '{workflow_name}': {e}",
                exc_info=True,
            )
            # Re-raise these specific errors for the API endpoint to handle appropriately (e.g., 404, 500)
            raise e
        except Exception as e:
            # Catch errors *during* the workflow's own execution
            # Define execute_method_name safely for logging, even if not reached
            execute_method_name_for_log = (
                getattr(execute_method, "__name__", "unknown_method")
                if "execute_method" in locals()
                else "execute_workflow"
            )
            logger.error(
                f"Exception raised within custom workflow '{workflow_name}' ({class_name}.{execute_method_name_for_log}): {e}",
                exc_info=True,
            )
            # Wrap internal workflow errors in a RuntimeError for the API endpoint
            raise RuntimeError(
                f"Exception during custom workflow execution: {e}"
            ) from e
