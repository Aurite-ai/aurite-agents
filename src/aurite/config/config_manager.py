import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .config_utils import find_anchor_files

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

    def _initialize_sources(self):
        """Initializes the configuration source paths based on the hierarchical context."""
        logger.debug("Initializing configuration sources...")
        config_sources: List[tuple[Path, Path]] = []
        processed_paths = set()

        # Process contexts from most specific (project) to most general (workspace)
        for anchor_path in self.context_paths:
            context_root = anchor_path.parent
            try:
                with open(anchor_path, "rb") as f:
                    settings = tomllib.load(f).get("aurite", {})

                # Add config paths defined in the current .aurite file
                for rel_path in settings.get("include_configs", []):
                    resolved_path = (context_root / rel_path).resolve()
                    if resolved_path.is_dir() and resolved_path not in processed_paths:
                        config_sources.append((resolved_path, context_root))
                        processed_paths.add(resolved_path)

                # If it's a workspace, find all its projects and their configs
                if settings.get("type") == "workspace":
                    for project_rel_path in settings.get("projects", []):
                        project_root = (context_root / project_rel_path).resolve()
                        project_anchor = project_root / ".aurite"
                        if project_anchor.is_file():
                            with open(project_anchor, "rb") as pf:
                                p_settings = tomllib.load(pf).get("aurite", {})
                            for p_rel_path in p_settings.get("include_configs", []):
                                resolved_p_path = (project_root / p_rel_path).resolve()
                                if resolved_p_path.is_dir() and resolved_p_path not in processed_paths:
                                    config_sources.append((resolved_p_path, project_root))
                                    processed_paths.add(resolved_p_path)
            except (tomllib.TOMLDecodeError, IOError) as e:
                logger.error(f"Could not parse {anchor_path} during source init: {e}")

        # Global user config is always last
        user_config_root = Path.home() / ".aurite"
        if user_config_root.is_dir():
            config_sources.append((user_config_root, user_config_root))

        self._config_sources = config_sources
        logger.debug(f"Final configuration source order: {self._config_sources}")

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

    def upsert_component(self, component_type: str, component_name: str, new_config: Dict[str, Any]) -> bool:
        # This method would need to be updated to work with the new flat-list structure
        # For now, we focus on getting the loading right.
        logger.error("upsert_component is not implemented for the new config structure yet.")
        return False
