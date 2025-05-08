import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple  # Add List, Tuple as needed
import json
from pydantic import ValidationError  # Import ValidationError

from .config_models import (  # Relative import
    ProjectConfig,
    ClientConfig,
    LLMConfig,
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    # Potentially HostConfig if it's used by ConfigManager directly
)
# Import load_host_config_from_json and its helpers if they are to be adapted
# from .config import _load_client_configs, _load_agent_configs, etc. OR refactor them here.
# For now, assume we'll adapt parts of load_host_config_from_json's logic.

logger = logging.getLogger(__name__)

# Define component base directories relative to project root (similar to config_api.py)
# This needs access to PROJECT_ROOT_DIR, which might be defined in src/config/config.py
try:
    # Import from the package __init__
    from src.config import PROJECT_ROOT_DIR
except ImportError:
    # Fallback or error if PROJECT_ROOT_DIR is not found.
    # This indicates a potential issue with how PROJECT_ROOT_DIR is defined/accessed.
    # For now, assume it's accessible.
    logger.error(
        "PROJECT_ROOT_DIR not found via src.config. ConfigManager may not function correctly."
    )
    # Attempt relative import as a fallback (might work depending on execution context)
    try:
        from .config import PROJECT_ROOT_DIR
    except ImportError:
        logger.error("Could not import PROJECT_ROOT_DIR via relative path either.")
        PROJECT_ROOT_DIR = Path(".")  # Placeholder, needs proper resolution

COMPONENT_TYPES_DIRS = {
    "clients": PROJECT_ROOT_DIR / "config/clients",
    "llm_configs": PROJECT_ROOT_DIR
    / "config/llms",  # Assuming a new dir for LLM components
    "agents": PROJECT_ROOT_DIR / "config/agents",
    "simple_workflows": PROJECT_ROOT_DIR
    / "config/workflows",  # Existing dir for simple workflows
    "custom_workflows": PROJECT_ROOT_DIR / "config/custom_workflows",
}


class ConfigManager:
    def __init__(self):
        self.component_clients: Dict[str, ClientConfig] = {}
        self.component_llm_configs: Dict[str, LLMConfig] = {}
        self.component_agents: Dict[str, AgentConfig] = {}
        self.component_simple_workflows: Dict[str, WorkflowConfig] = {}
        self.component_custom_workflows: Dict[str, CustomWorkflowConfig] = {}

        self._load_all_components()
        logger.info("ConfigManager initialized and all components loaded.")

    def _parse_component_file(
        self, file_path: Path, model_class: type, id_field: str
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

            # Resolve paths relative to project root if necessary
            if model_class == ClientConfig and "server_path" in data:
                # Ensure server_path is resolved correctly
                sp = Path(data["server_path"])
                data["server_path"] = (
                    (PROJECT_ROOT_DIR / sp).resolve()
                    if not sp.is_absolute()
                    else sp.resolve()
                )
            if model_class == CustomWorkflowConfig and "module_path" in data:
                mp = Path(data["module_path"])
                data["module_path"] = (
                    (PROJECT_ROOT_DIR / mp).resolve()
                    if not mp.is_absolute()
                    else mp.resolve()
                )

            # Validate and return model instance
            component_model = model_class(**data)
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
        component_map = {
            "clients": (ClientConfig, "client_id", self.component_clients),
            "llm_configs": (LLMConfig, "llm_id", self.component_llm_configs),
            "agents": (AgentConfig, "name", self.component_agents),
            "simple_workflows": (
                WorkflowConfig,
                "name",
                self.component_simple_workflows,
            ),
            "custom_workflows": (
                CustomWorkflowConfig,
                "name",
                self.component_custom_workflows,
            ),
        }

        for component_type, (
            model_class,
            id_field,
            target_dict,
        ) in component_map.items():
            component_dir = COMPONENT_TYPES_DIRS.get(component_type)
            if not component_dir:
                logger.warning(
                    f"No directory defined for component type '{component_type}'. Skipping."
                )
                continue

            component_dir.mkdir(parents=True, exist_ok=True)  # Ensure dir exists
            loaded_count = 0
            error_count = 0
            for file_path in component_dir.glob("*.json"):
                parse_result = self._parse_component_file(
                    file_path, model_class, id_field
                )
                if parse_result:
                    component_id, component_model = parse_result
                    target_dict[component_id] = component_model
                    loaded_count += 1
                else:
                    error_count += 1  # Error logged within _parse_component_file

            logger.debug(
                f"Loaded {loaded_count} components of type '{component_type}' from {component_dir}"
                + (f" ({error_count} errors)." if error_count else ".")
            )
        logger.debug("_load_all_components finished.")

    def load_project(self, project_config_file_path: Path) -> ProjectConfig:
        """
        Loads a project configuration file, resolving component references.

        Args:
            project_config_file_path: Path to the project JSON file.

        Returns:
            A fully resolved ProjectConfig object.

        Raises:
            FileNotFoundError: If the project file does not exist.
            RuntimeError: If JSON parsing fails or validation errors occur.
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

        project_name = project_data.get("name", "Unnamed Project")
        project_description = project_data.get("description")
        logger.debug(f"Processing project: '{project_name}'")

        # Helper function to resolve component references or use inline definitions
        def _resolve_components(
            project_key: str,
            component_dict: Dict[str, Any],
            model_class: type,
            id_field: str,
            type_name: str,
        ) -> Dict[str, Any]:
            resolved_items = {}
            item_references = project_data.get(project_key, [])
            if not isinstance(item_references, list):
                logger.warning(
                    f"'{project_key}' in project '{project_name}' is not a list. Skipping."
                )
                return {}

            for item_ref in item_references:
                component_id = None
                try:
                    if isinstance(item_ref, str):  # It's an ID reference
                        component_id = item_ref
                        if component_id in component_dict:
                            resolved_items[component_id] = component_dict[component_id]
                            logger.debug(
                                f"Resolved {type_name} component reference: '{component_id}'"
                            )
                        else:
                            logger.warning(
                                f"{type_name} component ID '{component_id}' referenced in project '{project_name}' not found in loaded components. Skipping."
                            )
                    elif isinstance(item_ref, dict):  # Inline definition
                        component_id = item_ref.get(id_field)
                        if not component_id:
                            logger.warning(
                                f"Inline {type_name} definition missing ID field '{id_field}' in project '{project_name}'. Skipping: {item_ref}"
                            )
                            continue

                        # Resolve paths if necessary before validation
                        if model_class == ClientConfig and "server_path" in item_ref:
                            item_ref["server_path"] = (
                                PROJECT_ROOT_DIR / item_ref["server_path"]
                            ).resolve()
                        if (
                            model_class == CustomWorkflowConfig
                            and "module_path" in item_ref
                        ):
                            item_ref["module_path"] = (
                                PROJECT_ROOT_DIR / item_ref["module_path"]
                            ).resolve()

                        inline_item = model_class(**item_ref)
                        # Decide precedence: Let inline definition override component if ID conflicts
                        if component_id in resolved_items:
                            logger.warning(
                                f"Inline {type_name} definition for '{component_id}' overrides previously resolved reference in project '{project_name}'."
                            )
                        resolved_items[component_id] = inline_item
                        logger.debug(
                            f"Loaded inline {type_name} definition: '{component_id}'"
                        )
                    else:
                        logger.warning(
                            f"Invalid {type_name} reference in project '{project_name}'. Expected string ID or dict definition. Got: {item_ref}"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to process {type_name} reference '{component_id or item_ref}' in project '{project_name}': {e}",
                        exc_info=True,
                    )
            return resolved_items

        # Resolve all component types
        resolved_clients = _resolve_components(
            "clients", self.component_clients, ClientConfig, "client_id", "Client"
        )
        resolved_llm_configs = _resolve_components(
            "llm_configs", self.component_llm_configs, LLMConfig, "llm_id", "LLMConfig"
        )
        resolved_agents = _resolve_components(
            "agent_configs", self.component_agents, AgentConfig, "name", "Agent"
        )
        resolved_simple_workflows = _resolve_components(
            "simple_workflow_configs",
            self.component_simple_workflows,
            WorkflowConfig,
            "name",
            "SimpleWorkflow",
        )
        resolved_custom_workflows = _resolve_components(
            "custom_workflow_configs",
            self.component_custom_workflows,
            CustomWorkflowConfig,
            "name",
            "CustomWorkflow",
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
            Exception
        ) as e:  # Catch Pydantic validation errors for the final ProjectConfig
            logger.error(
                f"Failed to validate final ProjectConfig for '{project_name}': {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Failed to validate final ProjectConfig for '{project_name}': {e}"
            ) from e

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
        json_data = model_instance.model_dump(mode="json")
        component_id = None  # We need the ID for logging warnings

        # Determine ID based on model type for logging
        if isinstance(model_instance, ClientConfig):
            component_id = model_instance.client_id
            if "server_path" in json_data and isinstance(
                json_data["server_path"], Path
            ):
                try:
                    json_data["server_path"] = str(
                        json_data["server_path"].relative_to(PROJECT_ROOT_DIR)
                    )
                except ValueError:
                    logger.warning(
                        f"Could not make server_path relative to project root for {component_id}. Storing absolute path."
                    )
                    json_data["server_path"] = str(json_data["server_path"])
        elif isinstance(model_instance, CustomWorkflowConfig):
            component_id = model_instance.name
            if "module_path" in json_data and isinstance(
                json_data["module_path"], Path
            ):
                try:
                    json_data["module_path"] = str(
                        json_data["module_path"].relative_to(PROJECT_ROOT_DIR)
                    )
                except ValueError:
                    logger.warning(
                        f"Could not make module_path relative to project root for {component_id}. Storing absolute path."
                    )
                    json_data["module_path"] = str(json_data["module_path"])
        # Add elif for other models if they contain Path fields that need conversion

        return json_data

    # --- Component CRUD Methods ---

    def list_component_files(self, component_type: str) -> List[str]:
        """Lists the JSON filenames for a given component type."""
        # Placeholder implementation
        logger.debug(f"Placeholder: list_component_files for {component_type}")
        component_dir = COMPONENT_TYPES_DIRS.get(component_type)
        if component_dir and component_dir.is_dir():
            return [f.name for f in component_dir.glob("*.json") if f.is_file()]
        return []

    def get_component_config(
        self, component_type: str, component_id: str
    ) -> Optional[Any]:
        """Gets the parsed configuration model for a specific component ID."""
        # Placeholder implementation - needs to map type to correct dict and model
        logger.debug(
            f"Placeholder: get_component_config for {component_type} / {component_id}"
        )
        component_map = {
            "clients": self.component_clients,
            "llm_configs": self.component_llm_configs,
            "agents": self.component_agents,
            "simple_workflows": self.component_simple_workflows,
            "custom_workflows": self.component_custom_workflows,
        }
        target_dict = component_map.get(component_type)
        if target_dict:
            return target_dict.get(component_id)
        return None

    def save_component_config(
        self, component_type: str, config_data: Dict[str, Any]
    ) -> Any:  # Return type could be the validated model or Dict for status
        """
        Saves (creates or updates) a component configuration JSON file and updates memory.

        Args:
            component_type: The type of component (e.g., 'agents', 'llm_configs').
            config_data: A dictionary representing the component's configuration.
                         Must include the appropriate ID field ('name' or 'llm_id' or 'client_id').

        Returns:
            The validated Pydantic model instance of the saved component, or raises an error.

        Raises:
            ValueError: If component_type is invalid, ID is missing, or validation fails.
            IOError: If writing the file fails.
            RuntimeError: For other unexpected errors.
        """
        logger.info(f"Attempting to save component config for type: {component_type}")
        component_map = {
            "clients": (ClientConfig, "client_id", self.component_clients),
            "llm_configs": (LLMConfig, "llm_id", self.component_llm_configs),
            "agents": (AgentConfig, "name", self.component_agents),
            "simple_workflows": (
                WorkflowConfig,
                "name",
                self.component_simple_workflows,
            ),
            "custom_workflows": (
                CustomWorkflowConfig,
                "name",
                self.component_custom_workflows,
            ),
        }

        if component_type not in component_map:
            raise ValueError(f"Invalid component type specified: {component_type}")

        model_class, id_field, target_dict = component_map[component_type]
        component_dir = COMPONENT_TYPES_DIRS.get(component_type)
        if not component_dir:
            # Should not happen if component_type is valid, but check defensively
            raise ValueError(
                f"Configuration error: No directory defined for component type '{component_type}'."
            )

        component_id = config_data.get(id_field)
        if not component_id or not isinstance(component_id, str):
            raise ValueError(
                f"Missing or invalid ID field ('{id_field}') in provided config data for type '{component_type}'."
            )

        # Construct filename based on ID
        filename = f"{component_id}.json"
        file_path = (component_dir / filename).resolve()

        # Security check: ensure path is still within the intended directory
        if not str(file_path).startswith(str(component_dir.resolve())):
            raise ValueError(
                f"Constructed file path '{file_path}' is outside the allowed directory '{component_dir}'."
            )

        try:
            # Create a copy to avoid modifying the original dict during path resolution
            data_to_validate = config_data.copy()

            # Resolve paths relative to project root *before* validation
            if model_class == ClientConfig and "server_path" in data_to_validate:
                sp = Path(data_to_validate["server_path"])
                if not sp.is_absolute():
                    data_to_validate["server_path"] = (PROJECT_ROOT_DIR / sp).resolve()
                else:
                    data_to_validate["server_path"] = sp.resolve()
            if (
                model_class == CustomWorkflowConfig
                and "module_path" in data_to_validate
            ):
                mp = Path(data_to_validate["module_path"])
                if not mp.is_absolute():
                    data_to_validate["module_path"] = (PROJECT_ROOT_DIR / mp).resolve()
                else:
                    data_to_validate["module_path"] = mp.resolve()

            # Validate data against the Pydantic model
            validated_model = model_class(**data_to_validate)

            # Prepare data for JSON serialization using the helper
            json_data = self._prepare_data_for_save(validated_model)

            # Write to file (pretty-printed)
            component_dir.mkdir(
                parents=True, exist_ok=True
            )  # Ensure dir exists before getting path
            file_path = self._get_component_file_path(
                component_type, component_id
            )  # Get path after ensuring dir exists
            with open(file_path, "w") as f:
                json.dump(json_data, f, indent=4)

            # Update in-memory dictionary
            target_dict[component_id] = validated_model
            logger.info(
                f"Successfully saved component '{component_id}' of type '{component_type}' to {file_path}"
            )
            return validated_model

        except ValidationError as e:
            logger.error(
                f"Validation failed for component '{component_id}' of type '{component_type}': {e}"
            )
            raise ValueError(f"Configuration validation failed: {e}") from e
        except IOError as e:
            logger.error(f"Failed to write component file {file_path}: {e}")
            raise IOError(f"Failed to write configuration file: {e}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error saving component '{component_id}' of type '{component_type}': {e}",
                exc_info=True,
            )
            raise RuntimeError(f"An unexpected error occurred during save: {e}") from e

    def delete_component_config(self, component_type: str, component_id: str) -> bool:
        """
        Deletes a component configuration JSON file and removes it from memory.

        Args:
            component_type: The type of component (e.g., 'agents', 'llm_configs').
            component_id: The unique identifier (name, llm_id, client_id) of the component.

        Returns:
            True if the component was successfully deleted (from memory and potentially filesystem),
            False otherwise.
        """
        logger.info(
            f"Attempting to delete component config for type: {component_type}, ID: {component_id}"
        )
        component_map = {
            "clients": (ClientConfig, "client_id", self.component_clients),
            "llm_configs": (LLMConfig, "llm_id", self.component_llm_configs),
            "agents": (AgentConfig, "name", self.component_agents),
            "simple_workflows": (
                WorkflowConfig,
                "name",
                self.component_simple_workflows,
            ),
            "custom_workflows": (
                CustomWorkflowConfig,
                "name",
                self.component_custom_workflows,
            ),
        }

        if component_type not in component_map:
            logger.error(
                f"Invalid component type specified for deletion: {component_type}"
            )
            return False  # Or raise ValueError? Returning False for API consistency.

        _model_class, _id_field, target_dict = component_map[component_type]
        component_dir = COMPONENT_TYPES_DIRS.get(component_type)
        if not component_dir:
            logger.error(
                f"Configuration error: No directory defined for component type '{component_type}'. Cannot delete."
            )
            return False

        try:
            file_path = self._get_component_file_path(component_type, component_id)
        except ValueError as e:
            logger.error(
                f"Cannot delete component '{component_id}' of type '{component_type}': {e}"
            )
            return False

        deleted_from_fs = False
        file_existed = False
        try:
            if file_path.is_file():
                file_existed = True
                file_path.unlink()
                logger.info(f"Successfully deleted component file: {file_path}")
                deleted_from_fs = True
            else:
                logger.warning(
                    f"Component file not found for deletion at {file_path}. Cannot delete from filesystem."
                )
                # If file doesn't exist, we consider FS part "successful" in terms of state change
                deleted_from_fs = (
                    True  # Treat non-existence as success for deletion intent
                )

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
