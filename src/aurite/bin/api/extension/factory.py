"""
Factory for dynamically loading API extensions.
"""

import importlib
import logging
from typing import Type

from .extension import Extension

logger = logging.getLogger(__name__)


class ExtensionFactory:
    """
    Factory for creating Extension instances from module paths.

    Supports loading extensions specified as:
    - module.ClassName (e.g., "my_package.extensions.MyExtension")
    - module path (will look for Extension class)
    """

    @staticmethod
    def get(path: str) -> Type[Extension]:
        """
        Dynamically import and return an Extension class.

        Args:
            path: Import path to the extension class
                 Format: "module.path.ClassName" or "module.path"

        Returns:
            Extension class (not instantiated)

        Raises:
            ImportError: If the module cannot be imported
            AttributeError: If the class doesn't exist
            TypeError: If the class is not an Extension subclass
        """
        try:
            # Split path into module and class name
            parts = path.rsplit(".", 1)

            if len(parts) == 2:
                module_path, class_name = parts
            else:
                # If only module given, look for "Extension" class
                module_path = path
                class_name = "Extension"

            # Import the module
            logger.info(f"Loading extension from: {module_path}")
            module = importlib.import_module(module_path)

            # Get the class
            extension_class = getattr(module, class_name)

            # Verify it's actually a class
            if not isinstance(extension_class, type):
                raise TypeError(f"{class_name} in module '{module_path}' is not a class")

            # Verify it's an Extension subclass
            if not issubclass(extension_class, Extension):
                raise TypeError(f"{class_name} must be a subclass of Extension")

            logger.info(f"Successfully loaded extension: {path}")
            return extension_class

        except ImportError as e:
            logger.error(f"Failed to import extension module '{module_path}': {e}")
            raise
        except AttributeError as e:
            logger.error(f"Extension class '{class_name}' not found in module '{module_path}': {e}")
            raise
        except TypeError as e:
            logger.error(f"Invalid extension class '{path}': {e}")
            raise


__all__ = ["ExtensionFactory"]
