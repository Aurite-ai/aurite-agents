"""
Agent Runner for executing Python functions from file paths.
"""

import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Executes a 'run' function from a Python file given a filepath.
    """

    def __init__(self, filepath: str | Path):
        """
        Initializes the AgentRunner.

        Args:
            filepath: Path to the Python file containing the 'run' function.
        """
        if isinstance(filepath, str):
            filepath = Path(filepath)

        if not isinstance(filepath, Path):
            raise TypeError("filepath must be a string or Path object")

        self.filepath = filepath
        self.run_function = None
        logger.debug(f"AgentRunner initialized for file: {self.filepath}")

        self._load_run_function()

    async def execute(
        self,
        input: str,
        **kwargs,
    ) -> Any:
        """
        Executes the loaded 'run' function with the provided input.

        Args:
            input: The string input to pass to the run function
            kwargs: Additional arguments to pass to the run function

        Returns:
            The result returned by the run function.

        Raises:
            RuntimeError: If the run function is not loaded or execution fails.
        """
        if self.run_function is None:
            raise RuntimeError("Run function not loaded. Check if the file contains a 'run' function.")

        try:
            logger.debug(f"Executing run function from {self.filepath}")

            if inspect.iscoroutinefunction(self.run_function):
                result = await self.run_function(input, **kwargs)
            else:
                result = self.run_function(input, **kwargs)

            logger.info(f"AgentRunner execution finished successfully for {self.filepath}")
            return result

        except Exception as e:
            logger.error(f"Exception raised during AgentRunner execution of {self.filepath}: {e}")
            raise RuntimeError(f"Exception during AgentRunner execution: {e}") from e

    def _load_run_function(self):
        """
        Dynamically loads the 'run' function from the specified Python file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ImportError: If the module cannot be imported.
            AttributeError: If the 'run' function is not found.
        """
        try:
            logger.debug(f"Loading run function from: {self.filepath}")

            # Check if file exists
            if not self.filepath.exists():
                logger.error(f"Python file not found: {self.filepath}")
                raise FileNotFoundError(f"Python file not found: {self.filepath}")

            # Dynamic import
            spec = importlib.util.spec_from_file_location(self.filepath.stem, self.filepath)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not create module spec for {self.filepath}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.debug(f"Dynamically imported module: {self.filepath}")

            # Get the 'run' function
            run_function = getattr(module, "run", None)
            if run_function is None:
                logger.error(f"Function 'run' not found in module {self.filepath}")
                raise AttributeError(f"Function 'run' not found in module {self.filepath}")

            if not callable(run_function):
                logger.error(f"Attribute 'run' is not callable in module {self.filepath}")
                raise AttributeError(f"Attribute 'run' is not callable in module {self.filepath}")

            self.run_function = run_function
            logger.info(f"Successfully loaded 'run' function from {self.filepath}")

        except (FileNotFoundError, ImportError, AttributeError) as e:
            logger.error(f"Error loading run function from {self.filepath}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error loading run function from {self.filepath}: {e}")
            raise RuntimeError(f"Unexpected error loading run function: {e}") from e

    def reload(self):
        """
        Reloads the run function from the file.
        Useful if the file has been modified and needs to be reloaded.
        """
        logger.debug(f"Reloading run function from {self.filepath}")
        self.run_function = None
        self._load_run_function()
