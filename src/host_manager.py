"""
Host Manager for orchestrating MCPHost, Agents, and Workflows.
"""

import logging
import os  # Added for environment variable check
from pathlib import Path
from typing import (
    Optional,
    AsyncGenerator,
    Dict,
    Any,
)  # Added AsyncGenerator, Dict, Any

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
        self.storage_manager: Optional["StorageManager"] = None  # Initialize as None
        self.execution: Optional[ExecutionFacade] = None
        self._db_engine = None  # Store engine if created
        # Instantiate ComponentManager first, as ProjectManager needs it
        self.component_manager = ComponentManager()
        self.project_manager = ProjectManager(
            self.component_manager
        )  # Pass component manager

        # Check if dynamic registration is allowed
        self._dynamic_registration_enabled = os.getenv("AURITE_ALLOW_DYNAMIC_REGISTRATION", "false").lower() == "true"
        if self._dynamic_registration_enabled:
            logger.info("Dynamic registration is ENABLED via AURITE_ALLOW_DYNAMIC_REGISTRATION.")
        else:
            logger.info("Dynamic registration is DISABLED via AURITE_ALLOW_DYNAMIC_REGISTRATION. Registration methods will raise an error if called.")

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
            logger.debug(  # Changed to DEBUG
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
        logger.debug(  # Changed to DEBUG
            f"Initializing HostManager with project config: {self.config_path}..."
        )
        try:
            # 1. Load Project Configuration using ProjectManager
            logger.debug(f"Loading project configuration from {self.config_path}...")
            # load_project now sets active_project_config in project_manager
            self.project_manager.load_project(self.config_path)
            active_project = self.project_manager.get_active_project_config()
            if not active_project:  # Ensure active_project is not None
                raise RuntimeError(
                    f"Failed to load project '{self.config_path}' into ProjectManager."
                )
            logger.debug(  # Changed to DEBUG
                f"Project '{active_project.name}' loaded successfully and set as active."
            )

            # Configs are now accessed via project_manager.get_active_project_config()
            logger.debug(
                f"Active project '{active_project.name}' has {len(active_project.agents)} agents, "  # Changed agent_configs to agents
                f"{len(active_project.llms)} LLMs, "  # Changed llm_configs to llms
                f"{len(active_project.simple_workflows)} simple workflows, "  # Changed simple_workflow_configs to simple_workflows
                f"{len(active_project.custom_workflows)} custom workflows."  # Changed custom_workflow_configs to custom_workflows
            )

            # 1.5 Initialize DB Schema if storage manager exists
            if self.storage_manager:
                self.storage_manager.init_db()

            # 2. Construct HostConfig for MCPHost from ProjectManager
            host_config_for_mcphost = (
                self.project_manager.get_host_config_for_active_project()
            )
            if not host_config_for_mcphost:  # Ensure host_config is not None
                raise RuntimeError(
                    "Failed to get HostConfig from ProjectManager for active project."
                )
            logger.debug("HostConfig constructed for MCPHost.")

            # Instantiate MCPHost
            logger.debug("Instantiating MCPHost...")
            self.host = MCPHost(config=host_config_for_mcphost)
            logger.debug("MCPHost instance created.")

            # 3. Initialize MCPHost
            logger.debug("Initializing MCPHost (connecting clients)...")
            await self.host.initialize()
            logger.debug("MCPHost initialized successfully.")  # Changed to DEBUG

            # 2.5 Sync initial configs to DB if storage manager exists
            if (
                self.storage_manager and active_project
            ):  # Ensure active_project for safety
                logger.debug("Syncing loaded configurations to database...")
                self.storage_manager.sync_all_configs(
                    agents=active_project.agents,  # Changed agent_configs to agents
                    workflows=active_project.simple_workflows,  # Changed simple_workflow_configs to simple_workflows
                    custom_workflows=active_project.custom_workflows,  # Changed custom_workflow_configs to custom_workflows
                    llm_configs=active_project.llms,  # Changed llm_configs to llms
                )
                logger.debug("Database sync complete.")

            # 4. Instantiate ExecutionFacade
            logger.debug("Instantiating ExecutionFacade...")
            if (
                not self.host or not active_project
            ):  # Ensure host and active_project are not None
                raise RuntimeError(
                    "Cannot instantiate ExecutionFacade: Host or active_project is not initialized."
                )
            self.execution = ExecutionFacade(
                host_instance=self.host,
                current_project=active_project,
                storage_manager=self.storage_manager,
            )
            
            # 5. Load additional config
            prompt_validation_path = Path("config/projects/prompt_validation_config.json")
            if not prompt_validation_path.is_file():
                logger.warning(
                    f"Prompt validation config not found. Expected at {prompt_validation_path}"
                )
            else:
                await self.load_components_from_project(prompt_validation_path)

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
            # Ensure a more specific error message if this generic block is hit
            detailed_error_msg = f"HostManager.initialize failed in generic exception handler: {type(e).__name__}: {str(e)}"
            logger.error(detailed_error_msg, exc_info=True)
            raise RuntimeError(detailed_error_msg) from e

    async def shutdown(self):
        """
        Shuts down the managed MCPHost and cleans up resources.
        """
        logger.debug("Shutting down HostManager...")  # Changed to DEBUG
        if self.host:
            try:
                await self.host.shutdown()
                logger.debug(
                    "Managed MCPHost shutdown successfully."
                )  # Changed to DEBUG
            except Exception as e:
                # Check for known anyio issues, which might be wrapped in an ExceptionGroup
                actual_exception_to_check = e
                # Check if it's an ExceptionGroup (anyio.exceptions.ExceptionGroup inherits from BaseExceptionGroup)
                # and if the first exception is a RuntimeError
                if (
                    hasattr(e, "exceptions")
                    and isinstance(e.exceptions, list)
                    and len(e.exceptions) > 0
                    and isinstance(e.exceptions[0], RuntimeError)
                ):
                    actual_exception_to_check = e.exceptions[0]

                is_known_anyio_issue = False
                if isinstance(actual_exception_to_check, RuntimeError):
                    exc_str = str(actual_exception_to_check).lower()
                    if (
                        "attempted to exit cancel scope" in exc_str
                        or "event loop is closed" in exc_str
                        or "cannot run shutdown() while loop is stopping" in exc_str
                    ):
                        is_known_anyio_issue = True

                if is_known_anyio_issue:
                    # Log the specific RuntimeError and the original exception type if it was a group
                    original_exc_type_name = type(e).__name__
                    logger.warning(
                        f"Known anyio issue during MCPHost shutdown (Original: {original_exc_type_name}): {actual_exception_to_check}"
                    )
                else:
                    # Log the original exception 'e' if it's not the specific anyio issue we're handling gently
                    logger.error(
                        f"Error during managed MCPHost shutdown: {e}", exc_info=True
                    )
                    # Decide if we should re-raise or just log the error for other exceptions
        else:
            logger.info("No active MCPHost instance to shut down.")

        # Clear internal state regardless of shutdown success/failure
        self.host = None
        # self.agent_configs.clear() # Removed
        # self.workflow_configs.clear() # Removed
        # self.custom_workflow_configs.clear() # Removed
        # self.llm_configs.clear()  # Removed
        # Dispose the engine if it was created
        if self._db_engine:
            try:
                self._db_engine.dispose()
                logger.info("Disposed managed database engine.")
            except Exception as e:
                logger.error(f"Error disposing database engine: {e}", exc_info=True)
        self._db_engine = None
        self.storage_manager = None  # Clear storage manager too
        logger.debug("HostManager internal state cleared.")  # Changed to DEBUG
        logger.info("HostManager shutdown complete.")

    async def unload_project(self):
        """
        Shuts down the current MCPHost instance and clears loaded project configurations.
        """
        logger.info("Unloading current project and shutting down host...")
        if self.host:
            try:
                # MCPHost.shutdown() handles shutting down clients via ClientManager
                await self.host.shutdown()
                logger.info("Managed MCPHost shutdown successfully during unload.")
            except Exception as e:
                # Check for known anyio issues, which might be wrapped in an ExceptionGroup
                actual_exception_to_check = e
                # Check if it's an ExceptionGroup (anyio.exceptions.ExceptionGroup inherits from BaseExceptionGroup)
                # and if the first exception is a RuntimeError
                if (
                    hasattr(e, "exceptions")
                    and isinstance(e.exceptions, list)
                    and len(e.exceptions) > 0
                    and isinstance(e.exceptions[0], RuntimeError)
                ):
                    actual_exception_to_check = e.exceptions[0]

                is_known_anyio_issue = False
                if isinstance(actual_exception_to_check, RuntimeError):
                    exc_str = str(actual_exception_to_check).lower()
                    if (
                        "attempted to exit cancel scope" in exc_str
                        or "event loop is closed" in exc_str
                        or "cannot run shutdown() while loop is stopping" in exc_str
                    ):
                        is_known_anyio_issue = True

                if is_known_anyio_issue:
                    # Log the specific RuntimeError and the original exception type if it was a group
                    original_exc_type_name = type(e).__name__
                    logger.warning(
                        f"Known anyio issue during MCPHost shutdown on unload (Original: {original_exc_type_name}): {actual_exception_to_check}"
                    )
                else:
                    # Log the original exception 'e' if it's not the specific anyio issue we're handling gently
                    logger.error(
                        f"Error during managed MCPHost shutdown on unload: {e}",
                        exc_info=True,
                    )
                    # For unload, we generally prefer to continue to clear state, so we don't re-raise here.
        else:
            logger.info("No active MCPHost instance to shut down during unload.")

        # Clear internal state related to the project
        self.host = None
        # self.current_project = None # Removed, project_manager handles active project state
        if self.project_manager:  # Ensure project_manager exists
            self.project_manager.unload_active_project()
        self.execution = None  # Clear the facade instance

        # The old dictionaries like self.agent_configs are already removed from the class.
        # Their state was tied to self.current_project which is now managed by ProjectManager.
        # Note: We keep the ComponentManager and ProjectManager instances,
        # as they manage the available components and project loading logic,
        # which might be needed for the next project.
        # We also keep the DB engine/storage manager if it exists, assuming
        # it might be used across projects or needs separate lifecycle management.
        logger.info("Current project configurations cleared.")
        logger.info("Project unload complete.")

    async def change_project(self, new_project_config_path: Path):
        """
        Unloads the current project and initializes the HostManager with a new project configuration.

        Args:
            new_project_config_path: The absolute path to the new project's JSON configuration file.
        """
        logger.info(f"Attempting to change project to: {new_project_config_path}...")
        # Ensure path is absolute
        if not new_project_config_path.is_absolute():
            logger.warning(
                f"New project path {new_project_config_path} is not absolute. Resolving."
            )
            new_project_config_path = new_project_config_path.resolve()

        # Unload current project and host
        await self.unload_project()

        # Update the config path for the next initialization
        self.config_path = new_project_config_path
        logger.info(f"HostManager config path updated to: {self.config_path}")

        # Initialize with the new project config
        # This will load the new project, create a new MCPHost, connect clients, etc.
        try:
            await self.initialize()
            logger.info(
                f"Successfully changed project and initialized with {self.config_path}."
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize HostManager after changing project to {self.config_path}: {e}",
                exc_info=True,
            )
            # Ensure state is clean even after failed initialization
            await self.unload_project()  # Call unload again to be safe
            raise  # Re-raise the exception so the caller knows it failed

    # --- Registration Methods ---

    async def register_client(
        self, client_config: ClientConfig
    ):  # Removed quotes from type hint
        """
        Dynamically registers and initializes a new MCP client.
        Updates the active project configuration upon successful registration.

        Args:
            client_config: The configuration for the client to register.

        Raises:
            ValueError: If the HostManager is not initialized, or if the client ID already exists.
            PermissionError: If dynamic registration is disabled.
            Exception: Propagates exceptions from the underlying MCPHost client initialization.
        """
        if not self._dynamic_registration_enabled:
            logger.error("Dynamic registration is disabled. Cannot register client.")
            raise PermissionError("Dynamic registration is disabled by configuration.")

        logger.debug(
            f"Attempting to dynamically register client: {client_config.client_id}"
        )
        if not self.host:
            logger.error("HostManager is not initialized. Cannot register client.")
            raise ValueError("HostManager is not initialized.")

        active_project = self.project_manager.get_active_project_config()
        if not active_project:
            logger.error("Cannot register client: No active project loaded.")
            raise RuntimeError("No active project loaded to register client against.")

        # Check for duplicate client ID using the host's method
        if self.host.is_client_registered(client_config.client_id):
            logger.info( # Changed from error to info
                f"Client ID '{client_config.client_id}' already registered with host. Updating configuration."
            )
            # Potentially unregister/reregister or update existing client in MCPHost
            # For now, we assume MCPHost.register_client can handle updates or we rely on ProjectManager update.
            # If MCPHost.register_client doesn't update, this might need more logic here or in MCPHost.
        # else: # No longer raising ValueError, proceed to register/update

        try:
            # Delegate to MCPHost to handle the actual initialization and lifecycle management
            # This might need to change if MCPHost.register_client cannot update.
            # If it can't, we might need an unregister_client then register_client,
            # or an update_client method on MCPHost.
            # For now, assume it handles it or ProjectManager update is sufficient for config.
            if not self.host.is_client_registered(client_config.client_id):
                 await self.host.register_client(client_config) # Only call if truly new to host
            else:
                 # If client is already on host, we might need an update mechanism on host
                 # For now, we'll update the project config and assume host might pick up changes
                 # or a restart/re-init of client is needed for host to see changes.
                 # This part of upsert for clients needs careful consideration of MCPHost capabilities.
                 logger.info(f"Client '{client_config.client_id}' already on host. Project config will be updated.")


            # If successful, add/update in the active project's configuration
            self.project_manager.add_component_to_active_project(
                "clients", client_config.client_id, client_config
            )
            logger.info(
                f"Client '{client_config.client_id}' (re)registered successfully with host and active project."
            )
        except Exception as e:
            logger.error(
                f"Failed to register/update client '{client_config.client_id}' with host: {e}",
                exc_info=True,
            )
            # Re-raise the exception for the caller (e.g., API endpoint) to handle
            raise

    async def register_agent(self, agent_config: AgentConfig):  # Removed quotes
        """
        Dynamically registers or updates an Agent configuration (upsert).

        Args:
            agent_config: The configuration for the agent to register/update.

        Raises:
            ValueError: If the HostManager is not initialized, or if any specified client_id is not found.
            PermissionError: If dynamic registration is disabled.
        """
        if not self._dynamic_registration_enabled:
            logger.error("Dynamic registration is disabled. Cannot register agent.")
            raise PermissionError("Dynamic registration is disabled by configuration.")

        logger.debug(
            f"Attempting to dynamically register/update agent: {agent_config.name}"
        )
        if not self.host:
            logger.error("HostManager is not initialized. Cannot register/update agent.")
            raise ValueError("HostManager is not initialized.")

        active_project = self.project_manager.get_active_project_config()
        if not active_project:
            logger.error("Cannot register/update agent: No active project loaded.")
            raise RuntimeError("No active project loaded to register/update agent against.")

        # Ensure agent has a name before registering
        if not agent_config.name:
            logger.error("Attempted to register/update an agent config with no name.")
            raise ValueError("Agent configuration must have a 'name'.")

        if (
            agent_config.name in active_project.agents
        ):
            logger.info(
                f"Agent name '{agent_config.name}' already exists in active project. It will be updated."
            )
        # else: # No longer raising ValueError, proceed to create/update

        # Cascading LLMConfig registration/update
        if agent_config.llm_config_id:
            logger.info(
                f"Agent '{agent_config.name}' specifies LLM config ID '{agent_config.llm_config_id}'. Attempting to register/update it."
            )
            try:
                retrieved_llm_config = self.component_manager.get_component_config(
                    "llm_configs", agent_config.llm_config_id
                )
                if retrieved_llm_config:
                    # Type cast to LLMConfig if get_component_config returns BaseModel
                    from .config.config_models import (
                        LLMConfig as LLMConfigModel,
                    )  # Local import for type hint

                    if isinstance(retrieved_llm_config, LLMConfigModel):
                        await self.register_llm_config(retrieved_llm_config)
                    else:
                        logger.error(
                            f"Retrieved component for LLM ID '{agent_config.llm_config_id}' is not an LLMConfig. Type: {type(retrieved_llm_config)}"
                        )
                        # Decide if this is a hard error or just a warning
                else:
                    logger.warning(
                        f"LLMConfig ID '{agent_config.llm_config_id}' for agent '{agent_config.name}' not found in ComponentManager. Agent might rely on overrides or fail."
                    )
            except Exception as e:
                logger.error(
                    f"Error during cascading registration of LLMConfig '{agent_config.llm_config_id}' for agent '{agent_config.name}': {e}",
                    exc_info=True,
                )
                # Decide if this should be a hard error for agent registration

        # Validate client_ids exist using the host's method
        if agent_config.client_ids:
            for client_id in agent_config.client_ids:
                if not self.host.is_client_registered(client_id):
                    logger.error(
                        f"Client ID '{client_id}' specified in agent '{agent_config.name}' not found in active host clients."
                    )
                    raise ValueError(
                        f"Client ID '{client_id}' not found for agent '{agent_config.name}'."
                    )

        # Validate llm_config_id if present
        if agent_config.llm_config_id:
            if (
                not active_project.llms  # Changed llm_configs to llms
                or agent_config.llm_config_id
                not in active_project.llms  # Changed llm_configs to llms
            ):
                logger.error(
                    f"LLMConfig ID '{agent_config.llm_config_id}' specified in agent '{agent_config.name}' not found in active project."
                )
                raise ValueError(
                    f"LLMConfig ID '{agent_config.llm_config_id}' not found for agent '{agent_config.name}'."
                )

        # Add the agent config to the active project
        # Ensure component_type_key matches the new attribute name in ProjectConfig
        self.project_manager.add_component_to_active_project(
            "agents",
            agent_config.name,
            agent_config,  # Changed "agent_configs" to "agents"
        )
        # Note: self.agent_configs attribute is removed, direct update to project_manager's state.
        logger.info(
            f"Agent '{agent_config.name}' registered successfully in active project."
        )

        # Sync to DB if enabled
        if self.storage_manager:
            try:
                self.storage_manager.sync_agent_config(agent_config)
                logger.info(f"Agent '{agent_config.name}' synced to database.")
            except Exception as e:
                logger.error(
                    f"Failed to sync agent '{agent_config.name}' to database: {e}",
                    exc_info=True,
                )

    async def register_llm_config(self, llm_config: LLMConfig):
        """
        Dynamically registers a new LLM configuration.

        Args:
            llm_config: The configuration for the LLM to register.

        Raises:
            ValueError: If the HostManager is not initialized or the llm_id already exists.
            RuntimeError: If no active project is loaded.
            PermissionError: If dynamic registration is disabled.
        """
        if not self._dynamic_registration_enabled:
            logger.error("Dynamic registration is disabled. Cannot register LLM config.")
            raise PermissionError("Dynamic registration is disabled by configuration.")

        logger.debug(
            f"Attempting to dynamically register LLM config: {llm_config.llm_id}"
        )
        if not self.host:  # Check self.host, implies manager is initialized
            logger.error("HostManager is not initialized. Cannot register LLM config.")
            raise ValueError("HostManager is not initialized.")

        active_project = self.project_manager.get_active_project_config()
        if not active_project:
            logger.error("Cannot register LLM config: No active project loaded.")
            raise RuntimeError(
                "No active project loaded to register LLM config against."
            )

        if llm_config.llm_id in active_project.llms:  # Changed llm_configs to llms
            logger.info(  # Changed from error to info, and adjusted message
                f"LLM config ID '{llm_config.llm_id}' already exists in active project. It will be updated."
            )
            # No longer raising ValueError, proceeding to update via add_component_to_active_project

        # Add the LLM config to the active project (this will overwrite/update if ID exists)
        # Ensure component_type_key matches the new attribute name in ProjectConfig
        self.project_manager.add_component_to_active_project(
            "llms",
            llm_config.llm_id,
            llm_config,  # Changed "llm_configs" to "llms"
        )
        logger.info(
            f"LLM config '{llm_config.llm_id}' registered successfully in active project."
        )

        # Sync to DB if enabled
        if self.storage_manager:
            try:
                self.storage_manager.sync_llm_config(llm_config)
                logger.info(f"LLM config '{llm_config.llm_id}' synced to database.")
            except Exception as e:
                logger.error(
                    f"Failed to sync LLM config '{llm_config.llm_id}' to database: {e}",
                    exc_info=True,
                )

    async def register_workflow(
        self, workflow_config: WorkflowConfig
    ):  # Removed quotes
        """
        Dynamically registers a new simple Workflow configuration.

        Args:
            workflow_config: The configuration for the workflow to register.

        Raises:
            ValueError: If the HostManager is not initialized, the workflow name already exists,
                        or if any agent name in the steps is not found.
            PermissionError: If dynamic registration is disabled.
        """
        if not self._dynamic_registration_enabled:
            logger.error("Dynamic registration is disabled. Cannot register workflow.")
            raise PermissionError("Dynamic registration is disabled by configuration.")

        logger.debug(  # INFO -> DEBUG
            f"Attempting to dynamically register workflow: {workflow_config.name}"
        )
        if not self.host:
            logger.error("HostManager is not initialized. Cannot register workflow.")
            raise ValueError("HostManager is not initialized.")

        active_project = self.project_manager.get_active_project_config()
        if not active_project:
            logger.error("Cannot register workflow: No active project loaded.")
            raise RuntimeError("No active project loaded to register workflow against.")

        if (
            workflow_config.name in active_project.simple_workflows
        ):  # Changed simple_workflow_configs to simple_workflows
            logger.info(
                f"Workflow name '{workflow_config.name}' already exists in active project. It will be updated."
            )
        else:  # New workflow
            logger.info(f"Registering new workflow: {workflow_config.name}")
        # No longer raising ValueError, proceed to create/update

        # Cascading Agent registration/update for steps
        if workflow_config.steps:
            for agent_name_step in workflow_config.steps: # Renamed to avoid conflict
                logger.info(
                    f"Workflow '{workflow_config.name}' step: Agent '{agent_name_step}'. Attempting to register/update it."
                )
                try:
                    retrieved_agent_config_step = self.component_manager.get_component_config(
                        "agents",
                        agent_name_step,
                    )
                    if retrieved_agent_config_step:
                        from .config.config_models import (
                            AgentConfig as AgentConfigModel,
                        )
                        if isinstance(retrieved_agent_config_step, AgentConfigModel):
                            # register_agent now handles upsert, so we can call it directly.
                            # It will create if new, or update if existing.
                            await self.register_agent(
                                retrieved_agent_config_step
                            )
                        else:
                            logger.error(
                                f"Retrieved component for Agent step '{agent_name_step}' in workflow '{workflow_config.name}' is not an AgentConfig. Type: {type(retrieved_agent_config_step)}. Skipping this step's agent registration."
                            )
                            raise ValueError(
                                f"Component for agent step '{agent_name_step}' in workflow '{workflow_config.name}' is not a valid AgentConfig."
                            )
                    else:
                        logger.error(
                            f"Agent '{agent_name_step}' (a step in workflow '{workflow_config.name}') not found in ComponentManager. Cannot register workflow."
                        )
                        raise ValueError(
                            f"Agent step '{agent_name_step}' for workflow '{workflow_config.name}' not found in ComponentManager."
                        )
                # ValueError from register_agent (e.g. client_id not found) should propagate
                except Exception as e:
                    logger.error(
                        f"Error during cascading registration/update of agent step '{agent_name_step}' for workflow '{workflow_config.name}': {e}",
                        exc_info=True,
                    )
                    raise  # Re-raise to stop workflow registration if a step agent fails

        # Add/Update the workflow config to the active project
        self.project_manager.add_component_to_active_project(
            "simple_workflows",
            workflow_config.name,
            workflow_config,  # Changed "simple_workflow_configs" to "simple_workflows"
        )
        logger.info(
            f"Workflow '{workflow_config.name}' registered successfully in active project."
        )

        # Sync to DB if enabled
        if self.storage_manager:
            try:
                self.storage_manager.sync_workflow_config(workflow_config)
                logger.info(f"Workflow '{workflow_config.name}' synced to database.")
            except Exception as e:
                logger.error(
                    f"Failed to sync workflow '{workflow_config.name}' to database: {e}",
                    exc_info=True,
                )

    async def register_custom_workflow(
        self,
        custom_workflow_config: CustomWorkflowConfig,  # Removed quotes
    ):
        """
        Dynamically registers a new custom Workflow configuration.

        Args:
            custom_workflow_config: The configuration for the custom workflow to register.

        Raises:
            ValueError: If the HostManager is not initialized, the custom workflow name already exists,
                        or the module_path is invalid.
            PermissionError: If dynamic registration is disabled.
        """
        if not self._dynamic_registration_enabled:
            logger.error("Dynamic registration is disabled. Cannot register custom workflow.")
            raise PermissionError("Dynamic registration is disabled by configuration.")

        logger.debug(  # INFO -> DEBUG
            f"Attempting to dynamically register workflow: {custom_workflow_config.name}"
        )
        if not self.host:
            logger.error(
                "HostManager is not initialized. Cannot register custom workflow."
            )
            raise ValueError("HostManager is not initialized.")

        active_project = self.project_manager.get_active_project_config()
        if not active_project:
            logger.error("Cannot register custom workflow: No active project loaded.")
            raise RuntimeError(
                "No active project loaded to register custom workflow against."
            )

        if (
            custom_workflow_config.name in active_project.custom_workflows
        ):  # Changed custom_workflow_configs to custom_workflows
            logger.info(  # Changed from error to info
                f"Custom Workflow name '{custom_workflow_config.name}' already exists in active project. It will be updated."
            )
            # No longer raising ValueError
        # else: # Removed else block, logging for new/update is handled by add_component_to_active_project or could be added before it.
        # logger.info(
        # f"Registering new custom workflow: {custom_workflow_config.name}"
        # )

        module_path = custom_workflow_config.module_path
        if not str(module_path.resolve()).startswith(str(PROJECT_ROOT_DIR.resolve())):
            logger.error(
                f"Custom workflow path '{module_path}' is outside the project directory {PROJECT_ROOT_DIR}. Aborting."
            )
            raise ValueError("Custom workflow path is outside the project directory.")

        if not module_path.exists():
            logger.error(f"Custom workflow module file not found: {module_path}")
            raise ValueError(f"Custom workflow module file not found: {module_path}")

        # Add the workflow config to the active project
        # Ensure component_type_key matches the new attribute name in ProjectConfig
        self.project_manager.add_component_to_active_project(
            "custom_workflows",  # Changed "custom_workflow_configs" to "custom_workflows"
            custom_workflow_config.name,
            custom_workflow_config,
        )
        logger.info(
            f"Custom Workflow '{custom_workflow_config.name}' registered successfully in active project."
        )

        # Sync to DB if enabled
        if self.storage_manager:
            try:
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
        """Retrieves the configuration for a specific agent by name from the active project."""
        active_project = self.project_manager.get_active_project_config()
        if active_project and active_project.agents:  # Changed agent_configs to agents
            return active_project.agents.get(
                agent_name
            )  # Changed agent_configs to agents
        return None

    def get_llm_config(self, llm_config_id: str) -> Optional[LLMConfig]:
        """Retrieves the configuration for a specific LLM config by ID from the active project."""
        active_project = self.project_manager.get_active_project_config()
        if active_project and active_project.llms:  # Changed llm_configs to llms
            return active_project.llms.get(llm_config_id)  # Changed llm_configs to llms
        return None

    # Add getters for simple_workflows and custom_workflows if needed later

    # --- Execution Methods --- # Comment remains relevant as a section separator
    # NOTE: The original execute_* methods are removed.
    # Execution is now handled by self.execution (ExecutionFacade instance).
    # Entrypoints (API, CLI, Worker) will need to be updated to call
    # self.execution.run_agent(), self.execution.run_simple_workflow(), etc.
    # (The actual method definitions below are removed by this change)

    async def stream_agent_run_via_facade(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams an agent run by delegating to the ExecutionFacade.
        """
        if not self.execution:
            logger.error("ExecutionFacade not available on HostManager for streaming.")
            # Yield an error event or raise an exception
            # For now, let's yield an error event consistent with facade's stream_agent_run
            yield {
                "event_type": "error",
                "data": {
                    "message": "Execution subsystem not available for streaming.",
                    "agent_name": agent_name,
                },
            }
            return

        logger.debug(
            f"HostManager delegating streaming run for agent '{agent_name}' to ExecutionFacade."
        )
        async for event in self.execution.stream_agent_run(
            agent_name=agent_name,
            user_message=user_message,
            system_prompt=system_prompt,
            session_id=session_id,
        ):
            yield event

    async def load_components_from_project(self, project_config_path: Path):
        """
        Loads components from a specified project configuration file and adds them
        to the active project. If no project is active, this will initialize
        the HostManager with the specified project.

        Args:
            project_config_path: Path to the project JSON file to load components from.
        """
        logger.info(
            f"Attempting to load components from project: {project_config_path}"
        )
        if not project_config_path.is_absolute():
            project_config_path = (PROJECT_ROOT_DIR / project_config_path).resolve()
            logger.debug(f"Resolved relative path to: {project_config_path}")

        if not project_config_path.is_file():
            logger.error(f"Project config file not found at: {project_config_path}")
            raise FileNotFoundError(
                f"Project configuration file not found: {project_config_path}"
            )

        try:
            parsed_config = self.project_manager.parse_project_file(project_config_path)
            logger.info(f"Successfully parsed project file: {project_config_path.name}")

            active_project_config = self.project_manager.get_active_project_config()

            if not active_project_config or not self.host:
                logger.info(
                    "No active project or host. Initializing with the new project."
                )
                # This effectively becomes an initial load.
                # We need to set the config_path for initialize to use the correct one.
                self.config_path = project_config_path
                await self.initialize()
                logger.info(
                    f"HostManager initialized with project: {parsed_config.name}"
                )
                return  # Initialization handles everything

            # Project is already active, add components additively
            logger.info(
                f"Adding components from '{parsed_config.name}' to active project '{active_project_config.name}'."
            )

            # Add Clients
            for client_id, client_config in parsed_config.clients.items():
                if not self.host.is_client_registered(client_id):
                    try:
                        logger.debug(f"Registering new client: {client_id}")
                        await self.register_client(client_config)
                    except (
                        ValueError
                    ) as e:  # Catch if client already registered by another call
                        logger.warning(f"Skipping client {client_id}: {e}")
                    except Exception as e:
                        logger.error(
                            f"Error registering client {client_id}: {e}", exc_info=True
                        )
                else:
                    logger.debug(f"Client {client_id} already registered. Skipping.")

            # Add LLM Configs
            for (
                llm_id,
                llm_config,
            ) in parsed_config.llms.items():  # Changed llm_configs to llms
                if (
                    llm_id not in active_project_config.llms
                ):  # Changed llm_configs to llms
                    try:
                        logger.debug(f"Registering new LLM config: {llm_id}")
                        await self.register_llm_config(llm_config)
                    except ValueError as e:
                        logger.warning(f"Skipping LLM config {llm_id}: {e}")
                    except Exception as e:
                        logger.error(
                            f"Error registering LLM config {llm_id}: {e}", exc_info=True
                        )
                else:
                    logger.debug(f"LLM config {llm_id} already exists. Skipping.")

            # Add Agent Configs
            for (
                agent_name,
                agent_config,
            ) in parsed_config.agents.items():  # Changed agent_configs to agents
                if (
                    agent_name not in active_project_config.agents
                ):  # Changed agent_configs to agents
                    try:
                        logger.debug(f"Registering new agent: {agent_name}")
                        await self.register_agent(agent_config)
                    except ValueError as e:
                        logger.warning(f"Skipping agent {agent_name}: {e}")
                    except Exception as e:
                        logger.error(
                            f"Error registering agent {agent_name}: {e}", exc_info=True
                        )
                else:
                    logger.debug(f"Agent config {agent_name} already exists. Skipping.")

            # Add Simple Workflow Configs
            for (
                workflow_name,
                workflow_config,
            ) in (
                parsed_config.simple_workflows.items()
            ):  # Changed simple_workflow_configs to simple_workflows
                if (
                    workflow_name not in active_project_config.simple_workflows
                ):  # Changed simple_workflow_configs to simple_workflows
                    try:
                        logger.debug(
                            f"Registering new simple workflow: {workflow_name}"
                        )
                        await self.register_workflow(workflow_config)
                    except ValueError as e:
                        logger.warning(f"Skipping simple workflow {workflow_name}: {e}")
                    except Exception as e:
                        logger.error(
                            f"Error registering simple workflow {workflow_name}: {e}",
                            exc_info=True,
                        )
                else:
                    logger.debug(
                        f"Simple workflow config {workflow_name} already exists. Skipping."
                    )

            # Add Custom Workflow Configs
            for (
                custom_workflow_name,
                custom_workflow_config,
            ) in (
                parsed_config.custom_workflows.items()
            ):  # Changed custom_workflow_configs to custom_workflows
                if (
                    custom_workflow_name
                    not in active_project_config.custom_workflows  # Changed custom_workflow_configs to custom_workflows
                ):
                    try:
                        logger.debug(
                            f"Registering new custom workflow: {custom_workflow_name}"
                        )
                        await self.register_custom_workflow(custom_workflow_config)
                    except ValueError as e:
                        logger.warning(
                            f"Skipping custom workflow {custom_workflow_name}: {e}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error registering custom workflow {custom_workflow_name}: {e}",
                            exc_info=True,
                        )
                else:
                    logger.debug(
                        f"Custom workflow config {custom_workflow_name} already exists. Skipping."
                    )

            logger.info(
                f"Finished loading components from project: {parsed_config.name}"
            )

        except FileNotFoundError:
            # Already logged by parse_project_file, re-raise for API to handle
            raise
        except (RuntimeError, ValueError) as e:
            logger.error(
                f"Error loading components from project {project_config_path}: {e}",
                exc_info=True,
            )
            raise  # Re-raise for API to handle
        except Exception as e:
            logger.error(
                f"Unexpected error loading components from project {project_config_path}: {e}",
                exc_info=True,
            )
            raise  # Re-raise for API to handle
