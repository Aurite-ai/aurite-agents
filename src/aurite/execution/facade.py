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
import json  # Added for dynamic tool selection
import copy  # Added for copying agent_config

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from ..host.host import MCPHost  # Needed for passing to executors/workflows
    from ..components.workflows.simple_workflow import (
        SimpleWorkflowExecutor,
    )  # Import for type hint
    from ..components.workflows.custom_workflow import CustomWorkflowExecutor
    from ..storage.db_manager import StorageManager
    from ..config.config_models import ProjectConfig
    from aurite.components.llm.base_client import (
        BaseLLM,
    )  # Import for type hinting LLM clients


# Actual runtime imports
from ..components.llm.providers.openai_client import OpenAIClient  # Moved here
from ..config.config_models import (
    AgentConfig,
    LLMConfig,
)  # Ensure LLMConfig is imported for direct use at runtime

# Import Agent at runtime for instantiation
from ..components.agents.agent import Agent

# Import AgentExecutionResult for type hinting the result
from ..components.agents.agent_models import (
    AgentExecutionResult,
    AgentOutputMessage,  # Added AgentOutputContentBlock
)  # Added AgentOutputMessage

# Import MessageParam for constructing initial messages
from anthropic.types import MessageParam

# Import SimpleWorkflowExecutor at runtime
from ..components.workflows.simple_workflow import SimpleWorkflowExecutor
from ..components.workflows.workflow_models import SimpleWorkflowExecutionResult

# Import CustomWorkflowExecutor at runtime
from ..components.workflows.custom_workflow import CustomWorkflowExecutor

# Import default LLM client for SimpleWorkflowExecutor instantiation
from ..components.llm.providers.anthropic_client import (
    AnthropicLLM,
)
from ..components.llm.providers.gemini_client import GeminiLLM

from termcolor import colored  # Added import

logger = logging.getLogger(__name__)


class ExecutionFacade:
    """
    A facade that simplifies the execution of different component types
    (Agents, Simple Workflows, Custom Workflows) managed by the Aurite.

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
        self._llm_client_cache: Dict[str, BaseLLM] = {}  # LLM Client Cache
        self._is_shut_down = False  # Flag to prevent double shutdown
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
        model_name = (
            llm_config.model_name or "claude-3-haiku-20240307"
        )  # Default if not specified in config

        logger.debug(
            f"Creating LLM client for provider '{provider}', model '{model_name}' (ID: {llm_config.llm_id})"
        )

        if provider == "anthropic":
            # API key resolution could be enhanced here (e.g., check env vars specified in config)
            # For now, relies on AnthropicLLM's internal check for ANTHROPIC_API_KEY
            try:
                return AnthropicLLM(
                    model_name=model_name,
                    temperature=llm_config.temperature,  # Pass None if not set, client handles default
                    max_tokens=llm_config.max_tokens,  # Pass None if not set, client handles default
                    system_prompt=llm_config.default_system_prompt,  # Pass None if not set, client handles default
                    # api_key=resolved_api_key # Example if key resolution happened here
                )
            except Exception as e:
                logger.error(
                    f"Failed to instantiate AnthropicLLM for config '{llm_config.llm_id}': {e}",
                    exc_info=True,
                )
                raise ValueError(f"Failed to create Anthropic client: {e}") from e
        elif provider == "gemini":
            try:
                return GeminiLLM(
                    model_name=model_name,
                    temperature=llm_config.temperature, # Pass None if not set, client handles default
                    max_tokens=llm_config.max_tokens,   # Pass None if not set, client handles default
                    system_prompt=llm_config.default_system_prompt # Pass None if not set, client handles default
                    # api_key=resolved_api_key # Example if key resolution happened here
                )
            except Exception as e:
                logger.error(f"Failed to instantiate GeminiLLM for config '{llm_config.llm_id}': {e}", exc_info=True)
                raise ValueError(f"Failed to create Gemini client: {e}") from e
        elif provider == "openai":
            try:
                return OpenAIClient(
                    model_name=model_name,  # Already has a default if llm_config.model_name is None
                    temperature=llm_config.temperature,
                    max_tokens=llm_config.max_tokens,
                    system_prompt=llm_config.default_system_prompt,
                )
            except Exception as e:
                logger.error(
                    f"Failed to instantiate OpenAIClient for config '{llm_config.llm_id}': {e}",
                    exc_info=True,
                )
                raise ValueError(f"Failed to create OpenAI client: {e}") from e
        else:
            logger.error(
                f"Unsupported LLM provider specified in LLMConfig '{llm_config.llm_id}': {provider}"
            )
            raise NotImplementedError(
                f"LLM provider '{provider}' is not currently supported."
            )

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
        logger.debug(
            "ExecutionFacade LLM client cache cleared and facade marked as shut down."
        )

    # --- Private Helper for Dynamic Tool Selection ---

    async def _get_llm_selected_client_ids(
        self,
        agent_config: AgentConfig,  # For context, logging, or future use
        user_message: str,
        system_prompt_for_agent: Optional[str],
    ) -> Optional[List[str]]:
        """
        Uses an LLM to dynamically select client_ids for an agent based on the user message,
        agent's system prompt, and available tools.
        """
        logger.debug(
            f"Attempting to dynamically select client_ids for agent '{agent_config.name}'."
        )

        tool_selector_llm_config = LLMConfig(
            llm_id="internal_dynamic_tool_selector_haiku",  # Specific ID for caching
            provider="anthropic",
            model_name="claude-3-haiku-20240307",  # Fast and cost-effective model
            temperature=0.2,  # Lower temperature for more deterministic selection
            max_tokens=1024,
            default_system_prompt=(
                "You are an expert AI assistant responsible for selecting the most relevant set of tools (MCP Clients) "
                "for another AI agent to accomplish a given task.\n"
                "You will be provided with:\n"
                "1. The user's message to the agent.\n"
                "2. The agent's primary system prompt.\n"
                "3. A list of available tool sets (MCP Clients) with their capabilities.\n"
                "Your goal is to choose the minimal set of tool sets that will provide the necessary capabilities "
                "for the agent to best respond to the user's message, guided by its system prompt.\n"
                'Respond with a JSON object containing a single key "selected_client_ids", which is a list of strings '
                "representing the IDs of the chosen tool sets.\n"
                'If no tool sets are relevant or necessary, return an empty list for "selected_client_ids".'
            ),
        )

        tool_selector_llm_client = self._llm_client_cache.get(
            tool_selector_llm_config.llm_id
        )
        if not tool_selector_llm_client:
            try:
                tool_selector_llm_client = self._create_llm_client(
                    tool_selector_llm_config
                )
                self._llm_client_cache[tool_selector_llm_config.llm_id] = (
                    tool_selector_llm_client
                )
                logger.debug(
                    f"Created and cached LLM client for tool selection: {tool_selector_llm_config.llm_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to create LLM client for tool selection: {e}",
                    exc_info=True,
                )
                return None
        else:
            logger.debug(
                f"Reusing cached LLM client for tool selection: {tool_selector_llm_config.llm_id}"
            )

        available_clients = self._current_project.mcp_servers
        client_info_parts = ["Available Tool Sets (MCP Clients):"]
        if not available_clients:
            client_info_parts.append("No tool sets are currently available.")
        else:
            for client_id, client_cfg in available_clients.items():
                client_capabilities = set(client_cfg.capabilities or [])
                root_names = []
                for root in client_cfg.roots:
                    client_capabilities.update(root.capabilities or [])
                    root_names.append(root.name)

                cap_string = (
                    ", ".join(sorted(list(client_capabilities)))
                    if client_capabilities
                    else "None"
                )
                roots_string = ", ".join(root_names) if root_names else "N/A"
                client_info_parts.append(
                    f"---\nTool Set ID: {client_id}\nCapabilities: {cap_string}\nRoot Names: {roots_string}"
                )
        client_info_parts.append("---")

        prompt_for_tool_selection_llm_parts = [
            *client_info_parts,
            "\nAgent's System Prompt:",
            system_prompt_for_agent or "No system prompt provided for the agent.",
            "\nUser's Message to Agent:",
            user_message,
            "\nBased on the Agent's System Prompt and the User's Message, which tool sets should be selected?",
        ]
        prompt_content_for_tool_selection = "\n".join(
            prompt_for_tool_selection_llm_parts
        )

        # Define the schema for the expected JSON output
        tool_selection_schema = {
            "type": "object",
            "properties": {
                "selected_client_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of client_ids that should be selected for the agent.",
                }
            },
            "required": ["selected_client_ids"],
        }

        try:
            logger.debug(
                f"Calling tool selection LLM. Prompt content:\n{prompt_content_for_tool_selection[:500]}..."
            )  # Log truncated prompt
            response_message: AgentOutputMessage = await tool_selector_llm_client.create_message(
                messages=[
                    {"role": "user", "content": prompt_content_for_tool_selection}
                ],
                tools=None,  # No tools for the tool selector LLM itself
                schema=tool_selection_schema,  # Pass schema for JSON enforcement
                llm_config_override=tool_selector_llm_config,  # Use the specific config for this call
            )

            if not response_message.content or not response_message.content[0].text:
                logger.error("Tool selection LLM returned empty content.")
                return None

            llm_response_text = response_message.content[0].text
            logger.debug(f"Tool selection LLM raw response: {llm_response_text}")

            try:
                parsed_response = json.loads(llm_response_text)
                selected_ids_from_llm = parsed_response.get("selected_client_ids")

                if selected_ids_from_llm is None or not isinstance(
                    selected_ids_from_llm, list
                ):
                    logger.error(
                        f"Tool selection LLM response missing 'selected_client_ids' list or invalid format: {llm_response_text}"
                    )
                    return None

                # Validate selected IDs
                valid_selected_ids = []
                all_available_client_ids = set(available_clients.keys())
                for client_id in selected_ids_from_llm:
                    if not isinstance(client_id, str):
                        logger.warning(
                            f"Tool selection LLM returned a non-string client_id: {client_id}. Skipping."
                        )
                        continue
                    if client_id in all_available_client_ids:
                        valid_selected_ids.append(client_id)
                    else:
                        logger.warning(
                            f"Tool selection LLM selected non-existent client_id '{client_id}'. It will be ignored."
                        )

                logger.info(
                    f"Dynamically selected client_ids: {valid_selected_ids} (Agent: {agent_config.name})"
                )
                return valid_selected_ids

            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to parse JSON response from tool selection LLM: {e}\nResponse: {llm_response_text}",
                    exc_info=True,
                )
                return None

        except Exception as e:
            logger.error(
                f"Error during LLM call for dynamic tool selection: {e}", exc_info=True
            )
            return None

    # --- Private Execution Helper ---

    async def _execute_component(
        self,
        component_type: str,
        component_name: str,
        config_lookup: Callable[[str], Any],
        executor_setup: Callable[[Any], Any],
        execution_func: Callable[..., Coroutine[Any, Any, Any]],
        error_structure_factory: Callable[[str, str], Any],
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

            # --- Dynamic Tool Selection (New Step for streaming) ---
            processed_agent_config = agent_config  # Start with the original
            if agent_config.auto:
                logger.info(
                    f"Agent '{agent_name}' (streaming) has 'auto=True'. Attempting dynamic tool selection."
                )
                # Determine the system prompt to pass to the tool selector LLM
                system_prompt_for_tool_selector = agent_config.system_prompt
                if not system_prompt_for_tool_selector and agent_config.llm_config_id:
                    temp_llm_config_for_prompt = self._current_project.llms.get(
                        agent_config.llm_config_id
                    )
                    if temp_llm_config_for_prompt:
                        system_prompt_for_tool_selector = (
                            temp_llm_config_for_prompt.default_system_prompt
                        )

                selected_client_ids = await self._get_llm_selected_client_ids(
                    agent_config=agent_config,  # Pass original for context
                    user_message=user_message,
                    system_prompt_for_agent=system_prompt_for_tool_selector,
                )
                if selected_client_ids is not None:
                    processed_agent_config = copy.deepcopy(agent_config)
                    processed_agent_config.mcp_servers = selected_client_ids
                    logger.info(
                        f"Dynamically selected mcp_servers for agent '{agent_name}' (streaming): {selected_client_ids}"
                    )
                else:
                    logger.warning(
                        f"Dynamic tool selection failed for agent '{agent_name}' (streaming). "
                        f"Falling back to static mcp_servers: {agent_config.mcp_servers or 'None'}."
                    )
            # Use processed_agent_config for the rest of the streaming logic

            # 2. Resolve LLM Parameters & Instantiate LLM Client (using processed_agent_config)
            effective_model_name: Optional[str] = None
            effective_temperature: Optional[float] = None
            effective_max_tokens: Optional[int] = None
            effective_system_prompt_for_llm_client: Optional[str] = None

            if processed_agent_config.llm_config_id:
                if self._current_project.llms:
                    llm_config_for_override_obj = self._current_project.llms.get(
                        processed_agent_config.llm_config_id
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
                        f"LLMConfig ID '{processed_agent_config.llm_config_id}' for agent '{agent_name}' (streaming) not found."
                    )

            if processed_agent_config.model is not None:
                effective_model_name = processed_agent_config.model
            if processed_agent_config.temperature is not None:
                effective_temperature = processed_agent_config.temperature
            if processed_agent_config.max_tokens is not None:
                effective_max_tokens = processed_agent_config.max_tokens
            if (
                processed_agent_config.system_prompt is not None
            ):  # This is agent's own default system prompt
                effective_system_prompt_for_llm_client = (
                    processed_agent_config.system_prompt
                )
            if not effective_model_name:  # Fallback if no model specified anywhere
                effective_model_name = "claude-3-haiku-20240307"

            # Note: The `system_prompt` argument to `stream_agent_run` is an override for THIS RUN.
            # `effective_system_prompt_for_llm_client` is for the LLM client's default initialization.
            # The Agent class will handle the final system prompt resolution.

            # 2.b Get/Create LLM Client Instance using Cache (based on resolved parameters)
            llm_client_instance: Optional[BaseLLM] = None
            cache_key: Optional[str] = None

            if llm_config_for_override_obj:
                cache_key = llm_config_for_override_obj.llm_id
                llm_client_instance = self._llm_client_cache.get(cache_key)
                if not llm_client_instance:
                    logger.debug(
                        f"Facade: LLM client for '{cache_key}' not in cache. Creating..."
                    )
                    llm_client_instance = self._create_llm_client(
                        llm_config_for_override_obj
                    )
                    self._llm_client_cache[cache_key] = llm_client_instance
                    logger.debug(f"Facade: Cached LLM client for '{cache_key}'.")
                else:
                    logger.debug(
                        f"Facade: Reusing cached LLM client for '{cache_key}'."
                    )
            else:
                # No LLMConfig ID - create temporary config and non-cached client
                logger.warning(
                    f"Facade: Agent '{agent_name}' (streaming) running without a specific LLMConfig ID. Creating temporary, non-cached client using default OpenAI config."
                )
                # Create a temporary LLMConfig using the new default values, but allowing agent-specific overrides
                temp_llm_config = LLMConfig(
                    llm_id=f"temp_{agent_name}",  # Temporary ID
                    provider="openai",
                    model_name=effective_model_name or "gpt-3.5-turbo",
                    temperature=effective_temperature
                    if effective_temperature is not None
                    else 0.7,
                    max_tokens=effective_max_tokens or 4000,
                    default_system_prompt=effective_system_prompt_for_llm_client
                    or "You are a helpful OpenAI assistant.",
                )
                llm_client_instance = self._create_llm_client(
                    temp_llm_config
                )  # Do not cache

            if not llm_client_instance:
                # This should ideally not happen if _create_llm_client raises errors
                raise RuntimeError(
                    f"Failed to obtain LLM client instance for agent '{agent_name}'."
                )

            # 3. Prepare Initial Messages (using processed_agent_config)
            initial_messages_for_agent: List[MessageParam] = []
            if (
                processed_agent_config.include_history
                and self._storage_manager
                and session_id
            ):
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

            # 4. Instantiate Agent (using processed_agent_config)
            agent_instance = Agent(
                config=processed_agent_config,  # Use the potentially modified config
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
    ) -> AgentExecutionResult:
        """
        Executes a configured agent by name, handling history loading/saving if configured.
        """
        agent_config: Optional[AgentConfig] = None
        # agent_instance: Optional[Agent] = None # Will be created after LLM client
        # llm_client_instance: Optional[BaseLLM] = None # Will be created after param resolution

        def error_factory(name: str, msg: str) -> AgentExecutionResult:
            # Return structure matching AgentExecutionResult fields for consistency
            return AgentExecutionResult(
                conversation=[],
                final_response=None,
                tool_uses_in_final_turn=[],
                error=msg,
            )  # Return as AgentExecutionResult instance

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

            # --- Dynamic Tool Selection (New Step) ---
            processed_agent_config = agent_config  # Start with the original
            if agent_config.auto:
                logger.info(
                    f"Agent '{agent_name}' has 'auto=True'. Attempting dynamic tool selection."
                )
                # Determine the system prompt to pass to the tool selector LLM
                # This logic mirrors how the agent's own system prompt is resolved later
                system_prompt_for_tool_selector = (
                    agent_config.system_prompt
                )  # Agent's specific system prompt
                if not system_prompt_for_tool_selector and agent_config.llm_config_id:
                    temp_llm_config_for_prompt = self._current_project.llms.get(
                        agent_config.llm_config_id
                    )
                    if temp_llm_config_for_prompt:
                        system_prompt_for_tool_selector = (
                            temp_llm_config_for_prompt.default_system_prompt
                        )

                selected_client_ids = await self._get_llm_selected_client_ids(
                    agent_config=agent_config,
                    user_message=user_message,
                    system_prompt_for_agent=system_prompt_for_tool_selector,  # Pass the resolved system prompt
                )
                if (
                    selected_client_ids is not None
                ):  # Can be an empty list if LLM chose no tools
                    # Create a copy to modify for this run
                    processed_agent_config = copy.deepcopy(agent_config)
                    processed_agent_config.mcp_servers = selected_client_ids
                    logger.info(
                        f"Dynamically selected mcp_servers for agent '{agent_name}': {selected_client_ids}"
                    )
                else:
                    logger.warning(
                        f"Dynamic tool selection failed for agent '{agent_name}'. "
                        f"Falling back to static mcp_servers: {agent_config.mcp_servers or 'None'}."
                    )
                    # processed_agent_config remains the original agent_config
            # Use processed_agent_config (which is original or a modified copy) for the rest of the logic

            # 2. Resolve LLM Parameters (using processed_agent_config)
            effective_model_name: Optional[str] = None
            effective_temperature: Optional[float] = None
            effective_max_tokens: Optional[int] = None
            effective_system_prompt_for_llm_client: Optional[
                str
            ] = (  # Renamed from effective_system_prompt
                None
            )
            llm_config_for_override_obj: Optional[LLMConfig] = None

            # 2.a. LLMConfig Lookup (Base values from processed_agent_config)
            if processed_agent_config.llm_config_id:
                if not self._current_project.llms:
                    logger.warning(
                        f"LLM configurations not found in current project for agent '{agent_name}'."
                    )
                else:
                    llm_config_for_override_obj = self._current_project.llms.get(
                        processed_agent_config.llm_config_id
                    )
                if llm_config_for_override_obj:
                    logger.debug(
                        f"Facade: Applying base LLMConfig '{processed_agent_config.llm_config_id}' for agent '{agent_name}'."
                    )
                    effective_model_name = llm_config_for_override_obj.model_name
                    effective_temperature = llm_config_for_override_obj.temperature
                    effective_max_tokens = llm_config_for_override_obj.max_tokens
                    # This is the default system prompt for the LLM client if agent doesn't override
                    effective_system_prompt_for_llm_client = (
                        llm_config_for_override_obj.default_system_prompt
                    )
                else:
                    logger.warning(
                        f"Facade: LLMConfig ID '{processed_agent_config.llm_config_id}' specified for agent '{agent_name}' not found. "
                        "Proceeding with AgentConfig-specific LLM parameters or defaults for LLM client instantiation."
                    )

            # 2.b. AgentConfig Overrides (from processed_agent_config)
            if processed_agent_config.model is not None:
                effective_model_name = processed_agent_config.model
                logger.debug(
                    f"Facade: AgentConfig overrides model_name to '{effective_model_name}'."
                )
            if processed_agent_config.temperature is not None:
                effective_temperature = processed_agent_config.temperature
                logger.debug(
                    f"Facade: AgentConfig overrides temperature to '{effective_temperature}'."
                )
            if processed_agent_config.max_tokens is not None:
                effective_max_tokens = processed_agent_config.max_tokens
                logger.debug(
                    f"Facade: AgentConfig overrides max_tokens to '{effective_max_tokens}'."
                )

            # System prompt for LLM client instantiation:
            # Prioritize agent_config.system_prompt, then llm_config.default_system_prompt.
            # The `system_prompt` argument to `run_agent` is handled by the Agent class itself.
            if processed_agent_config.system_prompt is not None:
                effective_system_prompt_for_llm_client = (
                    processed_agent_config.system_prompt
                )
                logger.debug(
                    "Facade: AgentConfig provides default system prompt for LLM client instantiation."
                )
            # If agent_config.system_prompt is None, effective_system_prompt_for_llm_client
            # will retain the value from LLMConfig (if any) or be None.

            if (
                not effective_model_name and not llm_config_for_override_obj
            ):  # Check based on llm_config_for_override_obj from processed_agent_config
                logger.debug(
                    f"Facade: No model name resolved for agent '{agent_name}' (no LLMConfig ID and no direct override). LLM client factory will use its default."
                )

            # 3. Get/Create LLM Client Instance using Cache (based on resolved parameters)
            llm_client_instance: Optional[BaseLLM] = None
            cache_key: Optional[str] = None

            if llm_config_for_override_obj:
                cache_key = llm_config_for_override_obj.llm_id
                llm_client_instance = self._llm_client_cache.get(cache_key)
                if not llm_client_instance:
                    logger.debug(
                        f"Facade: LLM client for '{cache_key}' not in cache. Creating..."
                    )
                    # Use the resolved LLMConfig object to create the client
                    llm_client_instance = self._create_llm_client(
                        llm_config_for_override_obj
                    )
                    self._llm_client_cache[cache_key] = llm_client_instance
                    logger.debug(f"Facade: Cached LLM client for '{cache_key}'.")
                else:
                    logger.debug(
                        f"Facade: Reusing cached LLM client for '{cache_key}'."
                    )
            else:
                # No LLMConfig ID - create temporary config and non-cached client
                logger.warning(
                    f"Facade: Agent '{agent_name}' running without a specific LLMConfig ID. Creating temporary, non-cached client using default OpenAI config."
                )
                # Create a temporary LLMConfig using the new default values, but allowing agent-specific overrides
                temp_llm_config = LLMConfig(
                    llm_id=f"temp_{agent_name}",  # Temporary ID
                    provider="openai",
                    model_name=effective_model_name or "gpt-3.5-turbo",
                    temperature=effective_temperature
                    if effective_temperature is not None
                    else 0.7,
                    max_tokens=effective_max_tokens or 4000,
                    default_system_prompt=effective_system_prompt_for_llm_client
                    or "You are a helpful OpenAI assistant.",
                )
                llm_client_instance = self._create_llm_client(
                    temp_llm_config
                )  # Do not cache

            if not llm_client_instance:
                # This should ideally not happen if _create_llm_client raises errors
                raise RuntimeError(
                    f"Failed to obtain LLM client instance for agent '{agent_name}'."
                )

            # Determine provider for conditional logic
            provider_name = "anthropic"  # Default
            if llm_config_for_override_obj and llm_config_for_override_obj.provider:
                provider_name = llm_config_for_override_obj.provider.lower()
            elif isinstance(
                llm_client_instance, OpenAIClient
            ):  # Check instance if no explicit config
                provider_name = "openai"

            logger.debug(
                f"Determined provider for agent '{agent_name}': {provider_name}"
            )

            # The logic for OpenAI provider using OpenAIMCPAgent and OpenAPIAgentRunner is removed.
            # All providers will now use Aurite's standard Agent execution flow.
            # The llm_client_instance will be either AnthropicLLM or our new OpenAIClient.

            # 4. Prepare Initial Messages (Load History + User Message, using processed_agent_config)
            initial_messages_for_agent: List[MessageParam] = []
            load_history = (
                processed_agent_config.include_history
                and self._storage_manager
                and session_id
            )
            if (
                load_history and self._storage_manager
            ):  # This block is for non-OpenAI providers
                try:
                    loaded_history = self._storage_manager.load_history(
                        agent_name, session_id
                    )
                    if loaded_history:
                        typed_history = [
                            cast(MessageParam, item) for item in loaded_history
                        ]
                        initial_messages_for_agent.extend(typed_history)
                        logger.info(
                            f"Facade: Loaded {len(loaded_history)} history turns for Aurite agent '{agent_name}', session '{session_id}'."
                        )
                except Exception as e:
                    logger.error(
                        f"Facade: Failed to load history for Aurite agent '{agent_name}', session '{session_id}': {e}",
                        exc_info=True,
                    )

            initial_messages_for_agent.append(
                {"role": "user", "content": [{"type": "text", "text": user_message}]}
            )

            # 5. Instantiate Aurite's Agent class (using processed_agent_config)
            aurite_agent_instance = Agent(
                config=processed_agent_config,  # Use the potentially modified config
                llm_client=llm_client_instance,  # This is Aurite's LLMClient (e.g. AnthropicLLM)
                host_instance=self._host,
                initial_messages=initial_messages_for_agent,
                system_prompt_override=system_prompt,
                llm_config_for_override=llm_config_for_override_obj,
            )
            logger.debug(f"Facade: Instantiated Aurite Agent class for '{agent_name}'")

            # 6. Execute Aurite Agent Conversation
            logger.info(
                colored(
                    f"Facade: Running conversation for Aurite Agent '{agent_name}'...",
                    "blue",
                    attrs=["bold"],
                )
            )
            agent_result: AgentExecutionResult = (
                await aurite_agent_instance.run_conversation()
            )
            logger.info(
                colored(
                    f"Facade: Aurite Agent '{agent_name}' conversation finished.",
                    "blue",
                    attrs=["bold"],
                )
            )

            # 7. Save History for Aurite Agent (if enabled and successful, using processed_agent_config)
            save_history = (
                processed_agent_config.include_history
                and self._storage_manager
                and session_id
                and not agent_result.has_error
            )
            if save_history and self._storage_manager:
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

            # 8. Return Result (as Pydantic model instance)
            return agent_result

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
    ) -> SimpleWorkflowExecutionResult:
        """Executes a configured simple workflow by name using the helper."""

        def error_factory(name: str, msg: str) -> SimpleWorkflowExecutionResult:
            return SimpleWorkflowExecutionResult(
                workflow_name=name,
                status="failed",
                final_output=None,
                error=msg,
            )

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

    def get_project_config(self):
        """Simple getter for project config"""
        return self._current_project

    async def get_custom_workflow_input_type(self, workflow_name: str):
        """Get the input type for a custom workflow.

        Returns:
            The type, or None if a get_input_type method is not defined"""

        def error_factory(name: str, msg: str) -> Dict[str, Any]:
            return {"status": "failed", "error": msg}

        return await self._execute_component(
            component_type="Custom Workflow",
            component_name=workflow_name,
            config_lookup=lambda name: self._current_project.custom_workflows.get(name),
            executor_setup=lambda wf_config: CustomWorkflowExecutor(
                config=wf_config,
            ),
            execution_func=lambda instance, **kwargs: instance.get_input_type(**kwargs),
            error_structure_factory=error_factory,
        )

    async def get_custom_workflow_output_type(self, workflow_name: str):
        """Get the output type for a custom workflow.

        Returns:
            The type, or None if a get_output_type method is not defined"""

        def error_factory(name: str, msg: str) -> Dict[str, Any]:
            return {"status": "failed", "error": msg}

        return await self._execute_component(
            component_type="Custom Workflow",
            component_name=workflow_name,
            config_lookup=lambda name: self._current_project.custom_workflows.get(name),
            executor_setup=lambda wf_config: CustomWorkflowExecutor(
                config=wf_config,
            ),
            execution_func=lambda instance, **kwargs: instance.get_output_type(
                **kwargs
            ),
            error_structure_factory=error_factory,
        )
