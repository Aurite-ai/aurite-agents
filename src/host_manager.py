"""
Host Manager for orchestrating MCPHost, Agents, and Workflows.
"""

import logging
import os  # Added for environment variable check
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Set

# Assuming this file is in src/, use relative imports
from .host.host import MCPHost
from .config.config_models import (  # Updated import path
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    ClientConfig,
    LLMConfig,  # Added LLMConfig
)

# Imports needed for execution methods
from .config import PROJECT_ROOT_DIR

# Import the new facade
from .execution.facade import ExecutionFacade

# Import StorageManager and engine factory unconditionally
from .storage.db_manager import StorageManager
from .storage.db_connection import create_db_engine  # Import engine factory

# Setup logger for this module
logger = logging.getLogger(__name__)

# Removed conditional import block for StorageManager

# Import the new managers and ProjectConfig
from .config.component_manager import ComponentManager
from .config.project_manager import ProjectManager
from .config.config_models import ProjectConfig


class HostManager:
    """
    Manages the lifecycle of MCPHost and orchestrates the execution of
    agents, simple workflows, and custom workflows based on loaded configurations.
    """

    def __init__(self, config_path: Path):
        """
        Initializes the HostManager.

        Args:
            config_path: The path to the main JSON configuration file.
        """
        if not isinstance(config_path, Path):
            # Ensure config_path is a Path object for consistency
            config_path = Path(config_path)

        if not config_path.is_absolute():
            logger.warning(
                f"Configuration path provided is not absolute: {config_path}. "
                "Resolving relative to current working directory. "
                "Ensure this is the intended behavior."
            )
            # Resolve relative paths based on CWD, or consider requiring absolute paths
            # For now, let's resolve it, but this might need adjustment based on usage context.
            config_path = config_path.resolve()

        self.config_path: Path = config_path
        self.host: Optional["MCPHost"] = (
            None  # Forward reference for type hint if MCPHost is imported later
        )
        self.agent_configs: Dict[str, "AgentConfig"] = {}
        self.workflow_configs: Dict[str, "WorkflowConfig"] = {}
        self.custom_workflow_configs: Dict[str, "CustomWorkflowConfig"] = {}
        self.llm_configs: Dict[str, "LLMConfig"] = {}  # Added for LLM configs
        self.storage_manager: Optional["StorageManager"] = None  # Initialize as None
        self.execution: Optional[ExecutionFacade] = None
        self._db_engine = None  # Store engine if created
        # Instantiate ComponentManager first, as ProjectManager needs it
        self.component_manager = ComponentManager()
        self.project_manager = ProjectManager(
            self.component_manager
        )  # Pass component manager
        self.current_project: Optional[ProjectConfig] = None  # To store loaded project

        # Instantiate StorageManager if DB is enabled
        if os.getenv("AURITE_ENABLE_DB", "false").lower() == "true":
            logger.info(
                "Database persistence enabled. Attempting to initialize StorageManager."
            )
            # Create the engine here and pass it
            self._db_engine = create_db_engine()
            if self._db_engine:
                try:
                    # Pass the created engine to the StorageManager
                    self.storage_manager = StorageManager(engine=self._db_engine)
                except Exception as e:
                    logger.error(
                        f"Failed to instantiate StorageManager with engine: {e}",
                        exc_info=True,
                    )
                    self.storage_manager = (
                        None  # Ensure it's None if instantiation fails
                    )
            else:
                # Engine creation failed (logged in create_db_engine)
                self.storage_manager = None
        else:
            logger.info(
                "Database persistence is disabled (AURITE_ENABLE_DB is not 'true')."
            )

        logger.debug(
            f"HostManager initialized with config path: {self.config_path}"
        )  # INFO -> DEBUG

    # --- Lifecycle Methods ---

    async def initialize(self):
        """
        Loads configurations, initializes the MCPHost, and prepares the manager.

        Raises:
            RuntimeError: If configuration loading or host initialization fails.
        """
        logger.info(  # Changed back to INFO for high-level start
            f"Initializing HostManager with project config: {self.config_path}..."
        )
        try:
            # 1. Load Project Configuration using ProjectManager
            logger.debug(f"Loading project configuration from {self.config_path}...")
            self.current_project = self.project_manager.load_project(self.config_path)
            # load_project raises FileNotFoundError or RuntimeError on failure
            logger.info(f"Project '{self.current_project.name}' loaded successfully.")

            # Store component configs from the loaded project directly onto the manager
            self.agent_configs = self.current_project.agent_configs
            self.workflow_configs = self.current_project.simple_workflow_configs
            self.custom_workflow_configs = self.current_project.custom_workflow_configs
            self.llm_configs = self.current_project.llm_configs
            logger.debug(
                f"Stored {len(self.agent_configs)} agents, {len(self.llm_configs)} LLMs, "
                f"{len(self.workflow_configs)} simple workflows, "
                f"{len(self.custom_workflow_configs)} custom workflows from project."
            )

            # 1.5 Initialize DB Schema if storage manager exists
            if self.storage_manager:
                self.storage_manager.init_db()  # Synchronous call for schema creation

            # 2. Construct HostConfig for MCPHost from ProjectConfig
            # Import HostConfig model if not already imported at top
            from .config.config_models import HostConfig  # Keep this import here

            logger.debug("Constructing HostConfig for MCPHost...")
            host_config_for_mcphost = HostConfig(
                name=self.current_project.name,  # Use name from loaded project
                description=self.current_project.description,  # Use description from loaded project
                clients=list(
                    self.current_project.clients.values()
                ),  # MCPHost expects a list of ClientConfig objects
            )
            logger.debug("HostConfig constructed.")

            # Instantiate MCPHost
            logger.debug("Instantiating MCPHost...")
            self.host = MCPHost(
                config=host_config_for_mcphost,  # Use constructed HostConfig
                agent_configs=self.agent_configs,  # Still pass this for now, MCPHost might use it internally
                # Removed workflow_configs argument as MCPHost doesn't need it directly
                # encryption_key could be passed from a secure source if needed
            )
            logger.debug("MCPHost instance created.")

            # 3. Initialize MCPHost (connects to clients, etc.)
            logger.debug("Initializing MCPHost (connecting clients)...")
            await self.host.initialize()
            logger.info("MCPHost initialized successfully.")

            # 2.5 Sync initial configs to DB if storage manager exists
            if self.storage_manager:
                logger.debug("Syncing loaded configurations to database...")
                # Assuming sync_all_configs is synchronous for now
                # If it becomes async, add await here.
                self.storage_manager.sync_all_configs(
                    agents=self.agent_configs,
                    workflows=self.workflow_configs,
                    custom_workflows=self.custom_workflow_configs,
                    llm_configs=self.llm_configs,  # Pass LLM configs to sync
                )
                logger.debug("Database sync complete.")

            # Old Step 3 (Load additional configs) is removed as project loading handles all necessary configs now.
            # Old private registration helpers (_register_clients_from_config etc.) are no longer needed here.

            # 4. Instantiate ExecutionFacade, passing self (the manager) and storage_manager
            logger.debug("Instantiating ExecutionFacade...")
            self.execution = ExecutionFacade(
                host_manager=self,
                storage_manager=self.storage_manager,  # Pass storage manager
            )

            logger.info(
                "HostManager initialization complete."
            )  # Keep this high-level INFO

        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {self.config_path} - {e}")
            raise RuntimeError(
                f"Configuration file not found: {self.config_path}"
            ) from e
        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            # Catch errors from load_host_config_from_json or MCPHost instantiation
            logger.error(f"Error during HostManager initialization: {e}", exc_info=True)
            # Clean up partially initialized host if necessary
            if self.host:
                try:
                    await self.host.shutdown()
                except Exception as shutdown_err:
                    logger.error(
                        f"Error shutting down host after initialization failure: {shutdown_err}"
                    )
            self.host = None  # Ensure host is None if init failed
            raise RuntimeError(f"HostManager initialization failed: {e}") from e
        except Exception as e:
            # Catch unexpected errors during host.initialize() or other steps
            logger.error(
                f"Unexpected error during HostManager initialization: {e}",
                exc_info=True,
            )
            if self.host:
                try:
                    await self.host.shutdown()
                except Exception as shutdown_err:
                    logger.error(
                        f"Error shutting down host after initialization failure: {shutdown_err}"
                    )
            self.host = None
            raise RuntimeError(
                f"Unexpected error during HostManager initialization: {e}"
            ) from e

    async def shutdown(self):
        """
        Shuts down the managed MCPHost and cleans up resources.
        """
        logger.info("Shutting down HostManager...")
        if self.host:
            try:
                await self.host.shutdown()
                logger.info("Managed MCPHost shutdown successfully.")
            except Exception as e:
                logger.error(
                    f"Error during managed MCPHost shutdown: {e}", exc_info=True
                )
                # Decide if we should re-raise or just log the error
        else:
            logger.info("No active MCPHost instance to shut down.")

        # Clear internal state regardless of shutdown success/failure
        self.host = None
        self.agent_configs.clear()
        self.workflow_configs.clear()
        self.custom_workflow_configs.clear()
        self.llm_configs.clear()  # Clear LLM configs
        # Dispose the engine if it was created
        if self._db_engine:
            try:
                self._db_engine.dispose()
                logger.info("Disposed managed database engine.")
            except Exception as e:
                logger.error(f"Error disposing database engine: {e}", exc_info=True)
        self._db_engine = None
        self.storage_manager = None  # Clear storage manager too
        logger.info("HostManager internal state cleared.")
        logger.info("HostManager shutdown complete.")

    # --- Registration Methods ---

    async def register_client(self, client_config: "ClientConfig"):
        """
        Dynamically registers and initializes a new MCP client.

        Args:
            client_config: The configuration for the client to register.

        Raises:
            ValueError: If the HostManager is not initialized, or if the client ID already exists.
            Exception: Propagates exceptions from the underlying MCPHost client initialization.
        """
        logger.debug(  # INFO -> DEBUG
            f"Attempting to dynamically register client: {client_config.client_id}"
        )
        if not self.host:
            logger.error("HostManager is not initialized. Cannot register client.")
            raise ValueError("HostManager is not initialized.")

        # Check for duplicate client ID (MCPHost will also check, but good to check early)
        # Accessing host._clients directly might be fragile, consider adding a method to host?
        # For now, following the plan.
        if client_config.client_id in self.host._clients:
            logger.error(f"Client ID '{client_config.client_id}' already registered.")
            raise ValueError(
                f"Client ID '{client_config.client_id}' already registered."
            )

        try:
            # Delegate to MCPHost to handle the actual initialization and lifecycle management
            await self.host.register_client(client_config)
            logger.info(f"Client '{client_config.client_id}' registered successfully.")
        except Exception as e:
            logger.error(
                f"Failed to register client '{client_config.client_id}': {e}",
                exc_info=True,
            )
            # Re-raise the exception for the caller (e.g., API endpoint) to handle
            raise

    async def register_agent(self, agent_config: "AgentConfig"):
        """
        Dynamically registers a new Agent configuration.

        Args:
            agent_config: The configuration for the agent to register.

        Raises:
            ValueError: If the HostManager is not initialized, the agent name already exists,
                        or if any specified client_id is not found.
        """
        logger.debug(
            f"Attempting to dynamically register agent: {agent_config.name}"
        )  # INFO -> DEBUG
        if not self.host:
            logger.error("HostManager is not initialized. Cannot register agent.")
            raise ValueError("HostManager is not initialized.")

        # Ensure agent has a name before registering
        if not agent_config.name:
            logger.error("Attempted to register an agent config with no name.")
            raise ValueError("Agent configuration must have a 'name'.")

        if agent_config.name in self.agent_configs:
            logger.error(f"Agent name '{agent_config.name}' already registered.")
            raise ValueError(f"Agent name '{agent_config.name}' already registered.")

        # Validate client_ids exist using the new host method
        if agent_config.client_ids:
            for client_id in agent_config.client_ids:
                # Use the new public method on the host instance
                if not self.host.is_client_registered(client_id):
                    logger.error(
                        f"Client ID '{client_id}' specified in agent '{agent_config.name}' not found."
                    )
                    raise ValueError(
                        f"Client ID '{client_id}' not found for agent '{agent_config.name}'."
                    )

        # Add the agent config to memory
        self.agent_configs[agent_config.name] = agent_config
        logger.info(f"Agent '{agent_config.name}' registered successfully (in memory).")

        # Sync to DB if enabled
        if self.storage_manager:
            try:
                # Assuming sync_agent_config is synchronous
                self.storage_manager.sync_agent_config(agent_config)
                logger.info(f"Agent '{agent_config.name}' synced to database.")
            except Exception as e:
                # Log error but don't fail registration, as it's in memory
                logger.error(
                    f"Failed to sync agent '{agent_config.name}' to database: {e}",
                    exc_info=True,
                )

    async def register_llm_config(self, llm_config: "LLMConfig"):
        """
        Dynamically registers a new LLM configuration.

        Args:
            llm_config: The configuration for the LLM to register.

        Raises:
            ValueError: If the HostManager is not initialized or the llm_id already exists.
        """
        logger.debug(
            f"Attempting to dynamically register LLM config: {llm_config.llm_id}"
        )
        if not self.host:  # Check self.host, implies manager is initialized
            logger.error("HostManager is not initialized. Cannot register LLM config.")
            raise ValueError("HostManager is not initialized.")

        if llm_config.llm_id in self.llm_configs:
            logger.error(f"LLM config ID '{llm_config.llm_id}' already registered.")
            raise ValueError(f"LLM config ID '{llm_config.llm_id}' already registered.")

        # Add the LLM config to memory
        self.llm_configs[llm_config.llm_id] = llm_config
        logger.info(
            f"LLM config '{llm_config.llm_id}' registered successfully (in memory)."
        )

        # Sync to DB if enabled
        if self.storage_manager:
            try:
                self.storage_manager.sync_llm_config(
                    llm_config
                )  # Assumes method exists
                logger.info(f"LLM config '{llm_config.llm_id}' synced to database.")
            except Exception as e:
                logger.error(
                    f"Failed to sync LLM config '{llm_config.llm_id}' to database: {e}",
                    exc_info=True,
                )

    async def register_workflow(self, workflow_config: "WorkflowConfig"):
        """
        Dynamically registers a new simple Workflow configuration.

        Args:
            workflow_config: The configuration for the workflow to register.

        Raises:
            ValueError: If the HostManager is not initialized, the workflow name already exists,
                        or if any agent name in the steps is not found.
        """
        logger.debug(  # INFO -> DEBUG
            f"Attempting to dynamically register workflow: {workflow_config.name}"
        )
        if not self.host:
            logger.error("HostManager is not initialized. Cannot register workflow.")
            raise ValueError("HostManager is not initialized.")

        if workflow_config.name in self.workflow_configs:
            logger.error(f"Workflow name '{workflow_config.name}' already registered.")
            raise ValueError(
                f"Workflow name '{workflow_config.name}' already registered."
            )

        # Validate agent names in steps exist
        if workflow_config.steps:
            for agent_name in workflow_config.steps:
                if agent_name not in self.agent_configs:
                    logger.error(
                        f"Agent name '{agent_name}' in workflow '{workflow_config.name}' steps not found."
                    )
                    raise ValueError(
                        f"Agent '{agent_name}' not found for workflow '{workflow_config.name}'."
                    )

        # Add the workflow config to memory
        self.workflow_configs[workflow_config.name] = workflow_config
        logger.info(
            f"Workflow '{workflow_config.name}' registered successfully (in memory)."
        )

        # Sync to DB if enabled
        if self.storage_manager:
            try:
                # Assuming sync_workflow_config is synchronous
                self.storage_manager.sync_workflow_config(workflow_config)
                logger.info(f"Workflow '{workflow_config.name}' synced to database.")
            except Exception as e:
                logger.error(
                    f"Failed to sync workflow '{workflow_config.name}' to database: {e}",
                    exc_info=True,
                )

    async def register_custom_workflow(
        self, custom_workflow_config: "CustomWorkflowConfig"
    ):
        """
        Dynamically registers a new custom Workflow configuration.

        Args:
            custom_workflow_config: The configuration for the custom workflow to register.

        Raises:
            ValueError: If the HostManager is not initialized, the custom workflow name already exists,
                        or the module_path is invalid
        """
        logger.debug(  # INFO -> DEBUG
            f"Attempting to dynamically register workflow: {custom_workflow_config.name}"
        )
        if not self.host:
            logger.error(
                "HostManager is not initialized. Cannot register custom workflow."
            )
            raise ValueError("HostManager is not initialized.")

        if custom_workflow_config.name in self.custom_workflow_configs:
            logger.error(
                f"Custom Workflow name '{custom_workflow_config.name}' already registered."
            )
            raise ValueError(
                f"Custom Workflow name '{custom_workflow_config.name}' already registered."
            )

        module_path = custom_workflow_config.module_path
        if not str(module_path.resolve()).startswith(str(PROJECT_ROOT_DIR.resolve())):
            logger.error(
                f"Custom workflow path '{module_path}' is outside the project directory {PROJECT_ROOT_DIR}. Aborting."
            )
            raise ValueError("Custom workflow path is outside the project directory.")

        if not module_path.exists():
            logger.error(f"Custom workflow module file not found: {module_path}")
            raise ValueError(f"Custom workflow module file not found: {module_path}")

        # Add the workflow config to memory
        self.custom_workflow_configs[custom_workflow_config.name] = (
            custom_workflow_config
        )
        logger.info(
            f"Custom Workflow '{custom_workflow_config.name}' registered successfully (in memory)."
        )

        # Sync to DB if enabled
        if self.storage_manager:
            try:
                # Assuming sync_custom_workflow_config is synchronous
                self.storage_manager.sync_custom_workflow_config(custom_workflow_config)
                logger.info(
                    f"Custom Workflow '{custom_workflow_config.name}' synced to database."
                )
            except Exception as e:
                logger.error(
                    f"Failed to sync custom workflow '{custom_workflow_config.name}' to database: {e}",
                    exc_info=True,
                )

    # --- Configuration Access Methods ---

    def get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """Retrieves the configuration for a specific agent by name."""
        return self.agent_configs.get(agent_name)

    def get_llm_config(self, llm_config_id: str) -> Optional[LLMConfig]:
        """Retrieves the configuration for a specific LLM config by ID."""
        return self.llm_configs.get(llm_config_id)

    # Add getters for workflow_configs and custom_workflow_configs if needed later

    # --- Execution Methods --- # Comment remains relevant as a section separator
    # NOTE: The original execute_* methods are removed.
    # Execution is now handled by self.execution (ExecutionFacade instance).
    # Entrypoints (API, CLI, Worker) will need to be updated to call
    # self.execution.run_agent(), self.execution.run_simple_workflow(), etc.
    # (The actual method definitions below are removed by this change)
