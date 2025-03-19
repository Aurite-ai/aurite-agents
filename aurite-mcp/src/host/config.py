"""
Configuration classes and utilities for MCP Host and clients.

This module provides:
1. Configuration models for Host, Client, and Root settings
2. JSON configuration loading and validation
3. Helper functions for working with config files
4. Base class for configuration-aware managers
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any, TypeVar, Type, Generic
from pathlib import Path
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Base configuration directory
CONFIG_DIR = Path(__file__).parents[2] / "config"

# Type variable for configuration types
T = TypeVar("T")


@dataclass
class BaseConfig:
    """Base class for all configurations"""

    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseConfig":
        return cls(metadata=data.get("metadata", {}))


@dataclass
class RootConfig:
    """Configuration for an MCP root"""

    uri: str
    name: str
    capabilities: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RootConfig":
        return cls(
            uri=data["uri"], name=data["name"], capabilities=data["capabilities"]
        )


@dataclass
class ClientConfig:
    """Configuration for an MCP client"""

    client_id: str
    server_path: Path
    roots: List[RootConfig]
    capabilities: List[str]
    timeout: float = 10.0
    routing_weight: float = 1.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientConfig":
        return cls(
            client_id=data["client_id"],
            server_path=Path(data["server_path"]),
            roots=[RootConfig.from_dict(r) for r in data.get("roots", [])],
            capabilities=data["capabilities"],
            timeout=data.get("timeout", 10.0),
            routing_weight=data.get("routing_weight", 1.0),
        )


@dataclass
class ConnectionConfig(BaseConfig):
    """Configuration for database connections"""

    connections: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectionConfig":
        return cls(
            connections=data.get("connections", {}), metadata=data.get("metadata", {})
        )


@dataclass
class AgentConfig(BaseConfig):
    """Configuration for agents"""

    agents: List[ClientConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        return cls(
            agents=[ClientConfig.from_dict(a) for a in data.get("agents", [])],
            metadata=data.get("metadata", {}),
        )


@dataclass
class WorkflowConfig(BaseConfig):
    """Configuration for workflows"""

    workflows: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowConfig":
        return cls(
            workflows=data.get("workflows", []), metadata=data.get("metadata", {})
        )


@dataclass
class HostConfigModel:
    """Complete host configuration model"""

    clients: List[ClientConfig] = field(default_factory=list)
    config_paths: Dict[str, Path] = field(default_factory=dict)
    encryption_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HostConfigModel":
        return cls(
            clients=[ClientConfig.from_dict(c) for c in data.get("clients", [])],
            config_paths={k: Path(v) for k, v in data.get("config_paths", {}).items()},
            encryption_key=data.get("encryption_key"),
            metadata=data.get("metadata", {}),
        )


class ConfigurableManager(Generic[T], ABC):
    """
    Base class for managers that use JSON configuration.

    Type parameter T is the configuration model type (e.g., AgentConfig).
    """

    def __init__(self, config_type: str):
        """
        Initialize the configurable manager.

        Args:
            config_type: Type of configuration this manager handles
        """
        self._config_type = config_type
        self._config: Optional[T] = None
        self._metadata: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize the manager and load configuration"""
        logger.info(f"Initializing {self._config_type} manager")

        # Create default config if needed
        ConfigurationManager.create_default_config(self._config_type)

        # Load configuration
        await self._load_config()

    async def _load_config(self):
        """Load configuration from JSON"""
        try:
            # Load configuration
            config_data = ConfigurationManager.load_json_config(
                ConfigurationManager.get_config_path(self._config_type)
            )

            # Validate structure
            if not self._validate_config_structure(config_data):
                logger.error(f"Invalid {self._config_type} configuration structure")
                return

            # Convert to configuration model
            self._config = self._config_model_class().from_dict(config_data)

            # Store metadata
            self._metadata = config_data.get("metadata", {})

            logger.info(f"Loaded {self._config_type} configuration")

        except Exception as e:
            logger.error(f"Failed to load {self._config_type} configuration: {e}")

    @abstractmethod
    def _config_model_class(self) -> Type[T]:
        """Get the configuration model class for this manager"""
        pass

    @abstractmethod
    def _validate_config_structure(self, config: Dict[str, Any]) -> bool:
        """
        Validate the configuration structure.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    async def save_config(self, config: T, merge: bool = True) -> bool:
        """
        Save configuration to JSON.

        Args:
            config: Configuration to save
            merge: Whether to merge with existing config

        Returns:
            True if successful
        """
        try:
            # Convert to dictionary
            config_dict = asdict(config)

            # Update configuration
            ConfigurationManager.update_config(
                self._config_type, config_dict, merge=merge
            )

            # Update in-memory state
            self._config = config

            return True
        except Exception as e:
            logger.error(f"Failed to save {self._config_type} configuration: {e}")
            return False

    @property
    def config(self) -> Optional[T]:
        """Get the current configuration"""
        return self._config

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get configuration metadata"""
        return self._metadata


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
            "agents": CONFIG_DIR / "agents" / "aurite_agents.json",
            "host": CONFIG_DIR / "host.json",
            "prompts": CONFIG_DIR / "prompts",
            "resources": CONFIG_DIR / "resources",
        }

        return config_paths.get(config_type, CONFIG_DIR / f"{config_type}.json")

    @staticmethod
    def load_host_config(config_name: Optional[str] = None) -> HostConfigModel:
        """
        Load host configuration from JSON.

        Args:
            config_name: Optional name of the host config file (without .json)

        Returns:
            HostConfigModel instance
        """
        # Determine config path
        if config_name:
            config_path = CONFIG_DIR / f"{config_name}.json"
        else:
            config_path = ConfigurationManager.get_config_path("host")

        # Create default if it doesn't exist
        if not config_path.exists():
            ConfigurationManager.create_default_config("host")

        # Load and validate config
        config_data = ConfigurationManager.load_json_config(config_path)

        # Validate basic structure
        if not ConfigurationManager.validate_config_structure(
            config_data, ["clients", "config_paths"], "host"
        ):
            logger.warning("Using default host configuration")
            config_data = ConfigurationManager.get_default_host_config()

        # Convert to model
        return HostConfigModel.from_dict(config_data)

    @staticmethod
    def get_default_host_config() -> Dict[str, Any]:
        """Get the default host configuration"""
        return {
            "clients": [],
            "config_paths": {
                "workflows": str(CONFIG_DIR / "workflows" / "aurite_workflows.json"),
                "storage": str(CONFIG_DIR / "storage" / "connections.json"),
                "agents": str(CONFIG_DIR / "agents" / "aurite_agents.json"),
                "prompts": str(CONFIG_DIR / "prompts"),
                "resources": str(CONFIG_DIR / "resources"),
            },
            "metadata": {
                "version": "1.0",
                "description": "Default MCP Host configuration",
            },
        }

    @staticmethod
    def load_agent_configs() -> List[ClientConfig]:
        """
        Load agent configurations from the agents config file.

        Returns:
            List of ClientConfig objects
        """
        config = ConfigurationManager.load_json_config(
            ConfigurationManager.get_config_path("agents")
        )

        if not config or "agents" not in config:
            logger.warning("No agent configurations found")
            return []

        return [ClientConfig.from_dict(agent) for agent in config["agents"]]

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
            True if all validators pass, False otherwise
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
            "host": ConfigurationManager.get_default_host_config(),
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
            "agents": {
                "agents": [],
                "metadata": {
                    "version": "1.0",
                    "description": "Configuration for Aurite agent registration",
                },
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
