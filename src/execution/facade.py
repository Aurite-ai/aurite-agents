# src/execution/facade.py
"""
Provides a unified facade for executing Agents, Simple Workflows, and Custom Workflows.
"""

import logging
from typing import (
    Any,
    Dict,
    Optional,
    TYPE_CHECKING,
    Callable,
    Coroutine,
    List,
    cast,
    AsyncGenerator,  # Added AsyncGenerator
)

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from ..host.host import MCPHost  # Needed for passing to executors/workflows
    from ..agents.agent import Agent  # Keep type hint here
    from ..workflows.simple_workflow import (
        SimpleWorkflowExecutor,
    )  # Import for type hint
    from ..workflows.custom_workflow import CustomWorkflowExecutor
    from ..storage.db_manager import StorageManager
    from ..config.config_models import AgentConfig, ProjectConfig # LLMConfig will be imported outside TYPE_CHECKING
    from ..llm.base_client import BaseLLM
    from ..llm.providers.anthropic_client import AnthropicLLM

# Actual runtime imports
from ..config.config_models import LLMConfig # Ensure LLMConfig is imported for direct use at runtime

# Import Agent at runtime for instantiation
from ..agents.agent import Agent

# Import AgentExecutionResult for type hinting the result
from ..agents.agent_models import AgentExecutionResult

# Import MessageParam for constructing initial messages
from anthropic.types import MessageParam

# Import SimpleWorkflowExecutor at runtime
from ..workflows.simple_workflow import SimpleWorkflowExecutor

# Import CustomWorkflowExecutor at runtime
from ..workflows.custom_workflow import CustomWorkflowExecutor

# Import default LLM client for SimpleWorkflowExecutor instantiation
from ..llm.providers.anthropic_client import (
    AnthropicLLM,
)

logger = logging.getLogger(__name__)


class ExecutionFacade:
    """
    A facade that simplifies the execution of different component types
    (Agents, Simple Workflows, Custom Workflows) managed by the HostManager.

    It uses the appropriate executor for each component type and passes
    the StorageManager if available.
    """

    def __init__(
        self,
        host_instance: "MCPHost",
        current_project: "ProjectConfig",  # Add ProjectConfig type hint
        storage_manager: Optional["StorageManager"] = None,
    ):
        """
        Initializes the ExecutionFacade.

        Args:
            host_instance: The initialized and active MCPHost instance.
            current_project: The currently loaded and resolved ProjectConfig object.
            storage_manager: An optional initialized StorageManager instance for persistence.
        """
        if not host_instance:
            raise ValueError("MCPHost instance is required for ExecutionFacade.")
        if not current_project:  # Check current_project directly
            raise ValueError("Current ProjectConfig is required for ExecutionFacade.")

        self._host = host_instance
        self._current_project = current_project
        self._storage_manager = storage_manager
        self._llm_client_cache: Dict[str, BaseLLM] = {} # LLM Client Cache
        self._is_shut_down = False # Flag to prevent double shutdown
        logger.debug(
            f"ExecutionFacade initialized with project '{current_project.name}' (StorageManager {'present' if storage_manager else 'absent'})."
        )

    # --- Private LLM Client Factory ---

    def _create_llm_client(self, llm_config: "LLMConfig") -> "BaseLLM":
        """
        Factory method to create an LLM client instance based on LLMConfig.
        Handles provider selection and API key resolution (basic for now).
        """
        provider = llm_config.provider.lower()
        model_name = llm_config.model_name or "claude-3-haiku-20240307" # Default if not specified in config

        logger.debug(f"Creating LLM client for provider '{provider}', model '{model_name}' (ID: {llm_config.llm_id})")

        if provider == "anthropic":
            # API key resolution could be enhanced here (e.g., check env vars specified in config)
            # For now, relies on AnthropicLLM's internal check for ANTHROPIC_API_KEY
            try:
                return AnthropicLLM(
                    model_name=model_name,
                    temperature=llm_config.temperature, # Pass None if not set, client handles default
                    max_tokens=llm_config.max_tokens,   # Pass None if not set, client handles default
                    system_prompt=llm_config.default_system_prompt # Pass None if not set, client handles default
                    # api_key=resolved_api_key # Example if key resolution happened here
                )
            except Exception as e:
                logger.error(f"Failed to instantiate AnthropicLLM for config '{llm_config.llm_id}': {e}", exc_info=True)
                raise ValueError(f"Failed to create Anthropic client: {e}") from e
        # Add other providers here
        # elif provider == "openai":
        #     # ... implementation ...
        #     pass
        else:
            logger.error(f"Unsupported LLM provider specified in LLMConfig '{llm_config.llm_id}': {provider}")
            raise NotImplementedError(f"LLM provider '{provider}' is not currently supported.")

    async def aclose(self):
        """Closes all cached LLM clients."""
        if self._is_shut_down:
            logger.debug("ExecutionFacade.aclose called but already shut down.")
            return
        logger.debug("ExecutionFacade.aclose() called. Closing cached LLM clients...")
        for llm_id, client_instance in self._llm_client_cache.items():
            try:
                if hasattr(client_instance, "aclose") and callable(
                    getattr(client_instance, "aclose")
                ):
                    logger.debug(f"Closing LLM client for ID: {llm_id}")
                    await client_instance.aclose()
            except Exception as e:
                logger.error(
                    f"Error closing LLM client for ID '{llm_id}': {e}", exc_info=True
                )
        self._llm_client_cache.clear()
        self._is_shut_down = True
        logger.debug("ExecutionFacade LLM client cache cleared and facade marked as shut down.")

    # --- Private Execution Helper ---

    async def _execute_component(
        self,
        component_type: str,
        component_name: str,
        config_lookup: Callable[[str], Any],
        executor_setup: Callable[[Any], Any],
        execution_func: Callable[..., Coroutine[Any, Any, Any]],
        error_structure_factory: Callable[[str, str], Dict[str, Any]],
        **execution_kwargs: Any,
    ) -> Any:
        """
        Generic helper to execute a component (Agent, Workflow).

        Handles config lookup, instantiation, execution, and error handling.

        Args:
            component_type: String description (e.g., "Agent", "Simple Workflow").
            component_name: The name of the component instance to execute.
            config_lookup: Callable that takes component_name and returns its config.
            executor_setup: Callable that takes the config and returns the executor/agent instance.
            execution_func: The async execution method of the executor/agent instance.
            error_structure_factory: Callable that takes component_name and error message
                                     and returns the standardized error dictionary.
            **execution_kwargs: Arguments to pass to the execution_func.

        Returns:
            The result of the execution or a standardized error dictionary.
        """
        logger.info(
            f"Facade: Received request to run {component_type} '{component_name}'"
        )

        # 1. Get Configuration
        try:
            config = config_lookup(component_name)
            logger.debug(  # Already DEBUG
                f"Facade: Found {component_type}Config for '{component_name}'"
            )
        except KeyError:
            error_msg = (
                f"Configuration error: {component_type} '{component_name}' not found."
            )
            logger.error(f"Facade: {error_msg}")
            # Call factory with positional arguments
            return error_structure_factory(component_name, error_msg)
        except Exception as config_err:
            # Catch unexpected errors during config lookup
            error_msg = f"Unexpected error retrieving config for {component_type} '{component_name}': {config_err}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return error_structure_factory(component_name, error_msg)

        # Add explicit check if config lookup succeeded but returned None
        if config is None:
            error_msg = (
                f"{component_type} '{component_name}' not found (lookup returned None)."
            )
            logger.error(f"Facade: {error_msg}")
            # Call factory with positional arguments
            return error_structure_factory(component_name, error_msg)

        # 2. Instantiate Executor/Agent
        try:
            instance = executor_setup(config)
            logger.debug(  # Already DEBUG
                f"Facade: Instantiated {component_type} '{component_name}'"
            )
        except Exception as setup_err:
            error_msg = f"Initialization error for {component_type} '{component_name}': {setup_err}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            # Call factory with positional arguments
            return error_structure_factory(component_name, error_msg)

        # 3. Execute
        try:
            result = await execution_func(instance, **execution_kwargs)
            logger.info(  # Keep final success as INFO
                f"Facade: {component_type} '{component_name}' execution finished."
            )
            return result
        except (
            KeyError,
            FileNotFoundError,
            AttributeError,
            ImportError,
            PermissionError,
            TypeError,
            RuntimeError,
        ) as exec_err:
            # Catch specific errors known to occur during execution/setup within executors
            error_msg = f"Runtime error during {component_type} '{component_name}' execution: {type(exec_err).__name__}: {exec_err}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            # Re-raise these specific errors so API handlers can catch them
            raise exec_err
        except Exception as e:
            # Catch other unexpected errors during execution
            error_msg = f"Unexpected runtime error during {component_type} '{component_name}' execution: {e}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            # Return standardized error structure for generic exceptions, passing positional args
            return error_structure_factory(component_name, error_msg)

    # --- Public Execution Methods ---

    async def stream_agent_run(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[
            str
        ] = None,  # For history, though less critical for pure stream
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes a configured agent by name, streaming events.
        Handles history loading for context but primarily focuses on streaming the current interaction.
        """
        logger.info(f"Facade: Received request to STREAM agent '{agent_name}'")
        agent_config: Optional[AgentConfig] = None
        llm_client_instance: Optional[BaseLLM] = None
        llm_config_for_override_obj: Optional[LLMConfig] = None

        try:
            # 1. Get Agent Configuration (same as non-streaming)
            if not self._current_project.agents:
                raise KeyError(
                    f"Agent configurations not found for agent '{agent_name}'."
                )
            agent_config = self._current_project.agents.get(agent_name)
            if not agent_config:
                raise KeyError(f"Agent configuration '{agent_name}' not found.")

            # 2. Resolve LLM Parameters & Instantiate LLM Client (same as non-streaming)
            effective_model_name: Optional[str] = None
            effective_temperature: Optional[float] = None
            effective_max_tokens: Optional[int] = None
            effective_system_prompt_for_llm_client: Optional[str] = None

            if agent_config.llm_config_id:
                if self._current_project.llms:
                    llm_config_for_override_obj = self._current_project.llms.get(
                        agent_config.llm_config_id
                    )
                if llm_config_for_override_obj:
                    effective_model_name = llm_config_for_override_obj.model_name
                    effective_temperature = llm_config_for_override_obj.temperature
                    effective_max_tokens = llm_config_for_override_obj.max_tokens
                    effective_system_prompt_for_llm_client = (
                        llm_config_for_override_obj.default_system_prompt
                    )
                else:
                    logger.warning(
                        f"LLMConfig ID '{agent_config.llm_config_id}' for agent '{agent_name}' not found."
                    )

            if agent_config.model is not None:
                effective_model_name = agent_config.model
            if agent_config.temperature is not None:
                effective_temperature = agent_config.temperature
            if agent_config.max_tokens is not None:
                effective_max_tokens = agent_config.max_tokens
            if agent_config.system_prompt is not None:
                effective_system_prompt_for_llm_client = agent_config.system_prompt
            if not effective_model_name:
                effective_model_name = "claude-3-haiku-20240307"  # Fallback

            llm_client_instance = AnthropicLLM(  # Assuming Anthropic for now, refactor for provider pattern later
                model_name=effective_model_name,
                temperature=effective_temperature,
                max_tokens=effective_max_tokens,
                system_prompt=effective_system_prompt_for_llm_client,
            )
            logger.debug(f"Facade: Resolved LLM parameters for streaming agent '{agent_name}'.")

            # 2.b Get/Create LLM Client Instance using Cache
            llm_client_instance: Optional[BaseLLM] = None
            cache_key: Optional[str] = None

            if llm_config_for_override_obj:
                cache_key = llm_config_for_override_obj.llm_id
                llm_client_instance = self._llm_client_cache.get(cache_key)
                if not llm_client_instance:
                    logger.debug(f"Facade: LLM client for '{cache_key}' not in cache. Creating...")
                    llm_client_instance = self._create_llm_client(llm_config_for_override_obj)
                    self._llm_client_cache[cache_key] = llm_client_instance
                    logger.debug(f"Facade: Cached LLM client for '{cache_key}'.")
                else:
                    logger.debug(f"Facade: Reusing cached LLM client for '{cache_key}'.")
            else:
                # No LLMConfig ID - create temporary config and non-cached client
                logger.warning(f"Facade: Agent '{agent_name}' running without a specific LLMConfig ID. Creating temporary, non-cached client.")
                temp_llm_config = LLMConfig(
                    llm_id=f"temp_{agent_name}", # Temporary ID
                    provider="anthropic", # Assuming default provider
                    model_name=effective_model_name,
                    temperature=effective_temperature,
                    max_tokens=effective_max_tokens,
                    default_system_prompt=effective_system_prompt_for_llm_client
                )
                llm_client_instance = self._create_llm_client(temp_llm_config) # Do not cache

            if not llm_client_instance:
                 # This should ideally not happen if _create_llm_client raises errors
                 raise RuntimeError(f"Failed to obtain LLM client instance for agent '{agent_name}'.")

            # 3. Prepare Initial Messages (same as non-streaming, for context)
            initial_messages_for_agent: List[MessageParam] = []
            if agent_config.include_history and self._storage_manager and session_id:
                try:
                    loaded_history = self._storage_manager.load_history(
                        agent_name, session_id
                    )
                    if loaded_history:
                        initial_messages_for_agent.extend(
                            [cast(MessageParam, item) for item in loaded_history]
                        )
                except Exception as e:
                    logger.error(
                        f"Facade: Failed to load history for streaming agent '{agent_name}': {e}",
                        exc_info=True,
                    )

            initial_messages_for_agent.append(
                {"role": "user", "content": [{"type": "text", "text": user_message}]}
            )

            # 4. Instantiate Agent
            agent_instance = Agent(
                config=agent_config,
                llm_client=llm_client_instance,
                host_instance=self._host,
                initial_messages=initial_messages_for_agent,
                system_prompt_override=system_prompt,  # User-provided override for this run
                llm_config_for_override=llm_config_for_override_obj,
            )
            logger.debug(
                f"Facade: Instantiated Agent for streaming run of '{agent_name}'."
            )

            # 5. Stream Conversation
            logger.info(f"Facade: Streaming conversation for Agent '{agent_name}'...")
            async for event in agent_instance.stream_conversation():
                yield event

            # Note: History saving for streamed conversations needs careful consideration.
            # It might happen after the stream ends, based on accumulated events,
            # or be handled differently. For now, this method focuses on yielding the stream.

        except Exception as e:
            error_msg = f"Error during streaming setup or execution for Agent '{agent_name}': {type(e).__name__}: {str(e)}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            yield {
                "event_type": "error",
                "data": {"message": error_msg, "agent_name": agent_name},
            }
            # Ensure the generator stops
            return

    async def run_agent(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[
        str, Any
    ]:  # Return type is Dict for API compatibility, AgentExecutionResult internally
        """
        Executes a configured agent by name, handling history loading/saving if configured.
        """
        agent_config: Optional[AgentConfig] = None
        # agent_instance: Optional[Agent] = None # Will be created after LLM client
        # llm_client_instance: Optional[BaseLLM] = None # Will be created after param resolution

        def error_factory(name: str, msg: str) -> Dict[str, Any]:
            # Return structure matching AgentExecutionResult fields for consistency
            return AgentExecutionResult(
                conversation=[],
                final_response=None,
                tool_uses_in_final_turn=[],
                error=msg,
            ).model_dump(mode="json")  # Return as dict

        try:
            # 1. Get Agent Configuration
            if (
                not self._current_project.agents  # Changed agent_configs to agents
            ):  # Should not happen if ProjectConfig is valid
                raise KeyError(
                    f"Agent configurations not found in current project for agent '{agent_name}'."
                )
            agent_config = self._current_project.agents.get(
                agent_name
            )  # Changed agent_configs to agents
            if not agent_config:
                raise KeyError(
                    f"Agent configuration '{agent_name}' not found in current project."
                )
            logger.debug(
                f"Facade: Found AgentConfig for '{agent_name}' in project '{self._current_project.name}'."
            )

            # 2. Resolve LLM Parameters
            effective_model_name: Optional[str] = None
            effective_temperature: Optional[float] = None
            effective_max_tokens: Optional[int] = None
            effective_system_prompt: Optional[str] = (
                None  # This will be for the LLM client itself
            )
            llm_config_for_override_obj: Optional[LLMConfig] = (
                None  # For passing to Agent constructor
            )

            # 2.a. LLMConfig Lookup (Base values)
            if agent_config.llm_config_id:
                if not self._current_project.llms:  # Changed llm_configs to llms
                    logger.warning(
                        f"LLM configurations not found in current project for agent '{agent_name}'."
                    )
                else:
                    llm_config_for_override_obj = (
                        self._current_project.llms.get(  # Changed llm_configs to llms
                            agent_config.llm_config_id
                        )
                    )  # Store the object
                if llm_config_for_override_obj:
                    logger.debug(
                        f"Facade: Applying base LLMConfig '{agent_config.llm_config_id}' for agent '{agent_name}'."
                    )
                    # These values are now primarily for the LLM client's direct instantiation,
                    # but the llm_config_for_override_obj itself will be passed to the Agent,
                    # which then passes it to the LLM client's create_message method.
                    effective_model_name = llm_config_for_override_obj.model_name
                    effective_temperature = llm_config_for_override_obj.temperature
                    effective_max_tokens = llm_config_for_override_obj.max_tokens
                    effective_system_prompt = (
                        llm_config_for_override_obj.default_system_prompt
                    )
                else:
                    logger.warning(
                        f"Facade: LLMConfig ID '{agent_config.llm_config_id}' specified for agent '{agent_name}' not found. "
                        "Proceeding with AgentConfig-specific LLM parameters or defaults for LLM client instantiation."
                    )
                    # llm_config_for_override_obj remains None

            # 2.b. AgentConfig Overrides (Agent-specific values override LLMConfig for LLM client instantiation)
            # The llm_config_override_obj is for the create_message call.
            # The LLM client itself is initialized with the most specific defaults available.
            if agent_config.model is not None:
                effective_model_name = agent_config.model
                logger.debug(
                    f"Facade: AgentConfig overrides model_name to '{effective_model_name}'."
                )
            if agent_config.temperature is not None:
                effective_temperature = agent_config.temperature
                logger.debug(
                    f"Facade: AgentConfig overrides temperature to '{effective_temperature}'."
                )
            if agent_config.max_tokens is not None:
                effective_max_tokens = agent_config.max_tokens
                logger.debug(
                    f"Facade: AgentConfig overrides max_tokens to '{effective_max_tokens}'."
                )

            # System prompt resolution:
            # 1. `system_prompt` argument to `run_agent` (highest precedence for this specific run)
            # 2. `agent_config.system_prompt` (agent's own specific default)
            # 3. `effective_system_prompt` from `LLMConfig` (if `llm_config_id` was used)
            # 4. Fallback to LLM client's internal default (e.g., "You are a helpful assistant.")
            # The `Agent` class itself also has a final fallback if its `system_prompt` argument is None.
            # For the LLM client instantiation, we prioritize agent_config.system_prompt over llm_config.default_system_prompt
            # The `system_prompt` argument to `run_agent` is passed directly to `agent.execute_agent`, which handles it.
            # So, for `effective_system_prompt` for the LLM client, we use agent_config's if available, else LLMConfig's.
            if agent_config.system_prompt is not None:
                effective_system_prompt_for_llm_client = agent_config.system_prompt # Use agent's default for LLM client init
                logger.debug(
                    "Facade: AgentConfig provides default system prompt for LLM client instantiation."
                )

            # Ensure a model name is available for the case where no LLMConfig ID is used
            # and agent_config.model is also None. _create_llm_client handles internal default.
            if not effective_model_name and not llm_config_for_override_obj:
                logger.warning(
                    f"Facade: No model name resolved for agent '{agent_name}' (no LLMConfig ID and no direct override). LLM client factory will use its default."
                )

            # 3. Get/Create LLM Client Instance using Cache
            llm_client_instance: Optional[BaseLLM] = None
            cache_key: Optional[str] = None

            if llm_config_for_override_obj:
                cache_key = llm_config_for_override_obj.llm_id
                llm_client_instance = self._llm_client_cache.get(cache_key)
                if not llm_client_instance:
                    logger.debug(f"Facade: LLM client for '{cache_key}' not in cache. Creating...")
                    # Use the resolved LLMConfig object to create the client
                    llm_client_instance = self._create_llm_client(llm_config_for_override_obj)
                    self._llm_client_cache[cache_key] = llm_client_instance
                    logger.debug(f"Facade: Cached LLM client for '{cache_key}'.")
                else:
                    logger.debug(f"Facade: Reusing cached LLM client for '{cache_key}'.")
            else:
                # No LLMConfig ID - create temporary config and non-cached client
                logger.warning(f"Facade: Agent '{agent_name}' running without a specific LLMConfig ID. Creating temporary, non-cached client.")
                # Create a temporary LLMConfig based on resolved effective parameters
                temp_llm_config = LLMConfig(
                    llm_id=f"temp_{agent_name}", # Temporary ID
                    provider="anthropic", # Assuming default provider for now
                    model_name=effective_model_name, # Use resolved name
                    temperature=effective_temperature,
                    max_tokens=effective_max_tokens,
                    default_system_prompt=effective_system_prompt_for_llm_client # Correct variable
                )
                llm_client_instance = self._create_llm_client(temp_llm_config) # Do not cache

            if not llm_client_instance:
                 # This should ideally not happen if _create_llm_client raises errors
                 raise RuntimeError(f"Failed to obtain LLM client instance for agent '{agent_name}'.")

            # 4. Prepare Initial Messages (Load History + User Message)
            initial_messages_for_agent: List[MessageParam] = []
            load_history = (
                agent_config.include_history and self._storage_manager and session_id
            )
            if (
                load_history and self._storage_manager
            ):  # Added check for self._storage_manager
                try:
                    loaded_history = self._storage_manager.load_history(
                        agent_name, session_id
                    )
                    if loaded_history:
                        # Cast each dict to MessageParam before extending
                        typed_history = [
                            cast(MessageParam, item) for item in loaded_history
                        ]
                        initial_messages_for_agent.extend(typed_history)
                        logger.info(
                            f"Facade: Loaded {len(loaded_history)} history turns for agent '{agent_name}', session '{session_id}'."
                        )
                except Exception as e:
                    logger.error(
                        f"Facade: Failed to load history for agent '{agent_name}', session '{session_id}': {e}",
                        exc_info=True,
                    )
                    # Continue without history on load failure

            # Add the current user message, formatted correctly as content block list
            initial_messages_for_agent.append(
                {"role": "user", "content": [{"type": "text", "text": user_message}]}
            )

            # 5. Instantiate the new Agent class (formerly ConversationManager)
            agent_instance = Agent(
                config=agent_config,
                llm_client=llm_client_instance,
                host_instance=self._host,
                initial_messages=initial_messages_for_agent,
                system_prompt_override=system_prompt,  # Pass override from run_agent args
                llm_config_for_override=llm_config_for_override_obj,  # Pass fetched override object
            )
            logger.debug(f"Facade: Instantiated new Agent class for '{agent_name}'")

            # 6. Execute Conversation
            logger.info(f"Facade: Running conversation for Agent '{agent_name}'...")
            agent_result: AgentExecutionResult = await agent_instance.run_conversation()
            logger.info(f"Facade: Agent '{agent_name}' conversation finished.")

            # 7. Save History (if enabled and successful)
            save_history = (
                agent_config.include_history
                and self._storage_manager
                and session_id
                and not agent_result.has_error
            )
            if (
                save_history and self._storage_manager
            ):  # Added check for self._storage_manager
                try:
                    # AgentExecutionResult.conversation is List[AgentOutputMessage]
                    # Convert to List[Dict] for storage
                    serializable_conversation = [
                        msg.model_dump(mode="json") for msg in agent_result.conversation
                    ]
                    self._storage_manager.save_full_history(
                        agent_name=agent_name,
                        session_id=session_id,
                        conversation=serializable_conversation,
                    )
                    logger.info(
                        f"Facade: Saved {len(serializable_conversation)} history turns for agent '{agent_name}', session '{session_id}'."
                    )
                except Exception as e:
                    # Log error but don't fail the overall result
                    logger.error(
                        f"Facade: Failed to save history for agent '{agent_name}', session '{session_id}': {e}",
                        exc_info=True,
                    )

            # 8. Return Result (as dict)
            return agent_result.model_dump(mode="json")

        except KeyError as e:
            error_msg = f"Configuration error: {str(e)}"
            logger.error(f"Facade: {error_msg}")
            return error_factory(agent_name, error_msg)
        except ValueError as e:  # Catch LLM client init errors, etc.
            error_msg = f"Initialization error for Agent '{agent_name}': {str(e)}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return error_factory(agent_name, error_msg)
        except Exception as e:
            # Catch unexpected errors during setup or execution within the facade logic
            error_msg = f"Unexpected error running Agent '{agent_name}': {type(e).__name__}: {str(e)}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return error_factory(agent_name, error_msg)

    async def run_simple_workflow(
        self, workflow_name: str, initial_input: Any
    ) -> Dict[str, Any]:
        """Executes a configured simple workflow by name using the helper."""

        def error_factory(name: str, msg: str) -> Dict[str, Any]:
            return {
                "workflow_name": name,
                "status": "failed",
                "final_message": None,
                "error": msg,
            }

        return await self._execute_component(
            component_type="Simple Workflow",
            component_name=workflow_name,
            config_lookup=lambda name: self._current_project.simple_workflows.get(  # Changed simple_workflow_configs to simple_workflows
                name
            ),
            executor_setup=lambda wf_config: SimpleWorkflowExecutor(
                config=wf_config,
                agent_configs=self._current_project.agents,  # Pass from facade's current_project # Changed agent_configs to agents
                # host_instance=self._host, # To be removed from SimpleWorkflowExecutor
                # llm_client=AnthropicLLM(model_name="claude-3-haiku-20240307"), # To be removed
                facade=self,
            ),
            execution_func=lambda instance, **kwargs: instance.execute(**kwargs),
            error_structure_factory=error_factory,
            # Execution kwargs:
            initial_input=initial_input,
        )

    async def run_custom_workflow(
        self, workflow_name: str, initial_input: Any, session_id: Optional[str] = None
    ) -> Any:  # Added session_id
        """Executes a configured custom workflow by name using the helper."""

        def error_factory(name: str, msg: str) -> Dict[str, Any]:
            # Custom workflows can return anything, so error structure is simpler
            return {"status": "failed", "error": msg}

        return await self._execute_component(
            component_type="Custom Workflow",
            component_name=workflow_name,
            config_lookup=lambda name: self._current_project.custom_workflows.get(  # Changed custom_workflow_configs to custom_workflows
                name
            ),
            executor_setup=lambda wf_config: CustomWorkflowExecutor(
                config=wf_config,
            ),
            execution_func=lambda instance, **kwargs: instance.execute(**kwargs),
            error_structure_factory=error_factory,
            # Execution kwargs:
            initial_input=initial_input,
            executor=self,  # Pass the facade itself to the custom workflow
            session_id=session_id,  # Pass session_id here
        )
