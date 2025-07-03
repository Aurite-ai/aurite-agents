import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from importlib.abc import Traversable
import yaml
import json


logger = logging.getLogger(__name__)

# Mapping component type to its expected ID field name
COMPONENT_ID_FIELDS = {
    "mcp_servers": "name",
    "llms": "name",
    "agents": "name",
    "simple_workflows": "name",
    "custom_workflows": "name",
}


class ConfigManager:
    """
    Manages the discovery, loading, and validation of configurations
    from various sources and formats.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initializes the ConfigManager.

        Args:
            project_root: The root directory of the current project.
        """
        self._config_sources: List[Union[Path, Traversable]] = []
        self._component_index: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._force_refresh = (
            os.getenv("AURITE_CONFIG_FORCE_REFRESH", "true").lower() == "true"
        )

        self._initialize_sources(project_root)
        self._build_component_index()

    def _initialize_sources(self, project_root: Optional[Path]):
        """Initializes the configuration source paths in order of precedence."""
        logger.debug("Initializing configuration sources...")

        # 1. Project Configuration
        if project_root:
            project_config_path = project_root / "config"
            if project_config_path.is_dir():
                self._config_sources.append(project_config_path)
                logger.debug(f"Added project config source: {project_config_path}")

        # 2. Global User Configuration
        user_config_path = Path.home() / ".aurite" / "config"
        if user_config_path.is_dir():
            self._config_sources.append(user_config_path)
            logger.debug(f"Added user config source: {user_config_path}")

        # TODO: Add Repository source detection

        # 3. Packaged Defaults
        try:
            import importlib.resources

            packaged_root_trav = importlib.resources.files("aurite.packaged")
            packaged_configs_dir = packaged_root_trav.joinpath("component_configs")
            if packaged_configs_dir.is_dir():
                self._config_sources.append(packaged_configs_dir)
                logger.debug(f"Added packaged defaults source: {packaged_configs_dir}")
        except (ModuleNotFoundError, FileNotFoundError):
            logger.warning("Could not find packaged default configurations.")

    def _build_component_index(self):
        """Builds an index of all available components from the config sources."""
        logger.debug(
            f"Building component index from {len(self._config_sources)} sources."
        )

        for source_path in reversed(
            self._config_sources
        ):  # Reverse to process highest priority last
            if not source_path.is_dir():
                continue

            for config_file in source_path.iterdir():
                self._parse_and_index_file(config_file)

    def _parse_and_index_file(self, config_file: Union[Path, Traversable]):
        """Parses a file and adds its component(s) to the index."""
        is_file = getattr(config_file, "is_file", lambda: False)()
        if not is_file:
            return

        file_name = getattr(config_file, "name", "")
        file_suffix = Path(file_name).suffix
        if file_suffix not in [".json", ".yaml", ".yml"]:
            return

        try:
            with config_file.open("r", encoding="utf-8") as f:
                if file_suffix == ".json":
                    content = json.load(f)
                else:
                    content = yaml.safe_load(f)
        except (IOError, json.JSONDecodeError, yaml.YAMLError) as e:
            logger.error(f"Failed to load or parse config file {config_file}: {e}")
            return

        if not isinstance(content, dict):
            return  # Monolithic files must be a dictionary

        for component_type, component_list in content.items():
            if component_type not in COMPONENT_ID_FIELDS:
                continue

            id_field = COMPONENT_ID_FIELDS[component_type]
            if component_type not in self._component_index:
                self._component_index[component_type] = {}

            if isinstance(component_list, list):
                for component_data in component_list:
                    if isinstance(component_data, dict):
                        component_id = component_data.get(id_field)
                        if component_id:
                            self._component_index[component_type][component_id] = (
                                component_data
                            )
                            logger.debug(
                                f"Indexed '{component_id}' ({component_type}) from {config_file}"
                            )
                        else:
                            logger.warning(
                                f"Component in {config_file} is missing ID field '{id_field}'."
                            )

    def get_config(
        self, component_type: str, component_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Gets the configuration for a specific component.

        Args:
            component_type: The type of the component (e.g., 'agents').
            component_id: The ID of the component.

        Returns:
            A dictionary containing the component's configuration, or None if not found.
        """
        if self._force_refresh:
            self.refresh()
        return self._component_index.get(component_type, {}).get(component_id)

    def list_configs(self, component_type: str) -> List[Dict[str, Any]]:
        """
        Lists all configurations for a specific component type.

        Args:
            component_type: The type of the component (e.g., 'agents').

        Returns:
            A list of dictionaries, where each dictionary is a component's configuration.
        """
        if self._force_refresh:
            self.refresh()
        return list(self._component_index.get(component_type, {}).values())

    def get_all_configs(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Returns the entire component index.

        Returns:
            A dictionary containing all component configurations, grouped by type.
        """
        if self._force_refresh:
            self.refresh()
        return self._component_index

    def refresh(self):
        """Clears the component index and rebuilds it from the sources."""
        logger.debug("Refreshing configuration index...")
        self._component_index = {}
        self._build_component_index()
