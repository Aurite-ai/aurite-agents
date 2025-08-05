import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ..models.api.responses import ComponentCreateResponse
from ..storage.db.db_manager import StorageManager
from .config_utils import find_anchor_files
from .file_manager import FileManager

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import toml

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages the discovery, loading, and validation of configurations
    from various sources and formats in a hierarchical context.
    """

    def __init__(self, start_dir: Optional[Path] = None):
        """
        Initializes the ConfigManager, automatically discovering the context
        from the start_dir or current working directory.
        """
        start_path = start_dir if start_dir else Path.cwd()
        self.context_paths: List[Path] = find_anchor_files(start_path)
        self.project_root: Optional[Path] = None
        self.workspace_root: Optional[Path] = None
        self.project_name: Optional[str] = None
        self.workspace_name: Optional[str] = None
        self.llm_validations: dict[str, datetime | None] = {}

        # Identify workspace and project roots by inspecting the anchor files
        for anchor_path in self.context_paths:
            try:
                with open(anchor_path, "rb") as f:
                    settings = tomllib.load(f).get("aurite", {})
                context_type = settings.get("type")
                if context_type == "project":
                    self.project_root = anchor_path.parent
                    self.project_name = self.project_root.name
                elif context_type == "workspace":
                    self.workspace_root = anchor_path.parent
                    self.workspace_name = self.workspace_root.name
            except (tomllib.TOMLDecodeError, IOError) as e:
                logger.error(f"Could not parse {anchor_path} during context init: {e}")

        # If the workspace is the starting context, there is no project_root
        # unless we are inside a nested project directory.
        if self.workspace_root == start_path.resolve():
            self.project_root = None
            self.project_name = None
        # Fallback for a standalone project not in a workspace
        elif not self.project_root and self.context_paths:
            self.project_root = self.context_paths[0].parent
            self.project_name = self.project_root.name

        self._config_sources: List[tuple[Path, Path]] = []
        self._component_index: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._force_refresh = os.getenv("AURITE_CONFIG_FORCE_REFRESH", "true").lower() == "true"
        self._db_enabled = os.getenv("AURITE_ENABLE_DB", "false").lower() == "true"
        self._storage_manager: Optional[StorageManager] = None
        self._file_manager: Optional[FileManager] = None

        if self._db_enabled:
            logger.info("Database mode is enabled. Loading configuration from DB.")
            self._storage_manager = StorageManager()
            self._component_index = self._storage_manager.load_index_from_db()
        else:
            logger.info("File-based mode is enabled. Loading configuration from files.")
            self._initialize_sources()
            self._build_component_index()

            # Initialize FileManager with our configuration sources
            self._file_manager = FileManager(
                config_sources=self._config_sources,
                project_root=self.project_root,
                workspace_root=self.workspace_root,
                project_name=self.project_name,
                workspace_name=self.workspace_name,
            )

    def _initialize_sources(self):
        """Initializes the configuration source paths based on the hierarchical context."""
        logger.debug("Initializing configuration sources...")
        config_sources: List[tuple[Path, Path]] = []
        processed_paths = set()

        # Phase 1: Add current context configs (highest priority)
        if self.project_root:
            # We're in a project - add project configs first
            logger.debug(f"Starting from project: {self.project_name}")
            project_anchor = self.project_root / ".aurite"
            if project_anchor.is_file():
                try:
                    with open(project_anchor, "rb") as f:
                        settings = tomllib.load(f).get("aurite", {})
                    for rel_path in settings.get("include_configs", []):
                        resolved_path = (self.project_root / rel_path).resolve()
                        if resolved_path.is_dir() and resolved_path not in processed_paths:
                            config_sources.append((resolved_path, self.project_root))
                            processed_paths.add(resolved_path)
                            logger.debug(f"Added project config: {resolved_path}")
                except (tomllib.TOMLDecodeError, IOError) as e:
                    logger.error(f"Could not parse project .aurite: {e}")

        # Phase 2: Add workspace configs (second priority)
        if self.workspace_root:
            workspace_anchor = self.workspace_root / ".aurite"
            if workspace_anchor.is_file():
                try:
                    with open(workspace_anchor, "rb") as f:
                        settings = tomllib.load(f).get("aurite", {})

                    # Add workspace's own configs
                    for rel_path in settings.get("include_configs", []):
                        resolved_path = (self.workspace_root / rel_path).resolve()
                        if resolved_path.is_dir() and resolved_path not in processed_paths:
                            config_sources.append((resolved_path, self.workspace_root))
                            processed_paths.add(resolved_path)
                            logger.debug(f"Added workspace config: {resolved_path}")

                    # Phase 3: Add other projects' configs (lower priority)
                    for project_rel_path in settings.get("projects", []):
                        project_root = (self.workspace_root / project_rel_path).resolve()

                        # Skip the current project (already added in Phase 1)
                        if self.project_root and project_root == self.project_root:
                            continue

                        project_anchor = project_root / ".aurite"
                        if project_anchor.is_file():
                            try:
                                with open(project_anchor, "rb") as pf:
                                    p_settings = tomllib.load(pf).get("aurite", {})
                                for p_rel_path in p_settings.get("include_configs", []):
                                    resolved_p_path = (project_root / p_rel_path).resolve()
                                    if resolved_p_path.is_dir() and resolved_p_path not in processed_paths:
                                        config_sources.append((resolved_p_path, project_root))
                                        processed_paths.add(resolved_p_path)
                                        logger.debug(f"Added other project config: {resolved_p_path}")
                            except (tomllib.TOMLDecodeError, IOError) as e:
                                logger.error(f"Could not parse project {project_root} .aurite: {e}")

                except (tomllib.TOMLDecodeError, IOError) as e:
                    logger.error(f"Could not parse workspace .aurite: {e}")

        # Phase 4: Global user config is always last
        user_config_root = Path.home() / ".aurite"
        if user_config_root.is_dir():
            config_sources.append((user_config_root, user_config_root))
            logger.debug(f"Added user config: {user_config_root}")

        self._config_sources = config_sources
        logger.debug(f"Final configuration source order: {[str(s[0]) for s in self._config_sources]}")

    def _build_component_index(self):
        """Builds an index of all available components, respecting priority."""
        logger.debug("Building component index...")
        self._component_index = {}

        for source_path, context_root in self._config_sources:
            if not source_path.is_dir():
                logger.warning(f"Config source path {source_path} is not a directory.")
                continue

            for config_file in source_path.rglob("*.json"):
                self._parse_and_index_file(config_file, context_root)
            for config_file in source_path.rglob("*.yaml"):
                self._parse_and_index_file(config_file, context_root)
            for config_file in source_path.rglob("*.yml"):
                self._parse_and_index_file(config_file, context_root)

    def _parse_and_index_file(self, config_file: Path, context_root: Path):
        """
        Parses a config file containing a list of components and adds them to the index.
        """
        try:
            with config_file.open("r", encoding="utf-8") as f:
                if config_file.suffix == ".json":
                    content = json.load(f)
                else:
                    content = yaml.safe_load(f)
        except (IOError, json.JSONDecodeError, yaml.YAMLError) as e:
            logger.error(f"Failed to load or parse config file {config_file}: {e}")
            return

        if not isinstance(content, list):
            logger.warning(f"Skipping config file {config_file}: root is not a list of components.")
            return

        for component_data in content:
            if not isinstance(component_data, dict):
                continue

            component_type = component_data.get("type")
            component_id = component_data.get("name")

            if not component_type or not component_id:
                logger.warning(f"Skipping component in {config_file} due to missing 'type' or 'name'.")
                continue

            self._component_index.setdefault(component_type, {})

            # Honor the priority of sources: if a component is already indexed, skip
            if component_id in self._component_index.get(component_type, {}):
                continue

            component_data["_source_file"] = str(config_file.resolve())
            component_data["_context_path"] = str(context_root.resolve())

            if self.workspace_root and context_root == self.workspace_root:
                component_data["_context_level"] = "workspace"
                component_data["_workspace_name"] = self.workspace_name
            elif self.project_root and context_root == self.project_root:
                component_data["_context_level"] = "project"
                component_data["_project_name"] = self.project_name
                if self.workspace_name:
                    component_data["_workspace_name"] = self.workspace_name
            elif context_root == Path.home() / ".aurite":
                component_data["_context_level"] = "user"
            else:
                # It's a project within a workspace, but not the CWD project
                component_data["_context_level"] = "project"
                component_data["_project_name"] = context_root.name
                if self.workspace_name:
                    component_data["_workspace_name"] = self.workspace_name

            self._component_index.setdefault(component_type, {})[component_id] = component_data
            logger.debug(f"Indexed '{component_id}' ({component_type}) from {config_file}")

    def _resolve_paths_in_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves relative paths in a component's configuration data."""
        context_path_str = config_data.get("_context_path")
        if not context_path_str:
            return config_data

        context_path = Path(context_path_str)
        resolved_data = config_data.copy()
        component_type = resolved_data.get("type")

        if component_type == "mcp_server":
            if "server_path" in resolved_data and resolved_data["server_path"]:
                path = Path(resolved_data["server_path"])
                if not path.is_absolute():
                    resolved_data["server_path"] = (context_path / path).resolve()

        elif component_type == "custom_workflow":
            if "module_path" in resolved_data and resolved_data["module_path"]:
                # Convert module dot-path to a file path
                module_str = resolved_data["module_path"]
                # This assumes the module path is relative to the context root
                # e.g., "custom_workflows.my_workflow" -> custom_workflows/my_workflow.py
                module_as_path = Path(module_str.replace(".", "/")).with_suffix(".py")

                path = context_path / module_as_path
                if path.exists():
                    resolved_data["module_path"] = path.resolve()
                else:
                    # Fallback for if the path was already a direct file path
                    path = Path(module_str)
                    if not path.is_absolute():
                        resolved_data["module_path"] = (context_path / path).resolve()
                    else:
                        resolved_data["module_path"] = path
        elif component_type == "llm":
            # return last validated timestamp for llms
            resolved_data["validated_at"] = self.llm_validations.get(resolved_data["name"], None)

        return resolved_data

    def get_config(self, component_type: str, component_id: str) -> Optional[Dict[str, Any]]:
        if self._force_refresh:
            self.refresh()

        config = self._component_index.get(component_type, {}).get(component_id)
        if config:
            return self._resolve_paths_in_config(config)
        return None

    def list_configs(self, component_type: str) -> List[Dict[str, Any]]:
        if self._force_refresh:
            self.refresh()

        configs = self._component_index.get(component_type, {}).values()
        return [self._resolve_paths_in_config(c) for c in configs]

    def get_all_configs(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        if self._force_refresh:
            self.refresh()
        return self._component_index

    def get_component_index(self) -> List[Dict[str, Any]]:
        """
        Returns a flattened list of all indexed components, with their context.
        """
        if self._force_refresh:
            self.refresh()

        flat_list = []
        for comp_type, components in self._component_index.items():
            for comp_name, config in components.items():
                item = {
                    "name": comp_name,
                    "component_type": comp_type,
                    "project_name": config.get("_project_name"),
                    "workspace_name": config.get("_workspace_name"),
                    "source_file": config.get("_source_file"),
                    "config": {k: v for k, v in config.items() if not k.startswith("_")},
                }
                flat_list.append(item)
        return flat_list

    def refresh(self):
        logger.debug("Refreshing configuration index...")
        # Preserve llm_validations across refresh
        preserved_validations = self.llm_validations.copy()
        self.__init__()
        self.llm_validations = preserved_validations

    def register_component_in_memory(self, component_type: str, config: Dict[str, Any]):
        """
        Registers a component configuration directly into the in-memory index.
        This is useful for testing or programmatic registration in notebooks.
        These components have the highest priority.
        """
        component_id = config.get("name")
        if not component_id:
            logger.error("Cannot register component in memory: 'name' is missing.")
            return

        # Ensure the component type exists in the index
        self._component_index.setdefault(component_type, {})

        # Add or overwrite the component in the index
        # We can add a special marker to indicate it's an in-memory registration
        config["_source_file"] = "in-memory"
        config["_context_level"] = "programmatic"
        self._component_index[component_type][component_id] = config
        logger.debug(f"Programmatically registered '{component_id}' ({component_type}).")

    def list_config_sources(self) -> List[Dict[str, Any]]:
        """
        List all configuration source directories with context information.
        NOTE: This operation is only supported in file-based mode.
        """
        if self._db_enabled or not self._file_manager:
            logger.warning("Listing config sources is only available in file-based mode.")
            return []
        if self._force_refresh:
            self.refresh()
        return self._file_manager.list_config_sources()

    def list_config_files(self, source_name: str) -> List[str]:
        """
        List all configuration files for a specific source.
        NOTE: This operation is only supported in file-based mode.
        """
        if self._db_enabled or not self._file_manager:
            logger.warning("Listing config files is only available in file-based mode.")
            return []
        if self._force_refresh:
            self.refresh()
        return self._file_manager.list_config_files(source_name)

    def get_file_content(self, source_name: str, relative_path: str) -> Optional[str]:
        """
        Get the content of a specific configuration file.
        NOTE: This operation is only supported in file-based mode.
        """
        if self._db_enabled or not self._file_manager:
            logger.warning("Getting file content is only available in file-based mode.")
            return None
        if self._force_refresh:
            self.refresh()
        return self._file_manager.get_file_content(source_name, relative_path)

    def create_config_file(self, source_name: str, relative_path: str, content: str) -> bool:
        """
        Create a new configuration file.
        NOTE: This operation is only supported in file-based mode.
        """
        if self._db_enabled or not self._file_manager:
            logger.warning("Creating config files is only available in file-based mode.")
            return False
        if self._force_refresh:
            self.refresh()
        return self._file_manager.create_config_file(source_name, relative_path, content)

    def update_config_file(self, source_name: str, relative_path: str, content: str) -> bool:
        """
        Update an existing configuration file.
        NOTE: This operation is only supported in file-based mode.
        """
        if self._db_enabled or not self._file_manager:
            logger.warning("Updating config files is only available in file-based mode.")
            return False
        if self._force_refresh:
            self.refresh()
        return self._file_manager.update_config_file(source_name, relative_path, content)

    def delete_config_file(self, source_name: str, relative_path: str) -> bool:
        """
        Delete an existing configuration file.
        NOTE: This operation is only supported in file-based mode.
        """
        if self._db_enabled or not self._file_manager:
            logger.warning("Deleting config files is only available in file-based mode.")
            return False
        if self._force_refresh:
            self.refresh()
        return self._file_manager.delete_config_file(source_name, relative_path)

    def update_component(self, component_type: str, component_name: str, new_config: Dict[str, Any]) -> bool:
        """
        Updates a component configuration by writing back to its source file or the database.
        """
        if self._db_enabled:
            if not self._storage_manager:
                logger.error("StorageManager not initialized. Cannot update component in DB mode.")
                return False
            try:
                # The _upsert_component method is on StorageManager, not ConfigManager
                with self._storage_manager.get_db_session() as db:
                    if db:
                        self._storage_manager._upsert_component(db, component_type, new_config)
                self.refresh()  # Refresh the in-memory index
                return True
            except Exception as e:
                logger.error(f"Failed to update component '{component_name}' in database: {e}")
                return False

        # File-based logic
        existing_config = self.get_config(component_type, component_name)
        if not existing_config:
            logger.error(f"Component '{component_name}' of type '{component_type}' not found for update.")
            return False

        source_file_path = Path(existing_config["_source_file"])
        source_info = next((s for s in self.list_config_sources() if source_file_path.is_relative_to(s["path"])), None)
        if not source_info:
            source_info = next(
                (s for s in self.list_config_sources() if str(source_file_path).startswith(s["path"])), None
            )
        if not source_info:
            logger.error(f"Could not determine source for file {source_file_path}")
            return False

        source_name = source_info.get("project_name") or source_info.get("workspace_name")
        if not source_name:
            logger.error(f"Could not determine source name for file {source_file_path}")
            return False
        relative_path = source_file_path.relative_to(source_info["path"])

        # Read the whole file, update the specific component, and write it back
        file_content_str = self.get_file_content(source_name, str(relative_path))
        if file_content_str is None:
            return False

        file_format = self._file_manager._detect_file_format(source_file_path)
        if file_format == "json":
            file_data = json.loads(file_content_str)
        else:
            file_data = yaml.safe_load(file_content_str)

        component_found = False
        for i, comp in enumerate(file_data):
            if comp.get("name") == component_name and comp.get("type") == component_type:
                new_config_with_type = new_config.copy()
                new_config_with_type["type"] = component_type
                file_data[i] = new_config_with_type
                component_found = True
                break

        if not component_found:
            return False

        if file_format == "json":
            updated_content = json.dumps(file_data, indent=2)
        else:
            updated_content = yaml.safe_dump(file_data)

        success = self.update_config_file(source_name, str(relative_path), updated_content)

        # Reset LLM validation entry to None if an LLM component was updated
        if success and component_type == "llm":
            self.llm_validations[component_name] = None
            logger.debug(f"Reset validation entry for LLM '{component_name}' due to configuration update.")

        return success

    def _determine_default_context(self) -> Optional[str]:
        """
        Determine the default context for component creation with clear logging.
        Uses the highest priority configuration source available.
        Returns:
            The context name to use, or None if no valid context found
        """
        if self.project_name:
            logger.info(f"Using current project context: {self.project_name}")
            return self.project_name

        if self.workspace_name:
            if self._db_enabled or not self._file_manager:
                # In DB mode, we can't determine context from file sources.
                # Default to workspace if no project is active.
                logger.info(f"Using workspace context: {self.workspace_name}")
                return self.workspace_name

            sources = self._file_manager.list_config_sources()
            project_sources = [s for s in sources if s["context"] == "project"]

            if len(project_sources) == 0:
                logger.info(f"Using workspace context: {self.workspace_name}")
                return self.workspace_name
            elif len(project_sources) == 1:
                project_name = project_sources[0].get("project_name")
                logger.info(f"Using single available project: {project_name}")
                return project_name
            else:
                # Multiple projects - use highest priority (first in list)
                project_name = project_sources[0].get("project_name")
                available_projects = [s.get("project_name") for s in project_sources]
                logger.info(f"Multiple projects available. Using highest priority: {project_name}")
                logger.debug(f"Available projects in priority order: {available_projects}")
                return project_name

        return None

    def create_component(
        self,
        component_type: str,
        component_config: Dict[str, Any],
        project: Optional[str] = None,
        workspace: bool = False,
        file_path: Optional[str] = None,
    ) -> Optional[ComponentCreateResponse]:
        # Step 1: Determine context
        context_name = None
        if workspace:
            context_name = self.workspace_name
            logger.info(f"Using explicitly specified workspace context: {context_name}")
        elif project:
            context_name = project
            logger.info(f"Using explicitly specified project context: {context_name}")
        else:
            # Auto-detect context using enhanced logic
            context_name = self._determine_default_context()

        if not context_name:
            logger.error("Could not determine a valid context for component creation.")
            return None

        # Step 2 & 3: Add component to file or DB
        if self._db_enabled:
            if not self._storage_manager:
                logger.error("StorageManager not initialized. Cannot create component in DB mode.")
                return None
            # In DB mode, we just upsert the component.
            # The concept of a "file" doesn't apply.
            with self._storage_manager.get_db_session() as db:
                if db:
                    self._storage_manager._upsert_component(db, component_type, component_config)
        else:
            if not self._file_manager:
                logger.error("FileManager not initialized. Cannot create component in file-based mode.")
                return None
            target_file = self._file_manager.find_or_create_component_file(component_type, context_name, file_path)
            if not target_file:
                return None
            success = self._file_manager.add_component_to_file(target_file, component_config)
            if not success:
                return None

        # set newly created components to not validated
        if component_type == "llm":
            self.llm_validations[component_config["name"]] = None

        # Refresh index to include the new component
        self.refresh()

        # Get the full component from the index to ensure we have the complete, resolved version
        newly_created_component = self.get_config(component_type, component_config["name"])

        if not newly_created_component:
            logger.error(f"Could not retrieve newly created component '{component_config['name']}' after creation.")
            # This case should be rare, but it's a safeguard.
            # We can still return a success message but with a partial component.
            return ComponentCreateResponse(
                message="Component created successfully, but failed to retrieve full data.",
                component=component_config,
            )

        return ComponentCreateResponse(
            message="Component created successfully",
            component=newly_created_component,
        )

    def delete_config(self, component_type: str, component_name: str) -> bool:
        """
        Deletes a component configuration from its source file or the database.
        """
        if self._db_enabled:
            if not self._storage_manager:
                logger.error("StorageManager not initialized. Cannot delete component in DB mode.")
                return False
            try:
                success = self._storage_manager.delete_component(component_name)
                if success:
                    self.refresh()  # Refresh the in-memory index
                return success
            except Exception as e:
                logger.error(f"Failed to delete component '{component_name}' from database: {e}")
                return False

        # File-based logic
        try:
            # Find the existing component to get its source file
            existing_config = self._component_index.get(component_type, {}).get(component_name)

            if not existing_config:
                logger.error(f"Component '{component_name}' of type '{component_type}' not found for deletion.")
                return False

            source_file_path = existing_config.get("_source_file")
            if not source_file_path:
                logger.error(f"No source file found for component '{component_name}'.")
                return False

            source_file = Path(source_file_path)
            if not source_file.exists():
                logger.error(f"Source file {source_file} does not exist.")
                return False

            # Load the current file content
            try:
                with source_file.open("r", encoding="utf-8") as f:
                    if source_file.suffix == ".json":
                        file_content = json.load(f)
                    else:
                        file_content = yaml.safe_load(f)
            except (IOError, json.JSONDecodeError, yaml.YAMLError) as e:
                logger.error(f"Failed to load source file {source_file}: {e}")
                return False

            if not isinstance(file_content, list):
                logger.error(f"Source file {source_file} does not contain a list of components.")
                return False

            # Find and remove the component from the file content
            component_found = False
            for i, component in enumerate(file_content):
                if (
                    isinstance(component, dict)
                    and component.get("name") == component_name
                    and component.get("type") == component_type
                ):
                    file_content.pop(i)
                    component_found = True
                    break

            if not component_found:
                logger.error(f"Component '{component_name}' not found in source file {source_file}.")
                return False

            # If the file is now empty, delete it
            if not file_content:
                try:
                    source_file.unlink()
                    logger.info(f"Deleted empty config file {source_file}")
                except IOError as e:
                    logger.error(f"Failed to delete empty config file {source_file}: {e}")
                    return False
            else:
                # Write the updated content back to the file
                try:
                    with source_file.open("w", encoding="utf-8") as f:
                        if source_file.suffix == ".json":
                            json.dump(file_content, f, indent=2, ensure_ascii=False)
                        else:
                            yaml.safe_dump(file_content, f, default_flow_style=False, allow_unicode=True)

                    logger.info(f"Successfully deleted component '{component_name}' from {source_file}")
                except (IOError, json.JSONDecodeError, yaml.YAMLError) as e:
                    logger.error(f"Failed to write updated config to {source_file}: {e}")
                    return False

            # Remove from the in-memory index
            if component_name in self._component_index.get(component_type, {}):
                del self._component_index[component_type][component_name]
                # If this was the last component of this type, remove the type entry
                if not self._component_index[component_type]:
                    del self._component_index[component_type]

            return True

        except Exception as e:
            logger.error(f"Unexpected error deleting component '{component_name}': {e}")
            return False

    def validate_component(self, component_type: str, component_id: str) -> Tuple[bool, List[str]]:
        """
        Validates a component's configuration using Pydantic models.

        Args:
            component_type: The type of component to validate.
            component_id: The ID of the component to validate.

        Returns:
            A tuple containing a boolean indicating if the component is valid,
            and a list of validation error messages.
        """
        config = self.get_config(component_type, component_id)
        if not config:
            return False, [f"Component '{component_id}' of type '{component_type}' not found."]

        return self._validate_component_config(component_type, config)

    def _validate_component_config(self, component_type: str, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates a component configuration against its Pydantic model.

        Args:
            component_type: The type of component to validate.
            config: The component configuration to validate.

        Returns:
            A tuple containing a boolean indicating if the component is valid,
            and a list of validation error messages.
        """
        from aurite.lib.models import AgentConfig, ClientConfig, CustomWorkflowConfig, LLMConfig, WorkflowConfig

        # Map component types to their Pydantic models
        model_map = {
            "agent": AgentConfig,
            "llm": LLMConfig,
            "mcp_server": ClientConfig,
            "linear_workflow": WorkflowConfig,
            "custom_workflow": CustomWorkflowConfig,
        }

        model_class = model_map.get(component_type)
        if not model_class:
            return False, [f"No validation model found for component type '{component_type}'"]

        try:
            # Remove internal fields that shouldn't be validated
            clean_config = {k: v for k, v in config.items() if not k.startswith("_")}

            # Validate using Pydantic model
            model_class(**clean_config)
            return True, []

        except Exception as e:
            # Parse Pydantic validation errors into readable messages
            errors = []
            if hasattr(e, "errors"):
                for error in e.errors():
                    field_path = " -> ".join(str(loc) for loc in error["loc"])
                    error_msg = error["msg"]
                    errors.append(f"Field '{field_path}': {error_msg}")
            else:
                errors.append(f"Validation error: {str(e)}")

            return False, errors

    def validate_all_components(self) -> List[Dict[str, Any]]:
        """
        Validates all components in the index.

        Returns:
            A list of validation error dictionaries.
        """
        errors = []
        all_components = self.get_all_configs()
        for comp_type, components in all_components.items():
            for comp_id, _config in components.items():
                is_valid, component_errors = self.validate_component(comp_type, comp_id)
                if not is_valid:
                    errors.append(
                        {
                            "component_type": comp_type,
                            "component_id": comp_id,
                            "errors": component_errors,
                        }
                    )

        # Check for duplicate names across all component types
        names = {}
        for comp_type, components in all_components.items():
            for comp_id in components:
                if comp_id not in names:
                    names[comp_id] = []
                names[comp_id].append(comp_type)

        for name, types in names.items():
            if len(types) > 1:
                errors.append(
                    {
                        "component_type": "multiple",
                        "component_id": name,
                        "errors": [f"Duplicate component name '{name}' found in types: {', '.join(types)}"],
                    }
                )
        return errors

    # Project and Workspace Management Methods

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects in the current workspace.

        Returns:
            List of project information dictionaries
        """
        if not self.workspace_root:
            return []

        projects = []
        workspace_anchor = self.workspace_root / ".aurite"

        try:
            with open(workspace_anchor, "rb") as f:
                settings = tomllib.load(f).get("aurite", {})

            for project_name in settings.get("projects", []):
                project_path = self.workspace_root / project_name
                if project_path.is_dir() and (project_path / ".aurite").is_file():
                    project_info = self.get_project_info(project_name)
                    if project_info:
                        projects.append(project_info)

        except (tomllib.TOMLDecodeError, IOError) as e:
            logger.error(f"Could not parse workspace .aurite: {e}")

        return projects

    def get_project_info(self, project_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific project.

        Args:
            project_name: Name of the project

        Returns:
            Project information dictionary or None if not found
        """
        if not self.workspace_root:
            return None

        project_path = self.workspace_root / project_name
        project_anchor = project_path / ".aurite"

        if not project_anchor.is_file():
            return None

        try:
            with open(project_anchor, "rb") as f:
                settings = tomllib.load(f).get("aurite", {})

            return {
                "name": project_name,
                "path": str(project_path),
                "is_active": self.project_name == project_name,
                "include_configs": settings.get("include_configs", []),
                "description": settings.get("description"),
                "created_at": project_anchor.stat().st_ctime,
            }
        except (tomllib.TOMLDecodeError, IOError) as e:
            logger.error(f"Could not parse project {project_name} .aurite: {e}")
            return None

    def create_project(self, name: str, description: Optional[str] = None) -> bool:
        """
        Create a new project from the template.

        Args:
            name: Name of the new project
            description: Optional project description

            project_path.mkdir(parents=True, exist_ok=True)

        """
        import re
        import shutil

        # Validate project name
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            logger.error(f"Invalid project name '{name}'. Use only letters, numbers, hyphens, and underscores.")
            return False

        if not self.workspace_root:
            logger.error("Cannot create project: not in a workspace context")
            return False

        project_path = self.workspace_root / name

        # Check if project already exists
        if project_path.exists():
            logger.error(f"Project '{name}' already exists")
            return False

        try:
            # Copy template directory
            template_path = Path(__file__).parent.parent / "init_templates"
            if not template_path.exists():
                logger.error(f"Template directory not found at {template_path}")
                return False

            shutil.copytree(template_path, project_path)

            # Update project .aurite file if description provided
            if description:
                project_anchor = project_path / ".aurite"
                with open(project_anchor, "rb") as f:
                    settings = tomllib.load(f)

                settings["aurite"]["description"] = description

                # Write back as TOML
                with open(project_anchor, "w") as f:
                    toml.dump(settings, f)

            # Update workspace .aurite to include new project
            workspace_anchor = self.workspace_root / ".aurite"
            with open(workspace_anchor, "rb") as f:
                workspace_settings = tomllib.load(f)

            projects = workspace_settings.get("aurite", {}).get("projects", [])
            if name not in projects:
                projects.append(name)
                workspace_settings["aurite"]["projects"] = sorted(projects)

                with open(workspace_anchor, "w") as f:
                    toml.dump(workspace_settings, f)

            logger.info(f"Successfully created project '{name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create project '{name}': {e}")
            # Try to clean up on failure
            if project_path.exists():
                try:
                    shutil.rmtree(project_path)
                except Exception:
                    pass
            return False

    def delete_project(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a project.

        Args:
            name: Name of the project to delete

        Returns:
            Tuple of (success, error_message)
        """
        import shutil

        if not self.workspace_root:
            msg = "Cannot delete project: not in a workspace context"
            logger.error(msg)
            return False, msg

        # Cannot delete the currently active project
        if self.project_name == name:
            msg = f"Cannot delete currently active project '{name}'"
            logger.error(msg)
            return False, msg

        project_path = self.workspace_root / name

        if not project_path.exists():
            msg = f"Project '{name}' does not exist"
            logger.error(msg)
            return False, msg

        try:
            # Remove project directory
            shutil.rmtree(project_path)

            # Update workspace .aurite to remove project
            workspace_anchor = self.workspace_root / ".aurite"
            with open(workspace_anchor, "rb") as f:
                workspace_settings = tomllib.load(f)

            projects = workspace_settings.get("aurite", {}).get("projects", [])
            if name in projects:
                projects.remove(name)
                workspace_settings["aurite"]["projects"] = projects

                with open(workspace_anchor, "w") as f:
                    toml.dump(workspace_settings, f)

            logger.info(f"Successfully deleted project '{name}'")
            return True, None

        except Exception as e:
            msg = f"Failed to delete project '{name}': {e}"
            logger.error(msg)
            return False, msg

    def update_project(self, name: str, updates: Dict[str, Any]) -> bool:
        """
        Update project configuration.

        Args:
            name: Name of the project to update
            updates: Dictionary of updates (description, include_configs, new_name)

        Returns:
            True if successful, False otherwise
        """
        import shutil

        if not self.workspace_root:
            logger.error("Cannot update project: not in a workspace context")
            return False

        project_path = self.workspace_root / name
        project_anchor = project_path / ".aurite"

        if not project_anchor.is_file():
            logger.error(f"Project '{name}' does not exist")
            return False

        try:
            # Read current settings
            with open(project_anchor, "rb") as f:
                settings = tomllib.load(f)

            # Apply updates
            if "description" in updates:
                settings["aurite"]["description"] = updates["description"]

            if "include_configs" in updates:
                settings["aurite"]["include_configs"] = updates["include_configs"]

            # Handle rename
            new_name = updates.get("new_name")
            if new_name and new_name != name:
                import re

                # Validate new name
                if not re.match(r"^[a-zA-Z0-9_-]+$", new_name):
                    logger.error(f"Invalid project name '{new_name}'")
                    return False

                new_path = self.workspace_root / new_name
                if new_path.exists():
                    logger.error(f"Project '{new_name}' already exists")
                    return False

                # Move project directory
                shutil.move(str(project_path), str(new_path))

                # Update workspace .aurite
                workspace_anchor = self.workspace_root / ".aurite"
                with open(workspace_anchor, "rb") as f:
                    workspace_settings = tomllib.load(f)

                projects = workspace_settings.get("aurite", {}).get("projects", [])
                if name in projects:
                    projects[projects.index(name)] = new_name
                    workspace_settings["aurite"]["projects"] = sorted(projects)

                with open(workspace_anchor, "w") as f:
                    toml.dump(workspace_settings, f)

                # Update anchor path for writing
                project_anchor = new_path / ".aurite"

            # Write updated settings
            with open(project_anchor, "w") as f:
                toml.dump(settings, f)

            logger.info(f"Successfully updated project '{name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to update project '{name}': {e}")
            return False

    def get_workspace_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current workspace.

        Returns:
            Workspace information dictionary or None if not in a workspace
        """
        if not self.workspace_root:
            return None

        workspace_anchor = self.workspace_root / ".aurite"

        try:
            with open(workspace_anchor, "rb") as f:
                settings = tomllib.load(f).get("aurite", {})

            return {
                "name": self.workspace_name,
                "path": str(self.workspace_root),
                "projects": settings.get("projects", []),
                "include_configs": settings.get("include_configs", []),
                "is_active": True,  # Always true if we found it
                "description": settings.get("description"),
            }
        except (tomllib.TOMLDecodeError, IOError) as e:
            logger.error(f"Could not parse workspace .aurite: {e}")
            return None

    def get_active_project(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently active project.

        Returns:
            Project information dictionary or None if not in a project
        """
        if self.project_name:
            return self.get_project_info(self.project_name)
        return None

    def validate_llm(self, llm_name: str):
        """
        Validate an llm config. This should be called after an llm is successfully called or tested.

        Args:
            llm_name (str): The name of the llm config to validate
        """

        self.llm_validations[llm_name] = datetime.now()

    def get_llm_validation(self, llm_name) -> datetime | None:
        """
        Get the last time an llm was validated

        Args:
            llm_name (str): The name of the llm config

        Returns:
            datetime | None: Returns the last time an llm has been validated as running successfully. Returns None if it has not been validated.
        """
        return self.llm_validations.get(llm_name, None)
