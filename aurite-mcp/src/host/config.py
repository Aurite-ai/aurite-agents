"""
Configuration classes and utilities for MCP Host and clients.

This module provides:
1. Configuration models for Host, Client, and Root settings
2. JSON configuration loading and validation
3. Helper functions for working with config files
"""

import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, TypeVar, Type
from pathlib import Path

logger = logging.getLogger(__name__)

# Base configuration directory
CONFIG_DIR = Path(__file__).parents[2] / "config"


@dataclass
class RootConfig:
    """Configuration for an MCP root"""

    uri: str
    name: str
    capabilities: List[str]


@dataclass
class ClientConfig:
    """Configuration for an MCP client"""

    client_id: str
    server_path: Path
    roots: List[RootConfig]
    capabilities: List[str]
    timeout: float = 10.0  # Default timeout in seconds
    routing_weight: float = 1.0  # Weight for server selection


@dataclass
class HostConfig:
    """Configuration for the MCP host"""

    clients: List[ClientConfig]


# Type variable for generic config loading
T = TypeVar("T")


class ConfigurationManager:
    """
    Manages configuration loading and validation for the MCP host system.
    Provides utilities for working with JSON configuration files.
    """

    @staticmethod
    def load_json_config(config_path: Path) -> Dict[str, Any]:
        """
        Load a JSON configuration file.

        Args:
            config_path: Path to the JSON config file

        Returns:
            Parsed JSON configuration
        """
        try:
            with open(config_path) as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file {config_path}: {e}")
            raise

    @staticmethod
    def get_config_path(config_type: str) -> Path:
        """
        Get the path to a configuration file.

        Args:
            config_type: Type of configuration (e.g., 'workflows', 'storage')

        Returns:
            Path to the configuration directory/file
        """
        config_paths = {
            "workflows": CONFIG_DIR / "workflows" / "aurite_workflows.json",
            "storage": CONFIG_DIR / "storage" / "connections.json",
            "prompts": CONFIG_DIR / "prompts",
            "resources": CONFIG_DIR / "resources",
        }

        return config_paths.get(config_type, CONFIG_DIR / f"{config_type}.json")

    @staticmethod
    def load_workflow_config(workflow_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load workflow configuration(s).

        Args:
            workflow_name: Optional specific workflow to load

        Returns:
            Workflow configuration dictionary
        """
        config_path = ConfigurationManager.get_config_path("workflows")
        config = ConfigurationManager.load_json_config(config_path)

        if workflow_name:
            # Find specific workflow configuration
            workflow_config = next(
                (
                    w["config"]
                    for w in config.get("workflows", [])
                    if w["name"] == workflow_name
                ),
                None,
            )
            return workflow_config if workflow_config else {}

        return config

    @staticmethod
    def load_storage_config() -> Dict[str, Any]:
        """
        Load storage/database connection configurations.

        Returns:
            Storage configuration dictionary
        """
        config_path = ConfigurationManager.get_config_path("storage")
        return ConfigurationManager.load_json_config(config_path)

    @staticmethod
    def validate_config_structure(
        config: Dict[str, Any], required_fields: List[str], config_name: str
    ) -> bool:
        """
        Validate that a configuration has required fields.

        Args:
            config: Configuration dictionary to validate
            required_fields: List of required field names
            config_name: Name of the configuration for error messages

        Returns:
            True if valid, False otherwise
        """
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            logger.error(
                f"Missing required fields in {config_name} configuration: {missing_fields}"
            )
            return False
        return True

    @staticmethod
    def create_default_config(config_type: str) -> None:
        """
        Create a default configuration file if it doesn't exist.

        Args:
            config_type: Type of configuration to create
        """
        config_path = ConfigurationManager.get_config_path(config_type)

        if config_path.exists():
            return

        default_configs = {
            "workflows": {
                "workflows": [],
                "metadata": {
                    "version": "1.0",
                    "description": "Configuration for Aurite workflow registration",
                },
            },
            "storage": {
                "connections": {
                    "default_sqlite": {
                        "type": "sqlite",
                        "database": "default.db",
                        "credentialsEnv": None,
                    }
                }
            },
        }

        if config_type in default_configs:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(default_configs[config_type], f, indent=2)
            logger.info(f"Created default {config_type} configuration at {config_path}")

    @staticmethod
    def update_config(
        config_type: str, updates: Dict[str, Any], merge: bool = True
    ) -> None:
        """
        Update a configuration file.

        Args:
            config_type: Type of configuration to update
            updates: Dictionary of updates to apply
            merge: Whether to merge with existing config (True) or replace (False)
        """
        config_path = ConfigurationManager.get_config_path(config_type)

        # Load existing config if merging
        if merge and config_path.exists():
            current_config = ConfigurationManager.load_json_config(config_path)

            # Deep merge the updates
            def deep_merge(base: dict, updates: dict) -> dict:
                for key, value in updates.items():
                    if (
                        key in base
                        and isinstance(base[key], dict)
                        and isinstance(value, dict)
                    ):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value
                return base

            final_config = deep_merge(current_config, updates)
        else:
            final_config = updates

        # Save the updated config
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(final_config, f, indent=2)
        logger.info(f"Updated {config_type} configuration at {config_path}")
