import logging
from pathlib import Path
from typing import Dict, Any
import json
from pydantic import ValidationError

# Use relative import for models and the ComponentManager
from .config_models import (
    ProjectConfig,
    ClientConfig,
    LLMConfig,
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)
from .component_manager import ComponentManager
from .config_utils import resolve_path_fields  # Import the utility

# Import PROJECT_ROOT_DIR from the package __init__
try:
    from src.config import PROJECT_ROOT_DIR
except ImportError:
    # Define logger earlier if needed here
    # logger = logging.getLogger(__name__) # Define logger if needed before use
    # logger.error("Could not import PROJECT_ROOT_DIR from src.config.")
    PROJECT_ROOT_DIR = Path(".")  # Fallback

logger = logging.getLogger(__name__)


class ProjectManager:
    """
    Manages the loading and resolution of project configurations.
    It uses a ComponentManager to resolve references to reusable components.
    """

    def __init__(self, component_manager: ComponentManager):
        """
        Initializes the ProjectManager.

        Args:
            component_manager: An initialized instance of ComponentManager.
        """
        if not isinstance(component_manager, ComponentManager):
            raise TypeError("component_manager must be an instance of ComponentManager")
        self.component_manager = component_manager
        logger.info("ProjectManager initialized.")

    def load_project(self, project_config_file_path: Path) -> ProjectConfig:
        """
        Loads a project configuration file, resolving component references
        using the associated ComponentManager.

        Args:
            project_config_file_path: Path to the project JSON file.

        Returns:
            A fully resolved ProjectConfig object.

        Raises:
            FileNotFoundError: If the project file does not exist.
            RuntimeError: If JSON parsing fails or validation errors occur.
            ValueError: If component references are invalid or cannot be resolved.
        """
        logger.info(f"Loading project configuration from: {project_config_file_path}")
        if not project_config_file_path.is_file():
            logger.error(
                f"Project configuration file not found: {project_config_file_path}"
            )
            raise FileNotFoundError(
                f"Project configuration file not found: {project_config_file_path}"
            )

        try:
            with open(project_config_file_path, "r") as f:
                project_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(
                f"Error parsing project configuration file {project_config_file_path}: {e}"
            )
            raise RuntimeError(f"Error parsing project configuration file: {e}") from e

        project_name = project_data.get(
            "name", project_config_file_path.stem
        )  # Use filename stem as fallback name
        project_description = project_data.get("description")
        logger.debug(f"Processing project: '{project_name}'")

        # Resolve all component types using the helper
        resolved_clients = self._resolve_components(
            project_data,
            project_name,
            "clients",
            ClientConfig,
            "client_id",
            "Client",
            "clients",
        )
        resolved_llm_configs = self._resolve_components(
            project_data,
            project_name,
            "llm_configs",
            LLMConfig,
            "llm_id",
            "LLMConfig",
            "llm_configs",
        )
        resolved_agents = self._resolve_components(
            project_data,
            project_name,
            "agent_configs",
            AgentConfig,
            "name",
            "Agent",
            "agents",
        )
        resolved_simple_workflows = self._resolve_components(
            project_data,
            project_name,
            "simple_workflow_configs",
            WorkflowConfig,
            "name",
            "SimpleWorkflow",
            "simple_workflows",
        )
        resolved_custom_workflows = self._resolve_components(
            project_data,
            project_name,
            "custom_workflow_configs",
            CustomWorkflowConfig,
            "name",
            "CustomWorkflow",
            "custom_workflows",
        )

        try:
            # Validate the final ProjectConfig structure
            project_config = ProjectConfig(
                name=project_name,
                description=project_description,
                clients=resolved_clients,
                llm_configs=resolved_llm_configs,
                agent_configs=resolved_agents,
                simple_workflow_configs=resolved_simple_workflows,
                custom_workflow_configs=resolved_custom_workflows,
            )
            logger.info(f"Successfully loaded and resolved project '{project_name}'.")
            return project_config
        except (
            ValidationError
        ) as e:  # Catch Pydantic validation errors for the final ProjectConfig
            logger.error(
                f"Failed to validate final ProjectConfig for '{project_name}': {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Failed to validate final ProjectConfig for '{project_name}': {e}"
            ) from e
        except (
            Exception
        ) as e:  # Catch any other unexpected errors during final assembly
            logger.error(
                f"Unexpected error assembling final ProjectConfig for '{project_name}': {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Unexpected error assembling final ProjectConfig for '{project_name}': {e}"
            ) from e

    # --- Private Helper for Resolving ---
    def _resolve_components(
        self,
        project_data: Dict[str, Any],  # The raw data from the project file
        project_name: str,  # For logging context
        project_key: str,  # e.g., "clients", "agent_configs"
        model_class: type,
        id_field: str,
        type_name: str,  # User-friendly type name for logging, e.g., "Client", "Agent"
        cm_component_type_key: str,  # Exact key for ComponentManager, e.g., "clients", "agents"
    ) -> Dict[str, Any]:
        """
        Helper function to resolve component references or use inline definitions
        within a project configuration. Uses the ComponentManager to look up referenced IDs.
        """
        resolved_items: Dict[str, Any] = {}
        item_references = project_data.get(project_key, [])

        if not isinstance(item_references, list):
            logger.warning(
                f"'{project_key}' in project '{project_name}' is not a list. Skipping resolution for this key."
            )
            return {}

        for item_ref in item_references:
            component_id = None
            try:
                if isinstance(item_ref, str):  # It's an ID reference
                    component_id = item_ref
                    # Use ComponentManager to get the pre-loaded, validated component
                    component_model = self.component_manager.get_component_config(
                        cm_component_type_key,
                        component_id,  # Use the exact key
                    )
                    if component_model:
                        resolved_items[component_id] = component_model
                        logger.debug(
                            f"Resolved {type_name} component reference: '{component_id}'"
                        )
                    else:
                        # Raise or log warning? Let's raise for now, as a missing reference is likely an error.
                        logger.error(
                            f"{type_name} component ID '{component_id}' referenced in project '{project_name}' not found in ComponentManager."
                        )
                        raise ValueError(
                            f"{type_name} component ID '{component_id}' not found."
                        )

                elif isinstance(item_ref, dict):  # Inline definition
                    component_id = item_ref.get(id_field)
                    if not component_id:
                        logger.warning(
                            f"Inline {type_name} definition missing ID field '{id_field}' in project '{project_name}'. Skipping: {item_ref}"
                        )
                        continue

                    # Resolve paths for the inline definition using the utility function
                    data_to_validate = resolve_path_fields(
                        item_ref, model_class, PROJECT_ROOT_DIR
                    )

                    # Validate the inline definition
                    inline_item = model_class(**data_to_validate)

                    # Decide precedence: Let inline definition override component if ID conflicts
                    if component_id in resolved_items:
                        logger.warning(
                            f"Inline {type_name} definition for '{component_id}' overrides previously resolved reference in project '{project_name}'."
                        )
                    resolved_items[component_id] = inline_item
                    logger.debug(
                        f"Loaded and validated inline {type_name} definition: '{component_id}'"
                    )
                else:
                    logger.warning(
                        f"Invalid {type_name} reference in project '{project_name}'. Expected string ID or dict definition. Got: {item_ref}"
                    )

            except ValidationError as e:
                logger.error(
                    f"Validation failed for inline {type_name} definition '{component_id or item_ref}' in project '{project_name}': {e}"
                )
                # Decide whether to skip this item or raise an error for the whole project load
                raise ValueError(f"Invalid inline {type_name} definition: {e}") from e
            except (
                ValueError
            ) as e:  # Catch missing reference or inline validation errors specifically
                logger.error(
                    f"Value error processing {type_name} reference '{component_id or item_ref}' in project '{project_name}': {e}",
                    exc_info=True,  # Include traceback for ValueError as well
                )
                # Re-raise the ValueError so it's not caught by the generic Exception handler below
                raise
            except Exception as e:  # Catch other unexpected errors
                logger.error(
                    f"Unexpected error processing {type_name} reference '{component_id or item_ref}' in project '{project_name}': {e}",
                    exc_info=True,  # Changed message to 'Unexpected error'
                )
                # Decide whether to skip or raise
                raise RuntimeError(
                    f"Error processing {type_name} reference: {e}"
                ) from e

        return resolved_items

    def create_project_file(
        self,
        file_path: Path,
        project_content: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """
        Creates a new project JSON file at the given file_path with the
        provided project_content.

        Args:
            file_path: The absolute Path where the project JSON file should be created.
            project_content: A dictionary representing the content of the project file.
            overwrite: If True, overwrite the file if it already exists.
                       Defaults to False.

        Returns:
            True if the file was successfully created.

        Raises:
            FileExistsError: If the project file already exists and overwrite is False.
            IOError: If there's an error writing the file.
            RuntimeError: For other unexpected errors.
        """
        logger.info(
            f"Attempting to create project file at: {file_path}, overwrite={overwrite}"
        )

        try:
            if not isinstance(file_path, Path):
                raise TypeError("file_path must be a Path object.")
            if not file_path.is_absolute():
                # Or decide to resolve it relative to PROJECT_ROOT_DIR if that's desired
                logger.warning(
                    f"Project file path {file_path} is not absolute. Proceeding, but absolute paths are recommended."
                )

            if file_path.exists() and not overwrite:
                raise FileExistsError(
                    f"Project file {file_path} already exists. Set overwrite=True to replace it."
                )

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file (pretty-printed)
            with open(file_path, "w") as f:
                json.dump(project_content, f, indent=4)

            logger.info(f"Successfully created project file at {file_path}")
            return True

        except FileExistsError:  # Re-raise specifically
            raise
        except TypeError as e:  # For incorrect file_path type
            logger.error(f"Invalid argument type for create_project_file: {e}")
            raise
        except IOError as e:
            logger.error(f"Failed to write project file {file_path}: {e}")
            raise IOError(f"Failed to write project file: {e}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error creating project file {file_path}: {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"An unexpected error occurred during project file creation: {e}"
            ) from e
