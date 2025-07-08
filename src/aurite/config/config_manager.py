import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .config_utils import find_anchor_files
from .file_manager import FileManager

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


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

            if component_id not in self._component_index[component_type]:
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

                self._component_index[component_type][component_id] = component_data
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
        self.__init__()

    def list_config_sources(self) -> List[Dict[str, Any]]:
        """
        List all configuration source directories with context information.

        Returns:
            List of dictionaries containing source directory information
        """
        if self._force_refresh:
            self.refresh()
        return self._file_manager.list_config_sources()

    def list_config_files(self, source_name: str) -> List[str]:
        """
        List all configuration files for a specific source.

        Args:
            source_name: The name of the source to list files for.

        Returns:
            A list of relative file paths.
        """
        if self._force_refresh:
            self.refresh()
        return self._file_manager.list_config_files(source_name)

    def get_file_content(self, source_name: str, relative_path: str) -> Optional[str]:
        """
        Get the content of a specific configuration file.

        Args:
            source_name: The name of the source the file belongs to.
            relative_path: The relative path of the file within the source.

        Returns:
            The file content as a string, or None if not found or invalid.
        """
        if self._force_refresh:
            self.refresh()
        return self._file_manager.get_file_content(source_name, relative_path)

    def create_config_file(self, source_name: str, relative_path: str, content: str) -> bool:
        """
        Create a new configuration file.

        Args:
            source_name: The name of the source to create the file in.
            relative_path: The relative path for the new file.
            content: The content to write to the file.

        Returns:
            True if the file was created successfully, False otherwise.
        """
        if self._force_refresh:
            self.refresh()
        return self._file_manager.create_config_file(source_name, relative_path, content)

    def update_config_file(self, source_name: str, relative_path: str, content: str) -> bool:
        """
        Update an existing configuration file.

        Args:
            source_name: The name of the source where the file exists.
            relative_path: The relative path of the file to update.
            content: The new content to write to the file.

        Returns:
            True if the file was updated successfully, False otherwise.
        """
        if self._force_refresh:
            self.refresh()
        return self._file_manager.update_config_file(source_name, relative_path, content)

    def delete_config_file(self, source_name: str, relative_path: str) -> bool:
        """
        Delete an existing configuration file.

        Args:
            source_name: The name of the source where the file exists.
            relative_path: The relative path of the file to delete.

        Returns:
            True if the file was deleted successfully, False otherwise.
        """
        if self._force_refresh:
            self.refresh()
        return self._file_manager.delete_config_file(source_name, relative_path)

    def update_component(self, component_type: str, component_name: str, new_config: Dict[str, Any]) -> bool:
        """
        Updates a component configuration by writing back to its source file.
        """
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
                file_data[i] = new_config
                component_found = True
                break

        if not component_found:
            return False

        if file_format == "json":
            updated_content = json.dumps(file_data, indent=2)
        else:
            updated_content = yaml.safe_dump(file_data)

        return self.update_config_file(source_name, str(relative_path), updated_content)

    def create_component(
        self,
        component_type: str,
        component_config: Dict[str, Any],
        project: Optional[str] = None,
        workspace: bool = False,
        file_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        # Step 1: Determine context
        context_name = None
        if workspace:
            context_name = self.workspace_name
        elif project:
            context_name = project
        else:
            # Auto-detect context
            if self.project_name:
                context_name = self.project_name
            elif self.workspace_name:
                # Check for multiple projects
                sources = self._file_manager.list_config_sources()
                project_sources = [s for s in sources if s["context"] == "project"]
                if len(project_sources) > 1:
                    logger.error("Multiple projects found. Specify 'project' or 'workspace'.")
                    return None
                context_name = self.workspace_name

        if not context_name:
            logger.error("Could not determine a valid context for component creation.")
            return None

        # Step 2: Determine target file
        target_file = self._file_manager.find_or_create_component_file(component_type, context_name, file_path)
        if not target_file:
            return None

        # Step 3: Add component to file
        success = self._file_manager.add_component_to_file(target_file, component_config)
        if not success:
            return None

        # Refresh index to include the new component
        self.refresh()

        # Return success response
        source_info = self._file_manager.list_config_sources()
        context_info = next(
            (
                s
                for s in source_info
                if s.get("project_name") == context_name
                or (s.get("workspace_name") == context_name and s["context"] == "workspace")
            ),
            {},
        )

        return {
            "message": "Component created successfully",
            "component": {
                "name": component_config["name"],
                "type": component_type,
                "file_path": str(target_file.relative_to(Path(context_info["path"]))),
                "context": context_info.get("context"),
                "project_name": context_info.get("project_name"),
                "workspace_name": context_info.get("workspace_name"),
            },
        }

    def delete_config(self, component_type: str, component_name: str) -> bool:
        """
        Deletes a component configuration by removing it from its source file.
        If the component is the last one in the file, the file will be deleted.
        """
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
