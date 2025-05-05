"""
Host Manager for orchestrating MCPHost, Agents, and Workflows.
"""

import logging
import os # Added for environment variable check
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Set

# Assuming this file is in src/, use relative imports
from .config import load_host_config_from_json
from .host.host import MCPHost
from .host.models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    ClientConfig,
)

# Imports needed for execution methods
from .config import PROJECT_ROOT_DIR

# Import the new facade
from .execution.facade import ExecutionFacade

# Setup logger for this module *before* conditional import that might use it
logger = logging.getLogger(__name__)

# Import StorageManager if DB persistence is enabled
try:
    # Use a conditional import based on the flag or handle potential ImportError
    if os.getenv("AURITE_ENABLE_DB", "false").lower() == "true":
        from .storage.db_manager import StorageManager
    else:
        StorageManager = None # Define as None if DB is not enabled
except ImportError:
    logger.warning("Storage module not found or AURITE_ENABLE_DB not set to true. Database persistence disabled.")
    StorageManager = None # Ensure StorageManager is None if import fails


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
        self.storage_manager: Optional["StorageManager"] = None # Added storage manager attribute
        self.execution: Optional[ExecutionFacade] = None

        # Instantiate StorageManager if enabled
        if StorageManager: # Check if the class was imported successfully
            try:
                self.storage_manager = StorageManager()
                # Engine availability check happens within StorageManager.__init__
            except Exception as e:
                logger.error(f"Failed to instantiate StorageManager: {e}", exc_info=True)
                self.storage_manager = None # Ensure it's None if instantiation fails
        else:
             logger.info("Database persistence is disabled (AURITE_ENABLE_DB is not 'true' or storage module failed to import).")


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
        logger.debug(
            f"Initializing HostManager with config: {self.config_path}..."
        )  # INFO -> DEBUG
        try:
            # 1. Load all configurations
            (
                host_config,
                agent_configs_dict,
                workflow_configs_dict,
                custom_workflow_configs_dict,
            ) = load_host_config_from_json(self.config_path)

            # Store configs internally
            self.agent_configs = agent_configs_dict
            self.workflow_configs = workflow_configs_dict
            self.custom_workflow_configs = custom_workflow_configs_dict
            logger.debug("Configurations loaded successfully.")

            # 1.5 Initialize DB Schema if storage manager exists
            if self.storage_manager:
                self.storage_manager.init_db() # Synchronous call for schema creation

            # 2. Instantiate MCPHost
            self.host = MCPHost(
                config=host_config,
                agent_configs=self.agent_configs,
                # Removed workflow_configs argument
                # encryption_key could be passed from a secure source if needed
            )
            logger.debug("MCPHost instance created.")  # INFO -> DEBUG

            # 3. Initialize MCPHost (connects to clients, etc.)
            await self.host.initialize()
            logger.info("MCPHost initialized successfully.")

            # 2.5 Sync initial configs to DB if storage manager exists
            if self.storage_manager:
                 # Assuming sync_all_configs is synchronous for now
                 # If it becomes async, add await here.
                 self.storage_manager.sync_all_configs(
                     agents=self.agent_configs,
                     workflows=self.workflow_configs,
                     custom_workflows=self.custom_workflow_configs
                 )

            # 3. Load additional configs (e.g., prompt validation)
            # This will also sync the loaded configs if DB is enabled via register_* methods
            await self.register_config_file("config/prompt_validation_config.json")

            # 4. Instantiate ExecutionFacade, passing self (the manager) and storage_manager
            self.execution = ExecutionFacade(
                host_manager=self,
                storage_manager=self.storage_manager # Pass storage manager
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
                logger.error(f"Failed to sync agent '{agent_config.name}' to database: {e}", exc_info=True)


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
        logger.info(f"Workflow '{workflow_config.name}' registered successfully (in memory).")

        # Sync to DB if enabled
        if self.storage_manager:
            try:
                # Assuming sync_workflow_config is synchronous
                self.storage_manager.sync_workflow_config(workflow_config)
                logger.info(f"Workflow '{workflow_config.name}' synced to database.")
            except Exception as e:
                logger.error(f"Failed to sync workflow '{workflow_config.name}' to database: {e}", exc_info=True)


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
        self.custom_workflow_configs[custom_workflow_config.name] = custom_workflow_config
        logger.info(
            f"Custom Workflow '{custom_workflow_config.name}' registered successfully (in memory)."
        )

        # Sync to DB if enabled
        if self.storage_manager:
            try:
                # Assuming sync_custom_workflow_config is synchronous
                self.storage_manager.sync_custom_workflow_config(custom_workflow_config)
                logger.info(f"Custom Workflow '{custom_workflow_config.name}' synced to database.")
            except Exception as e:
                logger.error(f"Failed to sync custom workflow '{custom_workflow_config.name}' to database: {e}", exc_info=True)


    # --- Private Registration Helpers ---

    async def _register_clients_from_config(
        self, clients: List[ClientConfig]
    ) -> Tuple[int, int, List[str]]:
        """Registers clients from a loaded list, returning counts and errors."""
        registered_count = 0
        skipped_count = 0
        error_list = []
        logger.debug(f"Registering {len(clients)} clients...")  # INFO -> DEBUG
        for client_config in clients:
            try:
                # Assuming self.host is guaranteed to be initialized here
                await self.host.register_client(client_config)
                registered_count += 1
                logger.debug(
                    f"Successfully registered client: {client_config.client_id}"
                )
            except ValueError as e:  # Catch duplicate client IDs
                logger.warning(
                    f"Skipping client registration for '{client_config.client_id}': {e}"
                )
                skipped_count += 1
            except Exception as e:
                err_msg = f"Failed to register client '{client_config.client_id}': {e}"
                logger.error(err_msg, exc_info=True)
                error_list.append(err_msg)
                skipped_count += 1  # Count as skipped due to error
        return registered_count, skipped_count, error_list

    async def _register_agents_from_config(
        self, agents: Dict[str, AgentConfig]
    ) -> Tuple[int, int, List[str]]:
        """Registers agents from a loaded dict, returning counts and errors."""
        registered_count = 0
        skipped_count = 0
        error_list = []
        logger.debug(f"Registering {len(agents)} agents...")  # INFO -> DEBUG
        for agent_name, agent_config in agents.items():
            try:
                await self.register_agent(
                    agent_config
                )  # Uses internal check for host init
                registered_count += 1
                logger.debug(f"Successfully registered agent: {agent_name}")
            except ValueError as e:  # Catch duplicates or invalid client IDs
                logger.warning(f"Skipping agent registration for '{agent_name}': {e}")
                skipped_count += 1
            except Exception as e:  # Catch unexpected errors
                err_msg = f"Failed to register agent '{agent_name}': {e}"
                logger.error(err_msg, exc_info=True)
                error_list.append(err_msg)
                skipped_count += 1
        return registered_count, skipped_count, error_list

    async def _register_workflows_from_config(
        self,
        workflows: Dict[str, WorkflowConfig],
        available_agents: Set[str],  # Pass the set of available agent names
    ) -> Tuple[int, int, List[str]]:
        """Validates and registers simple workflows, returning counts and errors."""
        registered_count = 0
        skipped_count = 0
        error_list = []
        valid_workflows_to_register = {}
        logger.debug(
            f"Validating {len(workflows)} simple workflows..."
        )  # INFO -> DEBUG

        # First, validate agent references
        for workflow_name, workflow_config in workflows.items():
            is_valid = True
            if workflow_config.steps:
                for step_agent_name in workflow_config.steps:
                    if step_agent_name not in available_agents:
                        err_msg = f"Workflow '{workflow_name}' references unknown agent '{step_agent_name}'. Agent not found in existing or newly loaded configurations."
                        logger.error(err_msg)
                        error_list.append(err_msg)
                        skipped_count += 1
                        is_valid = False
                        break  # No need to check other steps
            if is_valid:
                valid_workflows_to_register[workflow_name] = workflow_config

        # Now register the valid ones
        logger.debug(  # INFO -> DEBUG
            f"Registering {len(valid_workflows_to_register)} valid simple workflows..."
        )
        for workflow_name, workflow_config in valid_workflows_to_register.items():
            try:
                await self.register_workflow(
                    workflow_config
                )  # Uses internal check for host init
                registered_count += 1
                logger.debug(f"Successfully registered workflow: {workflow_name}")
            except ValueError as e:  # Catch duplicates
                logger.warning(
                    f"Skipping workflow registration for '{workflow_name}': {e}"
                )
                skipped_count += 1
            except Exception as e:  # Catch unexpected errors
                err_msg = f"Failed to register workflow '{workflow_name}': {e}"
                logger.error(err_msg, exc_info=True)
                error_list.append(err_msg)
                skipped_count += 1
        return registered_count, skipped_count, error_list

    async def _register_custom_workflows_from_config(
        self, custom_workflows: Dict[str, CustomWorkflowConfig]
    ) -> Tuple[int, int, List[str]]:
        """Registers custom workflows from a loaded dict, returning counts and errors."""
        registered_count = 0
        skipped_count = 0
        error_list = []
        logger.debug(
            f"Registering {len(custom_workflows)} custom workflows..."
        )  # INFO -> DEBUG
        for cwf_name, cwf_config in custom_workflows.items():
            try:
                await self.register_custom_workflow(
                    cwf_config
                )  # Uses internal check for host init
                registered_count += 1
                logger.debug(f"Successfully registered custom workflow: {cwf_name}")
            except ValueError as e:  # Catch duplicates or invalid paths
                logger.warning(
                    f"Skipping custom workflow registration for '{cwf_name}': {e}"
                )
                skipped_count += 1
            except Exception as e:  # Catch unexpected errors
                err_msg = f"Failed to register custom workflow '{cwf_name}': {e}"
                logger.error(err_msg, exc_info=True)
                error_list.append(err_msg)
                skipped_count += 1
        return registered_count, skipped_count, error_list

    async def register_config_file(self, file_path: Path):
        """
        Dynamically loads and registers all components (clients, agents, workflows, custom workflows)
        from a specified JSON configuration file path.

        Args:
            file_path: The Path object pointing to the JSON configuration file.

        Raises:
            ValueError: If the HostManager is not initialized.
            FileNotFoundError: If the specified file_path does not exist.
            RuntimeError: If there's an error parsing the config file or during registration.
        """
        logger.debug(  # INFO -> DEBUG
            f"Attempting to dynamically register components from file: {file_path}"
        )
        if not self.host:
            logger.error("HostManager is not initialized. Cannot register from file.")
            raise ValueError("HostManager is not initialized.")

        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        if not file_path.is_absolute():
            logger.warning(
                f"Provided file path is not absolute: {file_path}. Resolving relative to CWD."
            )
            file_path = file_path.resolve()

        if not file_path.is_file():
            logger.error(f"Configuration file not found at path: {file_path}")
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        all_registered_counts = {
            "clients": 0,
            "agents": 0,
            "workflows": 0,
            "custom_workflows": 0,
        }
        all_skipped_counts = {
            "clients": 0,
            "agents": 0,
            "workflows": 0,
            "custom_workflows": 0,
        }
        all_error_messages = []

        try:
            # 1. Load all configurations from the specified file
            (
                host_config,
                agent_configs_dict,
                workflow_configs_dict,
                custom_workflow_configs_dict,
            ) = load_host_config_from_json(file_path)
            logger.debug(
                f"Successfully loaded configurations from {file_path}."
            )  # INFO -> DEBUG

            # 2. Register Clients using helper
            reg_c, skip_c, err_c = await self._register_clients_from_config(
                host_config.clients
            )
            all_registered_counts["clients"] = reg_c
            all_skipped_counts["clients"] = skip_c
            all_error_messages.extend(err_c)

            # 3. Register Agents using helper
            reg_a, skip_a, err_a = await self._register_agents_from_config(
                agent_configs_dict
            )
            all_registered_counts["agents"] = reg_a
            all_skipped_counts["agents"] = skip_a
            all_error_messages.extend(err_a)

            # 4. Register Workflows using helper
            # Need the combined set of agent names for validation
            available_agent_names = set(
                self.agent_configs.keys()
            )  # Already registered + newly registered
            reg_w, skip_w, err_w = await self._register_workflows_from_config(
                workflow_configs_dict, available_agent_names
            )
            all_registered_counts["workflows"] = reg_w
            all_skipped_counts["workflows"] = skip_w
            all_error_messages.extend(err_w)

            # 5. Register Custom Workflows using helper
            reg_cw, skip_cw, err_cw = await self._register_custom_workflows_from_config(
                custom_workflow_configs_dict
            )
            all_registered_counts["custom_workflows"] = reg_cw
            all_skipped_counts["custom_workflows"] = skip_cw
            all_error_messages.extend(err_cw)

            # Log summary
            summary_msg = (
                f"Finished processing config file '{file_path}'. "
                f"Registered: {all_registered_counts}. Skipped: {all_skipped_counts}."
            )
            if all_error_messages:
                summary_msg += f" Encountered {len(all_error_messages)} errors during registration."
                logger.error(summary_msg)
                # Optionally re-raise a generic error if any individual errors occurred
                # raise RuntimeError(f"Errors occurred during dynamic registration from {file_path}. See logs for details.")
            else:
                logger.info(summary_msg)

        except (FileNotFoundError, RuntimeError, ValueError) as e:
            # Catch errors from load_host_config_from_json or initial checks
            logger.error(
                f"Error processing config file {file_path}: {e}", exc_info=True
            )
            raise  # Re-raise the original exception
        except Exception as e:
            # Catch any other unexpected errors during the process
            logger.error(
                f"Unexpected error during registration from file {file_path}: {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Unexpected error during registration from {file_path}: {e}"
            ) from e

    # --- Execution Methods ---
    # NOTE: The original execute_* methods are removed.
    # Execution is now handled by self.execution (ExecutionFacade instance).
    # Entrypoints (API, CLI, Worker) will need to be updated to call
    # self.execution.run_agent(), self.execution.run_simple_workflow(), etc.
    # (The actual method definitions below are removed by this change)
