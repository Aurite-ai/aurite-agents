import json
import logging
from pathlib import Path
from typing import List
import yaml

from .config_utils import find_anchor_files

try:
    import tomllib
except ImportError:
    import tomli as tomllib

logger = logging.getLogger(__name__)


def list_component_names(component_type: str) -> List[str]:
    """
    Quickly finds and lists the names of all components of a specific type
    without fully loading or validating them. Designed for CLI completion.
    """
    names = set()
    context_paths = find_anchor_files(Path.cwd())
    config_sources: List[Path] = []

    # This logic is a simplified version of ConfigManager._initialize_sources
    for anchor_path in context_paths[:2]:
        context_root = anchor_path.parent
        try:
            with open(anchor_path, "rb") as f:
                toml_data = tomllib.load(f)
                aurite_settings = toml_data.get("aurite", {})

                # Default 'config' dir
                default_config_path = context_root / "config"
                if default_config_path.is_dir():
                    config_sources.append(default_config_path)

                # 'include_configs'
                for rel_path in aurite_settings.get("include_configs", []):
                    resolved_path = (context_root / rel_path).resolve()
                    if resolved_path.is_dir():
                        config_sources.append(resolved_path)

                # Peer projects for workspaces
                if aurite_settings.get("type") == "workspace":
                    for rel_path in aurite_settings.get("projects", []):
                        peer_project_root = (context_root / rel_path).resolve()
                        peer_anchor = peer_project_root / ".aurite"
                        if peer_anchor.is_file():
                            with open(peer_anchor, "rb") as peer_f:
                                peer_toml = tomllib.load(peer_f)
                                peer_settings = peer_toml.get("aurite", {})
                                # Default 'config' in peer
                                default_peer_path = peer_project_root / "config"
                                if default_peer_path.is_dir():
                                    config_sources.append(default_peer_path)
                                # 'include_configs' in peer
                                for peer_rel_path in peer_settings.get(
                                    "include_configs", []
                                ):
                                    resolved_peer_path = (
                                        peer_project_root / peer_rel_path
                                    ).resolve()
                                    if resolved_peer_path.is_dir():
                                        config_sources.append(resolved_peer_path)
        except (tomllib.TOMLDecodeError, IOError) as e:
            logger.debug(f"Fast loader could not parse {anchor_path}: {e}")

    # Global config
    user_config_path = Path.home() / ".aurite" / "config"
    if user_config_path.is_dir():
        config_sources.append(user_config_path)

    # Now, perform a shallow parse of files in the sources
    for source_path in config_sources:
        for config_file in source_path.rglob("*.json"):
            _shallow_parse_and_add_names(config_file, component_type, names)
        for config_file in source_path.rglob("*.yaml"):
            _shallow_parse_and_add_names(config_file, component_type, names)
        for config_file in source_path.rglob("*.yml"):
            _shallow_parse_and_add_names(config_file, component_type, names)

    return sorted(list(names))


def _shallow_parse_and_add_names(
    config_file: Path, target_component_type: str, names: set
):
    """
    Opens a config file and adds the 'name' of any components of the target type to the set.
    """
    try:
        with config_file.open("r", encoding="utf-8") as f:
            if config_file.suffix == ".json":
                content = json.load(f)
            else:
                content = yaml.safe_load(f)
    except (IOError, json.JSONDecodeError, yaml.YAMLError):
        return  # Ignore files that can't be parsed

    if not isinstance(content, dict):
        return

    component_list = content.get(target_component_type)
    if isinstance(component_list, list):
        for item in component_list:
            if isinstance(item, dict) and "name" in item:
                names.add(item["name"])
