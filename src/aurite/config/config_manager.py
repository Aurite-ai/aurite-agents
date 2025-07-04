import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
import json

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

    def __init__(self):
        """
        Initializes the ConfigManager, automatically discovering the context.
        """
        self.context_paths: List[Path] = find_anchor_files(Path.cwd())
        self.project_root: Optional[Path] = None
        self.workspace_root: Optional[Path] = None

        if self.context_paths:
            self.project_root = self.context_paths[0].parent
            if len(self.context_paths) > 1:
                self.workspace_root = self.context_paths[1].parent

        self._config_sources: List[Path] = []
        self._merged_settings: Dict[str, Any] = {}
        self._component_index: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._force_refresh = (
            os.getenv("AURITE_CONFIG_FORCE_REFRESH", "true").lower() == "true"
        )

        self._load_and_merge_settings()
        self._initialize_sources()
        self._build_component_index()

    def _load_and_merge_settings(self):
        """Loads and merges settings from all found .aurite files."""
        for anchor_path in reversed(self.context_paths):
            try:
                with open(anchor_path, "rb") as f:
                    toml_data = tomllib.load(f)
                    aurite_settings = toml_data.get("aurite", {})

                    # Merge [env] table
                    env_settings = toml_data.get("env", {})
                    self._merged_settings.setdefault("env", {}).update(env_settings)

                    # Prepend path lists
                    for key in [
                        "include_configs",
                        "custom_workflow_paths",
                        "mcp_server_paths",
                    ]:
                        new_paths = aurite_settings.get(key, [])
                        existing_paths = self._merged_settings.setdefault(key, [])
                        self._merged_settings[key] = new_paths + existing_paths

                    # Store other aurite settings, like 'type' and 'projects'
                    for key, value in aurite_settings.items():
                        if key not in [
                            "include_configs",
                            "custom_workflow_paths",
                            "mcp_server_paths",
                            "env",
                        ]:
                            self._merged_settings[key] = value

            except (tomllib.TOMLDecodeError, IOError) as e:
                logger.error(f"Failed to load or parse {anchor_path}: {e}")

        for key, value in self._merged_settings.get("env", {}).items():
            os.environ[key] = str(value)

    def _initialize_sources(self):
        """Initializes the configuration source paths based on the hierarchical context."""
        logger.debug("Initializing configuration sources...")

        config_sources = []

        # Process up to the first two levels (project and workspace)
        for i, anchor_path in enumerate(self.context_paths[:2]):
            context_root = anchor_path.parent

            # 1. Add the default 'config' directory for the current level
            config_sources.append(context_root / "config")

            # 2. Add any 'include_configs' from the .aurite file at this level
            try:
                with open(anchor_path, "rb") as f:
                    toml_data = tomllib.load(f)
                    aurite_settings = toml_data.get("aurite", {})
                    for rel_path in aurite_settings.get("include_configs", []):
                        config_sources.append(context_root / rel_path)

                    # 3. For the workspace, add peer projects
                    if aurite_settings.get("type") == "workspace":
                        for rel_path in aurite_settings.get("projects", []):
                            peer_project_root = (context_root / rel_path).resolve()
                            if (peer_project_root / ".aurite").is_file():
                                config_sources.append(peer_project_root / "config")
            except (tomllib.TOMLDecodeError, IOError) as e:
                logger.error(
                    f"Could not parse {anchor_path} during source initialization: {e}"
                )

        # Global config is last
        user_config_path = Path.home() / ".aurite" / "config"
        if user_config_path.is_dir():
            config_sources.append(user_config_path)

        self._config_sources = config_sources
        logger.debug(f"Final configuration source order: {self._config_sources}")

    def _build_component_index(self):
        """Builds an index of all available components, respecting priority."""
        logger.debug("Building component index...")
        self._component_index = {}

        for source_path in self._config_sources:
            if not source_path.is_dir():
                continue

            for config_file in source_path.rglob("*.json"):
                self._parse_and_index_file(config_file)
            for config_file in source_path.rglob("*.yaml"):
                self._parse_and_index_file(config_file)
            for config_file in source_path.rglob("*.yml"):
                self._parse_and_index_file(config_file)

    def _parse_and_index_file(self, config_file: Path):
        """Parses a file and adds its component(s) to the index if not already present."""
        try:
            with config_file.open("r", encoding="utf-8") as f:
                if config_file.suffix == ".json":
                    content = json.load(f)
                else:
                    content = yaml.safe_load(f)
        except (IOError, json.JSONDecodeError, yaml.YAMLError) as e:
            logger.error(f"Failed to load or parse config file {config_file}: {e}")
            return

        if not isinstance(content, dict):
            return

        for component_type, component_list in content.items():
            if not isinstance(component_list, list):
                continue

            self._component_index.setdefault(component_type, {})

            for component_data in component_list:
                if isinstance(component_data, dict):
                    component_id = component_data.get("name")
                    if (
                        component_id
                        and component_id not in self._component_index[component_type]
                    ):
                        self._component_index[component_type][component_id] = (
                            component_data
                        )
                        logger.debug(
                            f"Indexed '{component_id}' ({component_type}) from {config_file}"
                        )

    def _resolve_paths_in_config(
        self, config_data: Dict[str, Any], component_type: str
    ) -> Dict[str, Any]:
        """Resolves relative paths in a component's configuration data."""
        if not self.project_root:
            return config_data

        resolved_data = config_data.copy()

        if component_type == "mcp_servers":
            if "server_path" in resolved_data and resolved_data["server_path"]:
                path = Path(resolved_data["server_path"])
                if not path.is_absolute():
                    resolved_data["server_path"] = (self.project_root / path).resolve()

        elif component_type == "custom_workflows":
            if "module_path" in resolved_data and resolved_data["module_path"]:
                path = Path(resolved_data["module_path"])
                if not path.is_absolute():
                    resolved_data["module_path"] = (self.project_root / path).resolve()

        return resolved_data

    def get_config(
        self, component_type: str, component_id: str
    ) -> Optional[Dict[str, Any]]:
        if self._force_refresh:
            self.refresh()

        config = self._component_index.get(component_type, {}).get(component_id)
        if config:
            return self._resolve_paths_in_config(config, component_type)
        return None

    def list_configs(self, component_type: str) -> List[Dict[str, Any]]:
        if self._force_refresh:
            self.refresh()
        return list(self._component_index.get(component_type, {}).values())

    def get_all_configs(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        if self._force_refresh:
            self.refresh()
        return self._component_index

    def refresh(self):
        logger.debug("Refreshing configuration index...")
        self.__init__()
