import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Type
import json
from pydantic import ValidationError

# Use relative import for models within the same package
from .config_models import (
    ClientConfig,
    LLMConfig,
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)
from .config_utils import resolve_path_fields, relativize_path_fields

# Define logger before it might be used in except block
logger = logging.getLogger(__name__)

# Import PROJECT_ROOT_DIR from the package __init__
try:
    from src.config import PROJECT_ROOT_DIR
except ImportError:
    logger.error("Could not import PROJECT_ROOT_DIR from src.config.")
    # Define a fallback or raise a more critical error if essential
    PROJECT_ROOT_DIR = Path(".")

# Define component base directories relative to project root
# Duplicated from old ConfigManager - consider utils.py later if needed elsewhere
COMPONENT_TYPES_DIRS = {
    "clients": PROJECT_ROOT_DIR / "config/clients",
    "llm_configs": PROJECT_ROOT_DIR / "config/llms",
    "agents": PROJECT_ROOT_DIR / "config/agents",
    "simple_workflows": PROJECT_ROOT_DIR / "config/workflows",
    "custom_workflows": PROJECT_ROOT_DIR / "config/custom_workflows",
}

# Mapping component type to its model class and ID field name
COMPONENT_META = {
    "clients": (ClientConfig, "client_id"),
    "llm_configs": (LLMConfig, "llm_id"),
    "agents": (AgentConfig, "name"),
    "simple_workflows": (WorkflowConfig, "name"),
    "custom_workflows": (CustomWorkflowConfig, "name"),
}


class ComponentManager:
    """
    Manages the discovery, loading, validation, and CRUD operations
    for reusable component configurations (Agents, LLMs, Clients, etc.).
    """

    def __init__(self):
        """Initializes the ComponentManager by loading all components from disk."""
        self.clients: Dict[str, ClientConfig] = {}
        self.llm_configs: Dict[str, LLMConfig] = {}
        self.agents: Dict[str, AgentConfig] = {}
        self.simple_workflows: Dict[str, WorkflowConfig] = {}
        self.custom_workflows: Dict[str, CustomWorkflowConfig] = {}

        # Store components in a structured way for easier access
        self._component_stores = {
            "clients": self.clients,
            "llm_configs": self.llm_configs,
            "agents": self.agents,
            "simple_workflows": self.simple_workflows,
            "custom_workflows": self.custom_workflows,
        }

        self._load_all_components()
        logger.info("ComponentManager initialized and all components loaded.")

    def _parse_component_file(
        self, file_path: Path, model_class: Type, id_field: str
    ) -> Optional[Tuple[str, Any]]:
        """Parses a single component JSON file, validates it, and resolves paths."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            component_id = data.get(id_field)
            if not component_id:
                logger.warning(
                    f"Component file {file_path} missing ID field '{id_field}'. Skipping."
                )
                return None

            # Resolve paths using the utility function
            data_to_validate = resolve_path_fields(data, model_class, PROJECT_ROOT_DIR)

            # Validate and return model instance
            component_model = model_class(**data_to_validate)
            return component_id, component_model

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from component file {file_path}: {e}")
            return None
        except ValidationError as e:  # Catch Pydantic validation errors specifically
            logger.error(f"Validation failed for component file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Failed to load component from {file_path}: {e}", exc_info=True
            )
            return None

    def _load_all_components(self):
        """Loads all component configurations from their respective directories."""
        logger.debug("Loading all component configurations...")

        for component_type, (model_class, id_field) in COMPONENT_META.items():
            target_dict = self._component_stores.get(component_type)
            if target_dict is None:
                logger.error(
                    f"Internal error: No component store found for type '{component_type}'. Skipping."
                )
                continue  # Should not happen if COMPONENT_META and _component_stores are aligned

            component_dir = COMPONENT_TYPES_DIRS.get(component_type)
            if not component_dir:
                logger.warning(
                    f"No directory defined for component type '{component_type}'. Skipping loading."
                )
                continue

            component_dir.mkdir(parents=True, exist_ok=True)  # Ensure dir exists
            loaded_count = 0
            error_count = 0
            logger.debug(f"Scanning {component_dir} for {component_type} components...")
            for file_path in component_dir.glob("*.json"):
                parse_result = self._parse_component_file(
                    file_path, model_class, id_field
                )
                if parse_result:
                    component_id, component_model = parse_result
                    if component_id in target_dict:
                        logger.warning(
                            f"Duplicate component ID '{component_id}' found for type '{component_type}'. Overwriting existing entry from {file_path}."
                        )
                    target_dict[component_id] = component_model
                    loaded_count += 1
                else:
                    error_count += 1  # Error logged within _parse_component_file

            logger.info(  # Changed to INFO for summary
                f"Loaded {loaded_count} components of type '{component_type}' from {component_dir}"
                + (f" ({error_count} errors)." if error_count else ".")
            )
        logger.debug("_load_all_components finished.")

    # --- Helper Methods ---
    def _get_component_file_path(self, component_type: str, component_id: str) -> Path:
        """Constructs and validates the file path for a component."""
        component_dir = COMPONENT_TYPES_DIRS.get(component_type)
        if not component_dir:
            raise ValueError(
                f"Configuration error: No directory defined for component type '{component_type}'."
            )

        filename = f"{component_id}.json"
        file_path = (component_dir / filename).resolve()

        # Security check
        if not str(file_path).startswith(str(component_dir.resolve())):
            raise ValueError(
                f"Constructed file path '{file_path}' is outside the allowed directory '{component_dir}'."
            )

        return file_path

    def _prepare_data_for_save(self, model_instance: Any) -> Dict[str, Any]:
        """Converts a validated Pydantic model instance into a dict suitable for JSON, handling Path objects."""
        # First, dump the model to a dict. Path objects will remain Path objects.
        raw_model_dict = model_instance.model_dump()

        # Now, use the utility function to convert Path objects to relative/absolute strings
        json_data_with_str_paths = relativize_path_fields(
            raw_model_dict, type(model_instance), PROJECT_ROOT_DIR
        )
        return json_data_with_str_paths

    # --- Component Accessor Methods ---
    def get_component_config(
        self, component_type: str, component_id: str
    ) -> Optional[Any]:
        """Gets the loaded configuration model for a specific component ID."""
        target_dict = self._component_stores.get(component_type)
        if target_dict is not None:
            return target_dict.get(component_id)
        logger.warning(f"Attempted to get component of unknown type: {component_type}")
        return None

    # Convenience methods for specific types
    def get_client(self, client_id: str) -> Optional[ClientConfig]:
        return self.get_component_config("clients", client_id)  # type: ignore

    def get_llm_config(self, llm_id: str) -> Optional[LLMConfig]:
        return self.get_component_config("llm_configs", llm_id)  # type: ignore

    def get_agent(self, agent_name: str) -> Optional[AgentConfig]:
        return self.get_component_config("agents", agent_name)  # type: ignore

    def get_simple_workflow(self, workflow_name: str) -> Optional[WorkflowConfig]:
        return self.get_component_config("simple_workflows", workflow_name)  # type: ignore

    def get_custom_workflow(self, workflow_name: str) -> Optional[CustomWorkflowConfig]:
        return self.get_component_config("custom_workflows", workflow_name)  # type: ignore

    def list_components(self, component_type: str) -> List[Any]:
        """Lists all loaded component model instances of a specific type."""
        target_dict = self._component_stores.get(component_type)
        if target_dict is not None:
            return list(target_dict.values())
        logger.warning(
            f"Attempted to list components of unknown type: {component_type}"
        )
        return []

    # Convenience methods for listing specific types
    def list_clients(self) -> List[ClientConfig]:
        return self.list_components("clients")  # type: ignore

    def list_llm_configs(self) -> List[LLMConfig]:
        return self.list_components("llm_configs")  # type: ignore

    def list_agents(self) -> List[AgentConfig]:
        return self.list_components("agents")  # type: ignore

    def list_simple_workflows(self) -> List[WorkflowConfig]:
        return self.list_components("simple_workflows")  # type: ignore

    def list_custom_workflows(self) -> List[CustomWorkflowConfig]:
        return self.list_components("custom_workflows")  # type: ignore

    # --- Component File CRUD Methods ---
    def list_component_files(self, component_type: str) -> List[str]:
        """Lists the JSON filenames for a given component type."""
        component_dir = COMPONENT_TYPES_DIRS.get(component_type)
        if not component_dir:
            logger.error(
                f"Invalid component type specified for listing files: {component_type}"
            )
            return []  # Or raise error? API might expect empty list on bad type.

        if not component_dir.is_dir():
            logger.warning(
                f"Component directory not found for type '{component_type}' at {component_dir}. Returning empty list."
            )
            return []

        try:
            return sorted([f.name for f in component_dir.glob("*.json") if f.is_file()])
        except Exception as e:
            logger.error(f"Error listing files in {component_dir}: {e}", exc_info=True)
            return []  # Return empty list on error

    def save_component_config(
        self, component_type: str, config_data: Dict[str, Any]
    ) -> Any:
        """Saves (creates or updates) a component configuration JSON file and updates memory."""
        logger.info(
            f"Attempting to save/update component config for type: {component_type}"
        )  # Modified log

        target_dict = self._component_stores.get(component_type)
        meta = COMPONENT_META.get(component_type)

        if target_dict is None or meta is None:
            raise ValueError(f"Invalid component type specified: {component_type}")

        model_class, id_field = meta

        component_id = config_data.get(id_field)
        if not component_id or not isinstance(component_id, str):
            raise ValueError(
                f"Missing or invalid ID field ('{id_field}') in provided config data for type '{component_type}'."
            )

        try:
            # Get the validated file path (also performs security checks)
            file_path = self._get_component_file_path(component_type, component_id)

            # Resolve paths in the input data using the utility function before validation
            data_to_validate = resolve_path_fields(
                config_data, model_class, PROJECT_ROOT_DIR
            )

            # Validate data against the Pydantic model
            validated_model = model_class(**data_to_validate)

            # Prepare data for JSON serialization using the helper
            json_data = self._prepare_data_for_save(validated_model)

            # Write to file (pretty-printed)
            component_dir = file_path.parent  # Get directory from validated path
            component_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(json_data, f, indent=4)

            # Update in-memory dictionary
            target_dict[component_id] = validated_model
            logger.info(
                f"Successfully saved component '{component_id}' of type '{component_type}' to {file_path}"
            )
            return validated_model  # Return the validated model instance

        except ValidationError as e:
            logger.error(
                f"Validation failed for component '{component_id}' of type '{component_type}': {e}"
            )
            raise ValueError(f"Configuration validation failed: {e}") from e
        except ValueError as e:  # Catch errors from _get_component_file_path
            logger.error(
                f"Error determining file path for component '{component_id}' of type '{component_type}': {e}"
            )
            raise
        except IOError as e:
            logger.error(
                f"Failed to write component file {file_path}: {e}"
            )  # file_path might not be defined if _get_component_file_path failed
            raise IOError(f"Failed to write configuration file: {e}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error saving component '{component_id}' of type '{component_type}': {e}",
                exc_info=True,
            )
            raise RuntimeError(f"An unexpected error occurred during save: {e}") from e

    def delete_component_config(self, component_type: str, component_id: str) -> bool:
        """Deletes a component configuration JSON file and removes from memory."""
        logger.info(
            f"Attempting to delete component config for type: {component_type}, ID: {component_id}"
        )

        target_dict = self._component_stores.get(component_type)
        if target_dict is None:
            logger.error(
                f"Invalid component type specified for deletion: {component_type}"
            )
            return False  # Or raise ValueError? Returning False for API consistency.

        try:
            file_path = self._get_component_file_path(component_type, component_id)
        except ValueError as e:  # Catches invalid type or path issues from helper
            logger.error(
                f"Cannot get file path for component '{component_id}' of type '{component_type}': {e}"
            )
            # If we can't even determine the path, we likely can't delete. Check memory anyway?
            # Let's try removing from memory even if file path failed, but log clearly.
            if component_id in target_dict:
                del target_dict[component_id]
                logger.warning(
                    f"Removed component '{component_id}' from memory despite file path error."
                )
                return True  # Indicate removal from memory occurred
            else:
                return False  # Failed to get path and not in memory

        deleted_from_fs = False
        try:
            if file_path.is_file():
                file_path.unlink()
                logger.info(f"Successfully deleted component file: {file_path}")
                deleted_from_fs = True
            else:
                logger.warning(
                    f"Component file not found for deletion at {file_path}. Cannot delete from filesystem."
                )
                # Treat non-existence as success for deletion intent regarding filesystem state
                deleted_from_fs = True

        except OSError as e:
            logger.error(
                f"Error deleting component file {file_path}: {e}", exc_info=True
            )
            # If file deletion fails, we probably shouldn't remove from memory either, return False
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error during file deletion for {file_path}: {e}",
                exc_info=True,
            )
            return False  # Treat unexpected errors as failure

        # Remove from in-memory dictionary if it exists
        if component_id in target_dict:
            del target_dict[component_id]
            logger.info(
                f"Removed component '{component_id}' of type '{component_type}' from memory."
            )
            # Return True if removed from memory, regardless of FS state (as FS might not have existed)
            return True
        else:
            logger.warning(
                f"Component '{component_id}' of type '{component_type}' not found in memory. Already deleted or never loaded?"
            )
            # If it wasn't in memory, return True only if the file deletion attempt was successful
            # (i.e., file was deleted or didn't exist in the first place).
            # Return False only if file deletion failed with an error.
            return deleted_from_fs

    def create_component_file(
        self, component_type: str, config_data: Dict[str, Any], overwrite: bool = False
    ) -> Any:
        """
        Creates a new component JSON file from config_data and adds the component
        to the in-memory store.

        Args:
            component_type: The type of component (e.g., 'clients', 'agents').
            config_data: Dictionary containing the component's configuration.
            overwrite: If True, overwrite the file if it already exists.
                       Defaults to False.

        Returns:
            The validated Pydantic model instance of the created component.

        Raises:
            ValueError: If component_type is invalid, ID is missing/invalid, or
                        validation fails.
            FileExistsError: If the component file already exists and overwrite is False.
            IOError: If there's an error writing the file.
            RuntimeError: For other unexpected errors.
        """
        logger.info(
            f"Attempting to create component file for type: {component_type}, overwrite={overwrite}"
        )

        target_dict = self._component_stores.get(component_type)
        meta = COMPONENT_META.get(component_type)

        if target_dict is None or meta is None:
            raise ValueError(f"Invalid component type specified: {component_type}")

        model_class, id_field = meta

        component_id = config_data.get(id_field)
        if not component_id or not isinstance(component_id, str):
            raise ValueError(
                f"Missing or invalid ID field ('{id_field}') in provided config data for type '{component_type}'."
            )

        try:
            # Get the validated file path (also performs security checks)
            file_path = self._get_component_file_path(component_type, component_id)

            if file_path.exists() and not overwrite:
                raise FileExistsError(
                    f"Component file {file_path} already exists. Set overwrite=True to replace it."
                )

            # Resolve paths in the input data using the utility function before validation
            data_to_validate = resolve_path_fields(
                config_data, model_class, PROJECT_ROOT_DIR
            )

            # Validate data against the Pydantic model
            validated_model = model_class(**data_to_validate)

            # Prepare data for JSON serialization using the helper
            # _prepare_data_for_save now uses relativize_path_fields internally
            json_data = self._prepare_data_for_save(validated_model)

            # Write to file (pretty-printed)
            component_dir = file_path.parent  # Get directory from validated path
            component_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(json_data, f, indent=4)

            # Update in-memory dictionary
            target_dict[component_id] = validated_model
            logger.info(
                f"Successfully created component '{component_id}' of type '{component_type}' at {file_path}"
            )
            return validated_model  # Return the validated model instance

        except FileExistsError:  # Re-raise specifically
            raise
        except ValidationError as e:
            logger.error(
                f"Validation failed for new component '{component_id}' of type '{component_type}': {e}"
            )
            raise ValueError(f"Configuration validation failed: {e}") from e
        except (
            ValueError
        ) as e:  # Catch errors from _get_component_file_path or ID issues
            logger.error(
                f"Error processing component '{component_id}' of type '{component_type}': {e}"
            )
            raise
        except IOError as e:
            # file_path might not be defined if _get_component_file_path failed, but it should be by now
            logger.error(f"Failed to write component file {file_path}: {e}")
            raise IOError(f"Failed to write configuration file: {e}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error creating component '{component_id}' of type '{component_type}': {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"An unexpected error occurred during creation: {e}"
            ) from e
