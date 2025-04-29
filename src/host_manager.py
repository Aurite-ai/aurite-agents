"""
Host Manager for orchestrating MCPHost, Agents, and Workflows.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Any

# Assuming this file is in src/, use relative imports
from .config import load_host_config_from_json
from .host.host import MCPHost
from .host.models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    ClientConfig,
)  # Added ClientConfig
from src.prompt_validation.prompt_validation_helper import load_config

# Imports needed for execution methods
from .agents.agent import Agent
from .config import PROJECT_ROOT_DIR  # Import project root for path validation
import importlib
import inspect

logger = logging.getLogger(__name__)


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

        logger.info(f"HostManager initialized with config path: {self.config_path}")

    # --- Lifecycle Methods ---

    async def initialize(self):
        """
        Loads configurations, initializes the MCPHost, and prepares the manager.

        Raises:
            RuntimeError: If configuration loading or host initialization fails.
        """
        logger.info(f"Initializing HostManager with config: {self.config_path}...")
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
            logger.info("Configurations loaded successfully.")

            # 2. Instantiate MCPHost
            # Note: MCPHost still takes agent/workflow configs for its internal lookups
            self.host = MCPHost(
                config=host_config,
                agent_configs=self.agent_configs,
                workflow_configs=self.workflow_configs,
                # encryption_key could be passed from a secure source if needed
            )
            logger.info("MCPHost instance created.")

            # 3. Initialize MCPHost (connects to clients, etc.)
            await self.host.initialize()
            logger.info("MCPHost initialized successfully.")
            
            # Also load the prompt validation config
            await self.register_config_file("config/prompt_validation_config.json")
            logger.info("Prompt Validation Config loaded.")

            logger.info("HostManager initialization complete.")

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
        logger.info(
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
        logger.info(f"Attempting to dynamically register agent: {agent_config.name}")
        if not self.host:
            logger.error("HostManager is not initialized. Cannot register agent.")
            raise ValueError("HostManager is not initialized.")

        if agent_config.name in self.agent_configs:
            logger.error(f"Agent name '{agent_config.name}' already registered.")
            raise ValueError(f"Agent name '{agent_config.name}' already registered.")

        # Validate client_ids exist
        if agent_config.client_ids:
            # Accessing host._clients directly might be fragile
            for client_id in agent_config.client_ids:
                if client_id not in self.host._clients:
                    logger.error(
                        f"Client ID '{client_id}' specified in agent '{agent_config.name}' not found."
                    )
                    raise ValueError(
                        f"Client ID '{client_id}' not found for agent '{agent_config.name}'."
                    )

        # Add the agent config
        self.agent_configs[agent_config.name] = agent_config
        logger.info(f"Agent '{agent_config.name}' registered successfully.")

    async def register_workflow(self, workflow_config: "WorkflowConfig"):
        """
        Dynamically registers a new simple Workflow configuration.

        Args:
            workflow_config: The configuration for the workflow to register.

        Raises:
            ValueError: If the HostManager is not initialized, the workflow name already exists,
                        or if any agent name in the steps is not found.
        """
        logger.info(
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

        # Add the workflow config
        self.workflow_configs[workflow_config.name] = workflow_config
        logger.info(f"Workflow '{workflow_config.name}' registered successfully.")

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
        logger.info(
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

        # Add the workflow config
        self.custom_workflow_configs[custom_workflow_config.name] = (
            custom_workflow_config
        )
        logger.info(
            f"Custom Workflow '{custom_workflow_config.name}' registered successfully."
        )

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
        logger.info(
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

        registered_counts = {
            "clients": 0,
            "agents": 0,
            "workflows": 0,
            "custom_workflows": 0,
        }
        skipped_counts = {
            "clients": 0,
            "agents": 0,
            "workflows": 0,
            "custom_workflows": 0,
        }
        error_messages = []

        try:
            # 1. Load all configurations from the specified file
            (
                host_config,
                agent_configs_dict,
                workflow_configs_dict,
                custom_workflow_configs_dict,
            ) = load_host_config_from_json(file_path)
            logger.info(f"Successfully loaded configurations from {file_path}.")

            # 2. Register Clients
            logger.info(f"Registering {len(host_config.clients)} clients...")
            for client_config in host_config.clients:
                try:
                    await self.host.register_client(client_config)
                    registered_counts["clients"] += 1
                    logger.debug(
                        f"Successfully registered client: {client_config.client_id}"
                    )
                except ValueError as e:  # Catch duplicate client IDs
                    logger.warning(
                        f"Skipping client registration for '{client_config.client_id}': {e}"
                    )
                    skipped_counts["clients"] += 1
                except Exception as e:
                    err_msg = (
                        f"Failed to register client '{client_config.client_id}': {e}"
                    )
                    logger.error(err_msg, exc_info=True)
                    error_messages.append(err_msg)
                    skipped_counts["clients"] += 1  # Count as skipped due to error

            # 3. Register Agents
            logger.info(f"Registering {len(agent_configs_dict)} agents...")
            for agent_name, agent_config in agent_configs_dict.items():
                try:
                    await self.register_agent(agent_config)
                    registered_counts["agents"] += 1
                    logger.debug(f"Successfully registered agent: {agent_name}")
                except ValueError as e:  # Catch duplicates or invalid client IDs
                    logger.warning(
                        f"Skipping agent registration for '{agent_name}': {e}"
                    )
                    skipped_counts["agents"] += 1
                except Exception as e:  # Catch unexpected errors
                    err_msg = f"Failed to register agent '{agent_name}': {e}"
                    logger.error(err_msg, exc_info=True)
                    error_messages.append(err_msg)
                    skipped_counts["agents"] += 1

            # 4. Validate and Register Workflows
            logger.info(
                f"Validating and registering {len(workflow_configs_dict)} workflows..."
            )
            # Create a combined view of existing and newly loaded agents for validation
            available_agent_names = set(self.agent_configs.keys()) | set(
                agent_configs_dict.keys()
            )
            valid_workflows_to_register = {}

            for workflow_name, workflow_config in workflow_configs_dict.items():
                is_valid = True
                if workflow_config.steps:
                    for step_agent_name in workflow_config.steps:
                        if step_agent_name not in available_agent_names:
                            err_msg = f"Workflow '{workflow_name}' references unknown agent '{step_agent_name}'. Agent not found in existing or newly loaded configurations."
                            logger.error(err_msg)
                            error_messages.append(err_msg)
                            skipped_counts["workflows"] += 1
                            is_valid = False
                            break  # No need to check other steps for this workflow
                if is_valid:
                    valid_workflows_to_register[workflow_name] = workflow_config

            # Now register only the valid workflows
            for workflow_name, workflow_config in valid_workflows_to_register.items():
                try:
                    # Use the existing register_workflow which checks for duplicates in self.workflow_configs
                    await self.register_workflow(workflow_config)
                    registered_counts["workflows"] += 1
                    logger.debug(f"Successfully registered workflow: {workflow_name}")
                except ValueError as e:  # Catch duplicates or invalid agent names
                    logger.warning(
                        f"Skipping workflow registration for '{workflow_name}': {e}"
                    )
                    skipped_counts["workflows"] += 1
                except Exception as e:  # Catch unexpected errors
                    err_msg = f"Failed to register workflow '{workflow_name}': {e}"
                    logger.error(err_msg, exc_info=True)
                    error_messages.append(err_msg)
                    skipped_counts["workflows"] += 1

            # 5. Register Custom Workflows
            logger.info(
                f"Registering {len(custom_workflow_configs_dict)} custom workflows..."
            )
            for cwf_name, cwf_config in custom_workflow_configs_dict.items():
                try:
                    await self.register_custom_workflow(cwf_config)
                    registered_counts["custom_workflows"] += 1
                    logger.debug(f"Successfully registered custom workflow: {cwf_name}")
                except ValueError as e:  # Catch duplicates or invalid paths
                    logger.warning(
                        f"Skipping custom workflow registration for '{cwf_name}': {e}"
                    )
                    skipped_counts["custom_workflows"] += 1
                except Exception as e:  # Catch unexpected errors
                    err_msg = f"Failed to register custom workflow '{cwf_name}': {e}"
                    logger.error(err_msg, exc_info=True)
                    error_messages.append(err_msg)
                    skipped_counts["custom_workflows"] += 1

            # Log summary
            summary_msg = (
                f"Finished processing config file '{file_path}'. "
                f"Registered: {registered_counts}. Skipped: {skipped_counts}."
            )
            if error_messages:
                summary_msg += (
                    f" Encountered {len(error_messages)} errors during registration."
                )
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

    async def execute_agent(
        self, agent_name: str, user_message: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a configured agent by name.

        Args:
            agent_name: The name of the agent to execute (must match a key in loaded agent_configs).
            user_message: The user's input message for the agent.

        Returns:
            A dictionary containing the agent's execution result (e.g., conversation, final response).

        Raises:
            ValueError: If the HostManager is not initialized (host is None).
            KeyError: If the specified agent_name is not found in the configuration.
            Exception: Propagates exceptions from Agent instantiation or execution.
        """
        logger.info(f"Executing agent: {agent_name}")

        if not self.host:
            logger.error("HostManager is not initialized. Cannot execute agent.")
            raise ValueError("HostManager is not initialized.")

        try:
            # 1. Retrieve AgentConfig
            agent_config = self.agent_configs[agent_name]
            logger.debug(f"Found AgentConfig for '{agent_name}'")

            # 2. Instantiate Agent
            # Agent initialization might raise errors (e.g., missing API key)
            agent = Agent(config=agent_config)
            logger.debug(f"Instantiated Agent '{agent_name}'")

            # 3. Determine if prompt evaluation should happen
            if agent_config.evaluation:
                logger.debug(f"Using evaluation for '{agent_name}'")
                
                # determine if path to config or simple prompt. fill in default values if simple prompt
                testing_config_path = PROJECT_ROOT_DIR / f"config/testing/{agent_config.evaluation}"
                if os.path.exists(testing_config_path):
                    # valid path, run as normal
                    # overwrite input in config with actual user input
                    testing_config = load_config(testing_config_path)
                    testing_config.user_input = user_message
                    
                    workflow_result = await self.execute_custom_workflow(
                        workflow_name="Prompt Validation Workflow", 
                        initial_input={
                            "validation_config": testing_config
                        }
                    )
                    result = workflow_result.get("agent_responses")[-1]
                else:
                    # invalid path, it is system prompt
                    workflow_result = await self.execute_custom_workflow(
                        workflow_name="Prompt Validation Workflow", 
                        initial_input={
                            "testing_prompt": agent_config.evaluation,
                            "user_input": user_message,
                            "agent_name": agent_name
                        }
                    )
                    result = workflow_result.get("agent_responses")[-1]
                
            else:
                # 4. Execute the agent as normal
                if system_prompt:
                    logger.debug(f"Using system prompt for '{agent_name}': {system_prompt}")
                    result = await agent.execute_agent(
                        user_message=user_message,
                        host_instance=self.host,
                        system_prompt=system_prompt,
                    )
                else:
                    result = await agent.execute_agent(
                        user_message=user_message,
                        host_instance=self.host,
                    )
            logger.info(f"Agent '{agent_name}' execution finished.")
            return result

        except KeyError:
            logger.error(f"Agent configuration not found for name: {agent_name}")
            raise  # Re-raise KeyError for the caller (e.g., API endpoint) to handle
        except Exception as e:
            logger.error(
                f"Error during agent '{agent_name}' execution in HostManager: {e}",
                exc_info=True,
            )
            # Re-raise other exceptions (from Agent init or execute)
            raise

    async def execute_workflow(
        self, workflow_name: str, initial_user_message: str
    ) -> Dict[str, Any]:
        """
        Executes a configured simple workflow (sequence of agents) by name.

        Args:
            workflow_name: The name of the workflow to execute.
            initial_user_message: The initial input message for the first agent in the sequence.

        Returns:
            A dictionary containing the final status, the final message from the last agent,
            and any error message encountered.

        Raises:
            ValueError: If the HostManager is not initialized (host is None).
            KeyError: If the specified workflow_name or an agent within the workflow is not found.
            Exception: Propagates exceptions from underlying agent executions.
        """
        logger.info(f"Executing simple workflow: {workflow_name}")

        if not self.host:
            logger.error("HostManager is not initialized. Cannot execute workflow.")
            raise ValueError("HostManager is not initialized.")

        current_message = initial_user_message
        final_status = "failed"  # Default status
        error_message = None

        try:
            # 1. Retrieve WorkflowConfig
            workflow_config = self.workflow_configs[workflow_name]
            logger.debug(
                f"Found WorkflowConfig for '{workflow_name}' with steps: {workflow_config.steps}"
            )

            if not workflow_config.steps:
                logger.warning(f"Workflow '{workflow_name}' has no steps to execute.")
                return {
                    "workflow_name": workflow_name,
                    "status": "completed_empty",
                    "final_message": current_message,
                    "error": None,
                }

            # 2. Loop through steps (agents)
            for i, agent_name in enumerate(workflow_config.steps):
                step_num = i + 1
                logger.info(
                    f"Executing workflow '{workflow_name}' step {step_num}: Agent '{agent_name}'"
                )

                # Call self.execute_agent for the current step
                # This already handles agent config lookup, instantiation, and execution
                # It will raise KeyError if agent_name is not found in self.agent_configs
                try:
                    result = await self.execute_agent(
                        agent_name=agent_name, user_message=current_message
                    )

                    # Error Handling for Agent Execution within the workflow
                    if result.get("error"):
                        error_message = f"Agent '{agent_name}' (step {step_num}) failed: {result['error']}"
                        logger.error(error_message)
                        break  # Stop workflow execution

                    if (
                        not result.get("final_response")
                        or not result["final_response"].content
                    ):
                        error_message = f"Agent '{agent_name}' (step {step_num}) did not return a final response."
                        logger.error(error_message)
                        break  # Stop workflow execution

                    # Output Extraction (Basic: first text block)
                    try:
                        # Find the first text block in the content list
                        text_content = next(
                            (
                                block.text
                                for block in result["final_response"].content
                                if block.type == "text"
                            ),
                            None,
                        )
                        if text_content is None:
                            error_message = f"Agent '{agent_name}' (step {step_num}) response content has no text block."
                            logger.error(error_message)
                            break  # Stop workflow execution
                        current_message = (
                            text_content  # Update message for the next step
                        )
                        logger.debug(
                            f"Step {step_num}: Output message: '{current_message[:100]}...'"
                        )
                    except (AttributeError, IndexError, TypeError) as e:
                        error_message = f"Error extracting text from agent '{agent_name}' (step {step_num}) response: {e}"
                        logger.error(error_message, exc_info=True)
                        break  # Stop workflow execution

                except KeyError:
                    # This occurs if self.execute_agent raises KeyError for the agent_name
                    error_message = f"Configuration error: Agent '{agent_name}' (step {step_num}) not found."
                    logger.error(error_message)
                    # Re-raise here so the outer try/except catches it for consistent workflow failure reporting
                    raise
                except Exception as agent_exec_e:
                    # Catch other unexpected errors from self.execute_agent
                    error_message = f"Unexpected error during agent '{agent_name}' (step {step_num}) execution: {agent_exec_e}"
                    logger.error(error_message, exc_info=True)
                    break  # Stop workflow execution

            # 3. Determine final status
            if error_message is None:
                final_status = "completed"
                logger.info(f"Workflow '{workflow_name}' completed successfully.")

        except KeyError:
            # Catches KeyError if workflow_name itself is not found, or if re-raised from agent lookup
            logger.error(
                f"Workflow configuration or agent within workflow '{workflow_name}' not found."
            )
            # Re-raise for the caller (API endpoint) to handle as 404 or 500
            raise
        except Exception as e:
            # Catch any other unexpected errors during workflow orchestration
            logger.error(
                f"Unexpected error during workflow '{workflow_name}' execution: {e}",
                exc_info=True,
            )
            error_message = (
                error_message
                or f"Internal server error during workflow execution: {str(e)}"
            )
            # Don't re-raise here, return the failure status in the dictionary

        # 4. Return final result
        return {
            "workflow_name": workflow_name,
            "status": final_status,
            "final_message": current_message if final_status == "completed" else None,
            "error": error_message,
        }

    async def execute_custom_workflow(
        self, workflow_name: str, initial_input: Any
    ) -> Any:
        """
        Executes a configured custom Python workflow by name.

        Args:
            workflow_name: The name of the custom workflow to execute.
            initial_input: The input data to pass to the workflow's execute method.

        Returns:
            The result returned by the custom workflow's execute_workflow method.

        Raises:
            ValueError: If the HostManager is not initialized (host is None).
            KeyError: If the workflow_name is not found in the configuration.
            FileNotFoundError: If the configured module path does not exist.
            PermissionError: If the module path is outside the project directory.
            ImportError: If the module cannot be imported.
            AttributeError: If the specified class or 'execute_workflow' method is not found.
            TypeError: If the 'execute_workflow' method is not async or class instantiation fails.
            RuntimeError: Wraps exceptions raised during the workflow's execution.
        """
        logger.info(f"Executing custom workflow: {workflow_name}")

        if not self.host:
            logger.error(
                "HostManager is not initialized. Cannot execute custom workflow."
            )
            raise ValueError("HostManager is not initialized.")

        try:
            # 1. Get Config
            config = self.custom_workflow_configs[workflow_name]
            module_path = config.module_path
            class_name = config.class_name
            logger.debug(
                f"Found CustomWorkflowConfig for '{workflow_name}': path={module_path}, class={class_name}"
            )

            # 2. Security Check (Basic): Ensure path is within project
            # Use PROJECT_ROOT_DIR imported from config
            if not str(module_path.resolve()).startswith(
                str(PROJECT_ROOT_DIR.resolve())
            ):
                logger.error(
                    f"Custom workflow path '{module_path}' is outside the project directory {PROJECT_ROOT_DIR}. Aborting."
                )
                raise PermissionError(
                    "Custom workflow path is outside the project directory."
                )

            if not module_path.exists():
                logger.error(f"Custom workflow module file not found: {module_path}")
                raise FileNotFoundError(
                    f"Custom workflow module file not found: {module_path}"
                )

            # 3. Dynamic Import
            spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
            if spec is None or spec.loader is None:
                # Raise ImportError directly if spec creation fails
                raise ImportError(f"Could not create module spec for {module_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.debug(f"Dynamically imported module: {module_path}")

            # 4. Get Class
            WorkflowClass = getattr(module, class_name, None)
            if WorkflowClass is None:
                logger.error(f"Class '{class_name}' not found in module {module_path}")
                raise AttributeError(
                    f"Class '{class_name}' not found in module {module_path}"
                )

            # 5. Instantiate
            try:
                workflow_instance = WorkflowClass()
                logger.debug(f"Instantiated workflow class '{class_name}'")
            except Exception as init_err:
                logger.error(
                    f"Error instantiating workflow class '{class_name}' from {module_path}: {init_err}",
                    exc_info=True,
                )
                # Use TypeError consistent with original manager, though RuntimeError might also fit
                raise TypeError(
                    f"Failed to instantiate workflow class '{class_name}': {init_err}"
                ) from init_err

            # 6. Check for execute_workflow method
            execute_method_name = "execute_workflow"
            if not hasattr(workflow_instance, execute_method_name) or not callable(
                getattr(workflow_instance, execute_method_name)
            ):
                logger.error(
                    f"Method '{execute_method_name}' not found or not callable in class '{class_name}' from {module_path}"
                )
                raise AttributeError(
                    f"Method '{execute_method_name}' not found or not callable in class '{class_name}'"
                )

            execute_method = getattr(workflow_instance, execute_method_name)

            # 7. Execute (check if async)
            if not inspect.iscoroutinefunction(execute_method):
                logger.error(
                    f"Method '{execute_method_name}' in class '{class_name}' from {module_path} must be async."
                )
                raise TypeError(f"Method '{execute_method_name}' must be async.")

            logger.debug(
                f"Calling '{execute_method_name}' on instance of '{class_name}'"
            )
            result = await execute_method(
                initial_input=initial_input, host_instance=self.host
            )

            logger.info(
                f"Custom workflow '{workflow_name}' execution finished successfully."
            )
            return result

        except (
            KeyError,
            FileNotFoundError,
            ImportError,
            AttributeError,
            PermissionError,
            TypeError,
        ) as e:
            # Catch specific setup/loading errors and re-raise
            logger.error(
                f"Error setting up or loading custom workflow '{workflow_name}': {e}",
                exc_info=True,
            )
            raise e
        except Exception as e:
            # Catch errors *during* the workflow's own execution
            logger.error(
                f"Exception raised within custom workflow '{workflow_name}': {e}",
                exc_info=True,
            )
            # Wrap internal workflow errors in a RuntimeError
            raise RuntimeError(
                f"Exception during custom workflow '{workflow_name}' execution: {e}"
            ) from e
