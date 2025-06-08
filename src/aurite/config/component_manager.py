import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Type, Union
import json
import importlib.resources
import importlib.util  # Added
from importlib.abc import Traversable

from pydantic import ValidationError, BaseModel

from .config_models import (
    ClientConfig,
    LLMConfig,
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)
from .config_utils import resolve_path_fields, relativize_path_fields

logger = logging.getLogger(__name__)

# Relative paths for component types.
# For user projects, this will be relative to current_project_root / 'config'.
# For packaged defaults, this will be relative to 'aurite.packaged' / 'component_configs'.
COMPONENT_SUBDIRS = {
    "mcp_servers": "mcp_servers",
    "llms": "llms",
    "agents": "agents",
    "simple_workflows": "workflows",
    "custom_workflows": "custom_workflows",
    "projects": "projects",  # For packaged project templates like prompt_validation
}

# Mapping component type to its model class and ID field name
COMPONENT_META = {
    "mcp_servers": (ClientConfig, "name"),
    "llms": (LLMConfig, "llm_id"),
    "agents": (AgentConfig, "name"),
    "simple_workflows": (WorkflowConfig, "name"),
    "custom_workflows": (CustomWorkflowConfig, "name"),
    # Projects are not typically managed as individual components by ComponentManager in the same way,
    # but we might load project *templates* from packaged/component_configs/projects.
    # For now, ProjectManager handles full project loading.
}


class ComponentManager:
    """
    Manages the discovery, loading, validation, and CRUD operations
    for reusable component configurations (Agents, LLMs, Clients, etc.).
    It now loads packaged defaults first, then allows loading of project-specific components.
    """

    def __init__(self):
        """Initializes the ComponentManager by loading packaged default components."""
        self.mcp_servers: Dict[str, ClientConfig] = {}
        self.llms: Dict[str, LLMConfig] = {}
        self.agents: Dict[str, AgentConfig] = {}
        self.simple_workflows: Dict[str, WorkflowConfig] = {}
        self.custom_workflows: Dict[str, CustomWorkflowConfig] = {}
        self.component_counts: Dict[str, int] = {}

        self._component_stores = {
            "mcp_servers": self.mcp_servers,
            "llms": self.llms,
            "agents": self.agents,
            "simple_workflows": self.simple_workflows,
            "custom_workflows": self.custom_workflows,
        }

        self._load_packaged_defaults()
        logger.debug(
            "ComponentManager initialized and packaged default components loaded."
        )

    def get_component_counts(self) -> Dict[str, int]:
        """Returns a dictionary of component types to their loaded counts."""
        return self.component_counts

    def _parse_component_file_content(
        self,
        file_content: str,
        model_class: Type,
        id_field: str,
        base_path_for_resolution: Path,  # Now expects a concrete Path
        file_identifier_for_logging: str,
    ) -> List[Any]:
        """
        Parses component JSON content (can be a single object or an array),
        validates items, resolves paths relative to base_path_for_resolution,
        and returns a list of parsed models.
        """
        parsed_models: List[Any] = []
        try:
            raw_content = json.loads(file_content)
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to decode JSON from {file_identifier_for_logging}: {e}"
            )
            return parsed_models

        items_to_parse = []
        if isinstance(raw_content, list):
            items_to_parse.extend(raw_content)
        elif isinstance(raw_content, dict):
            items_to_parse.append(raw_content)
        else:
            logger.error(
                f"{file_identifier_for_logging} contains neither a JSON object nor an array. Skipping."
            )
            return parsed_models

        for index, item_data in enumerate(items_to_parse):
            if not isinstance(item_data, dict):
                logger.warning(
                    f"Item at index {index} in {file_identifier_for_logging} is not a JSON object. Skipping."
                )
                continue

            try:
                # Path resolution is now simpler as we expect a concrete Path object.
                data_to_validate = resolve_path_fields(
                    item_data, model_class, base_path_for_resolution
                )
                component_model = model_class(**data_to_validate)
                parsed_models.append(component_model)
            except ValidationError as e:
                logger.error(
                    f"Validation failed for item at index {index} in {file_identifier_for_logging}: {e}"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error parsing item at index {index} in {file_identifier_for_logging}: {e}",
                    exc_info=True,
                )
        return parsed_models

    def _load_components_from_dir(
        self,
        component_type: str,
        model_class: Type,
        id_field: str,
        directory_path: Union[Path, Traversable],
        base_path_for_resolution: Union[Path, Traversable],
        is_override_allowed: bool = False,
    ):
        """
        Loads components of a specific type from a given directory.

        Args:
            component_type: The type of component (e.g., 'mcp_servers').
            model_class: The Pydantic model class for the component.
            id_field: The name of the ID field in the model.
            directory_path: The Path object for the directory to scan.
            base_path_for_resolution: The base path for resolving relative paths within component JSONs.
            is_override_allowed: If True, allows overriding already loaded components.
        """
        target_dict = self._component_stores.get(component_type)
        if target_dict is None:
            logger.error(f"No store for component type '{component_type}'. Skipping.")
            return

        if not directory_path.is_dir():
            logger.debug(
                f"Directory not found for {component_type}: {directory_path}. Skipping."
            )
            return

        loaded_count_for_type = self.component_counts.get(component_type, 0)
        error_count = 0

        logger.debug(f"Scanning {directory_path} for {component_type} components...")

        files_to_iterate: List[Union[Path, Traversable]] = []
        if isinstance(directory_path, Path):
            files_to_iterate = list(directory_path.glob("*.json"))
        elif hasattr(directory_path, "iterdir"):
            for item in directory_path.iterdir():
                if (
                    hasattr(item, "is_file")
                    and item.is_file()
                    and item.name.endswith(".json")
                ):
                    files_to_iterate.append(item)

        for file_path in files_to_iterate:
            if not file_path.is_file():
                continue
            try:
                file_content = file_path.read_text(encoding="utf-8")
                # Ensure the base path for resolution is a concrete Path object.
                # This handles the case where it might be a Traversable from importlib.
                concrete_base_path = (
                    base_path_for_resolution
                    if isinstance(base_path_for_resolution, Path)
                    else Path(str(base_path_for_resolution))
                )
                parsed_models_from_file = self._parse_component_file_content(
                    file_content,
                    model_class,
                    id_field,
                    concrete_base_path,
                    str(file_path),
                )

                for component_model in parsed_models_from_file:
                    component_id = getattr(component_model, id_field, None)
                    if not component_id or not isinstance(component_id, str):
                        logger.warning(
                            f"Parsed component from {file_path} has missing/invalid ID. Skipping."
                        )
                        error_count += 1
                        continue

                    if component_id in target_dict and not is_override_allowed:
                        logger.warning(
                            f"Duplicate component ID '{component_id}' (from file {file_path}) for type '{component_type}'. "
                            "Packaged default will be kept. User project component will override if loaded later with override flag."
                        )
                    else:
                        if component_id in target_dict and is_override_allowed:
                            logger.debug(
                                f"Overriding component '{component_id}' of type '{component_type}' from {file_path}."
                            )
                        target_dict[component_id] = component_model
                        loaded_count_for_type += 1
                        logger.debug(
                            f"Registered component '{component_id}' of type '{component_type}' from {file_path}"
                        )

            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
                error_count += 1

        self.component_counts[component_type] = loaded_count_for_type
        logger.debug(
            f"Finished loading for type '{component_type}' from {directory_path}. Total loaded: {loaded_count_for_type}."
            + (f" ({error_count} errors encountered)." if error_count else "")
        )

    def _load_packaged_defaults(self):
        """Loads default component configurations bundled with the package."""
        logger.debug("Loading packaged default component configurations...")
        try:
            # Use importlib.resources.files to get a Traversable object for the packaged data.
            # This is the modern, correct way to access package data files.
            packaged_root_trav = importlib.resources.files("aurite.packaged")
            packaged_configs_dir = packaged_root_trav.joinpath("component_configs")

            for component_type, (model_class, id_field) in COMPONENT_META.items():
                subdir_name = COMPONENT_SUBDIRS.get(component_type)
                if not subdir_name:
                    continue

                component_dir_path = packaged_configs_dir.joinpath(subdir_name)

                # The base path for resolving file paths within the JSONs is the packaged root itself.
                self._load_components_from_dir(
                    component_type,
                    model_class,
                    id_field,
                    component_dir_path,  # This is a Traversable
                    base_path_for_resolution=packaged_root_trav,  # Pass the Traversable
                    is_override_allowed=False,
                )
        except (ModuleNotFoundError, RuntimeError) as e:
            logger.error(
                f"Could not load packaged defaults: {e}. This may happen if the package is not installed correctly."
            )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while loading packaged defaults: {e}",
                exc_info=True,
            )
        logger.debug("Finished loading packaged defaults.")

    def load_project_components(self, project_root_path: Path):
        """
        Loads component configurations from a user's project directory.
        These can override packaged defaults if IDs match.
        """
        logger.debug(
            f"Loading project-specific components from: {project_root_path}..."
        )
        user_config_main_dir = (
            project_root_path / "config"
        )  # User components are in project_root/config/

        if not user_config_main_dir.is_dir():
            logger.info(
                f"User project config directory not found at {user_config_main_dir}. No project-specific components will be loaded."
            )
            return

        for component_type, (model_class, id_field) in COMPONENT_META.items():
            subdir_name = COMPONENT_SUBDIRS.get(component_type)
            if (
                not subdir_name
            ):  # Should not happen if COMPONENT_SUBDIRS is aligned with COMPONENT_META
                logger.warning(
                    f"No subdir defined for user component type '{component_type}'. Skipping."
                )
                continue

            component_dir_path = user_config_main_dir.joinpath(subdir_name)

            # For user project components, paths inside their JSONs
            # should be relative to the project_root_path.
            self._load_components_from_dir(
                component_type,
                model_class,
                id_field,
                component_dir_path,
                base_path_for_resolution=project_root_path,  # Resolve paths relative to user's project root
                is_override_allowed=True,  # User components override packaged defaults
            )
        logger.debug(
            f"Finished loading project-specific components from {project_root_path}."
        )

    def _get_component_file_path(
        self, component_type: str, component_id: str, project_root_path: Path
    ) -> Path:
        """Constructs and validates the file path for a component within a user's project."""
        user_config_main_dir = project_root_path / "config"
        subdir_name = COMPONENT_SUBDIRS.get(component_type)
        if not subdir_name:
            raise ValueError(
                f"Invalid component type for path construction: {component_type}"
            )

        component_dir = user_config_main_dir / subdir_name
        filename = f"{component_id}.json"
        file_path = component_dir / filename

        # Security check: Ensure path is within the project's config directory
        if not str(file_path.resolve()).startswith(str(user_config_main_dir.resolve())):
            raise ValueError(
                f"Constructed file path '{file_path}' is outside the allowed project config directory '{user_config_main_dir}'."
            )
        return file_path

    def _prepare_data_for_save(
        self, model_instance: Any, base_path_for_relativization: Path
    ) -> Dict[str, Any]:
        """Converts a Pydantic model to a dict, relativizing paths against base_path_for_relativization."""
        raw_model_dict = model_instance.model_dump(
            mode="json"
        )  # mode="json" handles Path, datetime etc.
        json_data_with_str_paths = relativize_path_fields(
            raw_model_dict, type(model_instance), base_path_for_relativization
        )
        return json_data_with_str_paths

    def get_component_config(
        self, component_type: str, component_id: str
    ) -> Optional[Any]:
        target_dict = self._component_stores.get(component_type)
        if target_dict is not None:
            return target_dict.get(component_id)
        logger.warning(f"Attempted to get component of unknown type: {component_type}")
        return None

    def list_components(self, component_type: str) -> List[Any]:
        target_dict = self._component_stores.get(component_type)
        if target_dict is not None:
            return list(target_dict.values())
        logger.warning(
            f"Attempted to list components of unknown type: {component_type}"
        )
        return []

    # Convenience accessors
    def get_mcp_server(self, server_name: str) -> Optional[ClientConfig]:
        return self.get_component_config("mcp_servers", server_name)  # type: ignore

    def get_llm(self, llm_id: str) -> Optional[LLMConfig]:
        return self.get_component_config("llms", llm_id)  # type: ignore

    def get_agent(self, agent_name: str) -> Optional[AgentConfig]:
        return self.get_component_config("agents", agent_name)  # type: ignore

    def get_simple_workflow(self, workflow_name: str) -> Optional[WorkflowConfig]:
        return self.get_component_config("simple_workflows", workflow_name)  # type: ignore

    def get_custom_workflow(self, workflow_name: str) -> Optional[CustomWorkflowConfig]:
        return self.get_component_config("custom_workflows", workflow_name)  # type: ignore

    def list_mcp_servers(self) -> List[ClientConfig]:
        return self.list_components("mcp_servers")  # type: ignore

    def list_llms(self) -> List[LLMConfig]:
        return self.list_components("llms")  # type: ignore

    def list_agents(self) -> List[AgentConfig]:
        return self.list_components("agents")  # type: ignore

    def list_simple_workflows(self) -> List[WorkflowConfig]:
        return self.list_components("simple_workflows")  # type: ignore

    def list_custom_workflows(self) -> List[CustomWorkflowConfig]:
        return self.list_components("custom_workflows")  # type: ignore

    def list_component_files(
        self, component_type: str, project_root_path: Path
    ) -> List[str]:
        """Lists JSON filenames for a component type within a user's project."""
        user_config_main_dir = project_root_path / "config"
        subdir_name = COMPONENT_SUBDIRS.get(component_type)
        if not subdir_name:
            logger.error(f"Invalid component type for listing files: {component_type}")
            return []

        component_dir = user_config_main_dir / subdir_name
        if not component_dir.is_dir():
            logger.warning(
                f"Component directory not found for type '{component_type}' at {component_dir}. Returning empty list."
            )
            return []
        try:
            return sorted([f.name for f in component_dir.glob("*.json") if f.is_file()])
        except Exception as e:
            logger.error(f"Error listing files in {component_dir}: {e}", exc_info=True)
            return []

    def _save_component_to_file(
        self,
        file_path: Path,
        data_to_save: Union[Dict[str, Any], List[Dict[str, Any]]],
        component_id_for_log: str,  # For single save
        component_type_for_log: str,  # For single save
    ):
        """Helper to write component data to a file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(data_to_save, f, indent=4)
            logger.info(f"Successfully saved component(s) to {file_path}")
        except IOError as e:
            logger.error(f"Failed to write component file {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error saving component(s) to {file_path}: {e}",
                exc_info=True,
            )
            raise

    def save_component_config(
        self, component_type: str, config_data: Dict[str, Any], project_root_path: Path
    ) -> Any:
        """Saves (creates/updates) a single component config in the user's project."""
        target_dict = self._component_stores.get(component_type)
        meta = COMPONENT_META.get(component_type)
        if target_dict is None or meta is None:
            raise ValueError(f"Invalid component type: {component_type}")

        model_class, id_field = meta
        component_id = config_data.get(id_field)
        if not component_id or not isinstance(component_id, str):
            raise ValueError(
                f"Missing/invalid ID field '{id_field}' for type '{component_type}'."
            )

        try:
            file_path = self._get_component_file_path(
                component_type, component_id, project_root_path
            )
            data_to_validate = resolve_path_fields(
                config_data, model_class, project_root_path
            )
            validated_model = model_class(**data_to_validate)
            json_data = self._prepare_data_for_save(validated_model, project_root_path)

            self._save_component_to_file(
                file_path, json_data, component_id, component_type
            )

            target_dict[component_id] = validated_model  # Update in-memory store
            self.component_counts[component_type] = (
                self.component_counts.get(component_type, 0) + 1
            )
            return validated_model
        except ValidationError as e:
            logger.error(
                f"Validation failed for '{component_id}' ({component_type}): {e}"
            )
            raise ValueError(f"Config validation failed: {e}") from e
        except (
            Exception
        ) as e:  # Catches ValueError from _get_component_file_path, IOError from _save
            logger.error(
                f"Error saving component '{component_id}' ({component_type}): {e}",
                exc_info=True,
            )
            raise

    def delete_component_config(
        self, component_type: str, component_id: str, project_root_path: Path
    ) -> bool:
        """Deletes a component config file from the user's project and memory."""
        target_dict = self._component_stores.get(component_type)
        if target_dict is None:
            logger.error(f"Invalid component type for deletion: {component_type}")
            return False

        try:
            file_path = self._get_component_file_path(
                component_type, component_id, project_root_path
            )
        except ValueError as e:
            logger.error(
                f"Cannot get file path for component '{component_id}' ({component_type}): {e}"
            )
            return False  # If path is invalid, can't proceed with FS deletion

        deleted_from_fs = False
        if file_path.is_file():
            try:
                file_path.unlink()
                logger.info(f"Successfully deleted component file: {file_path}")
                deleted_from_fs = True
            except OSError as e:
                logger.error(
                    f"Error deleting component file {file_path}: {e}", exc_info=True
                )
                return False  # If file deletion fails, do not remove from memory
        else:
            logger.warning(
                f"Component file not found for deletion at {file_path}. Assuming success for FS part."
            )
            deleted_from_fs = True  # Treat as success if file wasn't there

        if component_id in target_dict:
            del target_dict[component_id]
            self.component_counts[component_type] = (
                self.component_counts.get(component_type, 1) - 1
            )
            logger.info(
                f"Removed component '{component_id}' ({component_type}) from memory."
            )
            return True

        # If not in memory, but FS operation was considered successful (file deleted or not found)
        return deleted_from_fs

    def save_components_to_file(
        self,
        component_type: str,
        components_data: List[Union[Dict[str, Any], BaseModel]],
        filename: str,
        project_root_path: Path,
        overwrite: bool = True,
    ) -> List[Any]:
        """Saves a list of component configs to a single JSON file in the user's project."""
        meta = COMPONENT_META.get(component_type)
        target_dict = self._component_stores.get(component_type)
        if meta is None or target_dict is None:
            raise ValueError(f"Invalid component type: {component_type}")

        model_class, id_field = meta

        user_config_main_dir = project_root_path / "config"
        subdir_name = COMPONENT_SUBDIRS.get(component_type)
        if not subdir_name:
            raise ValueError(f"No subdir for component type '{component_type}'")

        component_dir = user_config_main_dir / subdir_name
        file_path = (component_dir / filename).resolve()

        if not str(file_path).startswith(str(component_dir.resolve())):
            raise ValueError(
                f"File path '{file_path}' is outside allowed dir '{component_dir}'."
            )

        if not overwrite and file_path.exists():
            raise FileExistsError(f"Component file {file_path} already exists.")

        validated_models: List[Any] = []
        data_to_save_list: List[Dict[str, Any]] = []

        for item_data_raw in components_data:
            item_dict: Dict[str, Any]
            if isinstance(item_data_raw, BaseModel):
                item_dict = item_data_raw.model_dump(mode="json")
            else:
                item_dict = item_data_raw

            if not isinstance(item_dict, dict):
                continue

            try:
                resolved_item_data = resolve_path_fields(
                    item_dict, model_class, project_root_path
                )
                model_instance = model_class(**resolved_item_data)
                validated_models.append(model_instance)
                data_for_json = self._prepare_data_for_save(
                    model_instance, project_root_path
                )
                data_to_save_list.append(data_for_json)
            except ValidationError as e:
                logger.error(
                    f"Validation failed for item in '{filename}' ({component_type}): {e}. Skipping."
                )
            except Exception as e:
                logger.error(
                    f"Error processing item for '{filename}' ({component_type}): {e}. Skipping.",
                    exc_info=True,
                )

        if not data_to_save_list and components_data:  # Input had data, but all failed
            logger.warning(
                f"No valid components to save in {filename} for {component_type}. File not written."
            )
            return []

        self._save_component_to_file(
            file_path, data_to_save_list, filename, component_type
        )

        # Update in-memory store
        for model in validated_models:
            component_id = getattr(model, id_field, None)
            if component_id and isinstance(component_id, str):
                if component_id not in target_dict:
                    self.component_counts[component_type] = (
                        self.component_counts.get(component_type, 0) + 1
                    )
                target_dict[component_id] = model
        return validated_models
