"""
Provides a unified facade for executing Agents, Linear Workflows, and Custom Workflows.
"""

import logging
import os
import uuid
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional, Tuple

from langfuse import Langfuse
from termcolor import colored

from ..components.agents.agent import Agent
from ..components.agents.agent_models import AgentRunResult
from ..components.llm.providers.litellm_client import LiteLLMClient
from ..components.workflows.custom_workflow import CustomWorkflowExecutor
from ..components.workflows.linear_workflow import LinearWorkflowExecutor
from ..components.workflows.workflow_models import LinearWorkflowExecutionResult
from ..config.config_manager import ConfigManager
from ..config.config_models import (
    AgentConfig,
    ClientConfig,
    LLMConfig,
    LLMConfigOverrides,
)
from ..errors import AgentExecutionError, ConfigurationError, WorkflowExecutionError
from ..host.host import MCPHost
from ..storage.cache_manager import CacheManager
from ..storage.db_manager import StorageManager
from ..storage.session_manager import SessionManager
from ..storage.session_models import SessionMetadata

if TYPE_CHECKING:
    from langfuse.client import StatefulTraceClient

logger = logging.getLogger(__name__)


class ExecutionFacade:
    """
    A facade that simplifies the execution of different component types
    (Agents, Linear Workflows, Custom Workflows) managed by the Aurite.
    """

    def __init__(
        self,
        config_manager: "ConfigManager",
        host_instance: "MCPHost",
        storage_manager: Optional["StorageManager"] = None,
        cache_manager: Optional["CacheManager"] = None,
        langfuse: Optional["Langfuse"] = None,
    ):
        if not config_manager:
            raise ValueError("ConfigManager instance is required for ExecutionFacade.")
        if not host_instance:
            raise ValueError("MCPHost instance is required for ExecutionFacade.")

        self._config_manager = config_manager
        self._host = host_instance
        self._storage_manager = storage_manager
        # The facade now uses a SessionManager for history, which in turn uses the CacheManager.
        self._session_manager = SessionManager(cache_manager=cache_manager) if cache_manager else None
        self._llm_client_cache: Dict[str, "LiteLLMClient"] = {}
        self.langfuse = langfuse
        logger.debug(f"ExecutionFacade initialized (StorageManager {'present' if storage_manager else 'absent'}).")

    def set_config_manager(self, config_manager: "ConfigManager"):
        """Updates the ConfigManager instance used by the facade."""
        self._config_manager = config_manager

    # --- Private Helper Methods ---

    async def _prepare_agent_for_run(
        self,
        agent_name: str,
        user_message: str,
        system_prompt_override: Optional[str] = None,
        session_id: Optional[str] = None,
        force_include_history: Optional[bool] = None,
    ) -> Tuple[Agent, List[str]]:
        agent_config_dict = self._config_manager.get_config("agent", agent_name)
        if not agent_config_dict:
            raise ConfigurationError(f"Agent configuration '{agent_name}' not found.")

        agent_config_for_run = AgentConfig(**agent_config_dict)
        dynamically_registered_servers: List[str] = []

        # JIT Registration of MCP Servers
        if agent_config_for_run.mcp_servers:
            for server_name in agent_config_for_run.mcp_servers:
                if server_name not in self._host.registered_server_names:
                    server_config_dict = self._config_manager.get_config("mcp_server", server_name)
                    if not server_config_dict:
                        raise ConfigurationError(
                            f"MCP Server '{server_name}' required by agent '{agent_name}' not found."
                        )
                    server_config = ClientConfig(**server_config_dict)
                    await self._host.register_client(server_config)
                    dynamically_registered_servers.append(server_name)

        llm_config_id = agent_config_for_run.llm_config_id
        if not llm_config_id:
            logger.warning(f"Agent '{agent_name}' does not have an llm_config_id. Trying to use 'default' LLM.")
            llm_config_id = "default"

        llm_config_dict = self._config_manager.get_config("llm", llm_config_id)

        if not llm_config_dict:
            if llm_config_id == "default":
                logger.warning("No 'default' LLM config found. Falling back to hardcoded OpenAI GPT-4.")
                llm_config_dict = {
                    "name": "default_openai_fallback",
                    "provider": "openai",
                    "model": "gpt-4-turbo-preview",
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "default_system_prompt": "You are a helpful OpenAI assistant.",
                    "api_key_env_var": "OPENAI_API_KEY",
                }
            else:
                raise ConfigurationError(f"LLM configuration '{llm_config_id}' not found.")

        base_llm_config = LLMConfig(**llm_config_dict)
        if not base_llm_config:
            raise ConfigurationError(f"Could not determine LLM configuration for Agent '{agent_name}'.")

        # Handle force_include_history override from workflow
        effective_include_history = agent_config_for_run.include_history
        if force_include_history is not None:
            effective_include_history = force_include_history
            # Also update the agent config to reflect this override
            agent_config_for_run.include_history = force_include_history

        initial_messages: List[Dict[str, Any]] = []
        if effective_include_history and session_id and self._session_manager:
            history = self._session_manager.get_session_history(session_id)
            if history:
                initial_messages.extend(history)

        # Add current user message
        current_user_message = {"role": "user", "content": user_message}
        initial_messages.append(current_user_message)

        # Immediately update the history with the current user message
        # so the agent can reference it as part of the conversation history
        if effective_include_history and session_id and self._session_manager:
            self._session_manager.add_message_to_history(
                session_id=session_id,
                message=current_user_message,
                agent_name=agent_name,
            )

        if system_prompt_override:
            if agent_config_for_run.llm is None:
                agent_config_for_run.llm = LLMConfigOverrides()
            agent_config_for_run.llm.system_prompt = system_prompt_override

        agent_instance = Agent(
            agent_config=agent_config_for_run,
            base_llm_config=base_llm_config,
            host_instance=self._host,
            initial_messages=initial_messages,
            session_id=session_id,
        )
        return agent_instance, dynamically_registered_servers

    # --- Public Execution Methods ---

    async def stream_agent_run(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(f"Facade: Received request to STREAM agent '{agent_name}'")

        # Auto-generate session_id if agent wants history but none provided
        if not session_id:
            # Check if agent has include_history=true
            agent_config_dict = self._config_manager.get_config("agent", agent_name)
            if agent_config_dict:
                agent_config = AgentConfig(**agent_config_dict)
                if agent_config.include_history:
                    session_id = f"agent-{uuid.uuid4().hex[:8]}"
                    logger.info(
                        f"Auto-generated session_id for streaming agent with include_history=true: {session_id}"
                    )

        agent_instance = None
        servers_to_unregister: List[str] = []
        trace: Optional["StatefulTraceClient"] = None
        try:
            # Prepare the agent instance and dynamically register any required servers
            agent_instance, servers_to_unregister = await self._prepare_agent_for_run(
                agent_name, user_message, system_prompt, session_id
            )
            # Create trace if Langfuse is enabled
            if self.langfuse:
                if os.getenv("LANGFUSE_USER_ID"):
                    user_id = os.getenv("LANGFUSE_USER_ID")
                else:
                    user_id = session_id or "anonymous"

                trace = self.langfuse.trace(
                    name=f"Agent: {agent_name} (streaming) - Aurite Runtime",
                    session_id=session_id,  # This groups traces into sessions
                    user_id=user_id,
                    input={"user_message": user_message, "system_prompt": agent_instance.config.system_prompt},
                    metadata={
                        "agent_name": agent_name,
                        "source": "execution-facade",
                    },
                )

            # Pass trace to agent if available
            if trace:
                agent_instance.trace = trace

            logger.info(f"Facade: Streaming conversation for Agent '{agent_name}'...")

            # Yield session_id as the first event
            if session_id:
                yield {"type": "session_info", "data": {"session_id": session_id}}

            async for event in agent_instance.stream_conversation():
                yield event
        except Exception as e:
            error_msg = (
                f"Error during streaming setup or execution for Agent '{agent_name}': {type(e).__name__}: {str(e)}"
            )
            logger.error(f"Facade: {error_msg}")
            yield {"type": "error", "data": {"message": error_msg}}
            # Re-raise to be caught by the final `finally` block for cleanup
            raise AgentExecutionError(error_msg) from e
        finally:
            # Save history at the end of the stream
            if agent_instance and agent_instance.config.include_history and session_id and self._session_manager:
                # This is a streaming run, so we don't have a full result object yet.
                # We save the conversation history for now.
                self._session_manager.save_conversation_history(
                    session_id=session_id,
                    conversation=agent_instance.conversation_history,
                    agent_name=agent_name,
                )
                logger.info(
                    f"Facade: Saved {len(agent_instance.conversation_history)} history turns for agent '{agent_name}', session '{session_id}'."
                )

            # Don't unregister servers - keep them available for future use
            # This allows tools to remain available after agent execution
            if servers_to_unregister:
                logger.debug(
                    f"Keeping {len(servers_to_unregister)} dynamically registered servers active: {servers_to_unregister}"
                )

            # Update trace with output if available
            if self.langfuse and trace and agent_instance:
                # Get the final response from the agent
                final_output = None
                if hasattr(agent_instance, "final_response") and agent_instance.final_response:
                    final_output = agent_instance.final_response.content
                elif hasattr(agent_instance, "conversation_history") and agent_instance.conversation_history:
                    # Get the last assistant message
                    for msg in reversed(agent_instance.conversation_history):
                        if msg.get("role") == "assistant" and msg.get("content"):
                            final_output = msg.get("content")
                            break

                if final_output:
                    trace.update(output={"response": final_output})

            # Flush Langfuse trace if enabled
            if self.langfuse and trace:
                self.langfuse.flush()

    async def run_agent(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        force_include_history: Optional[bool] = None,
        base_session_id: Optional[str] = None,  # New parameter
    ) -> AgentRunResult:
        # --- Session ID Management ---
        agent_config_dict = self._config_manager.get_config("agent", agent_name)
        if not agent_config_dict:
            raise ConfigurationError(f"Agent configuration '{agent_name}' not found.")
        agent_config = AgentConfig(**agent_config_dict)
        effective_include_history = (
            force_include_history if force_include_history is not None else agent_config.include_history
        )

        final_session_id = session_id
        # If a base_session_id is passed from a workflow, use it. Otherwise, determine it.
        final_base_session_id = base_session_id if base_session_id is not None else session_id

        if effective_include_history:
            if final_session_id:
                # Only add prefix if it's not part of a workflow and doesn't already have the prefix
                if not final_session_id.startswith("agent-") and not final_session_id.startswith("workflow-"):
                    final_session_id = f"agent-{final_session_id}"
            else:
                # This is a standalone agent run, so it gets the agent prefix
                final_session_id = f"agent-{uuid.uuid4().hex[:8]}"
                final_base_session_id = final_session_id  # The generated ID is the base
                logger.info(f"Auto-generated session_id for agent '{agent_name}': {final_session_id}")
        # --- End Session ID Management ---

        agent_instance = None
        servers_to_unregister: List[str] = []
        trace: Optional["StatefulTraceClient"] = None
        try:
            # Create trace if Langfuse is enabled
            if self.langfuse:
                trace = self.langfuse.trace(
                    name=f"Agent: {agent_name} - Aurite Runtime",
                    session_id=session_id,  # This groups traces into sessions
                    user_id=session_id or "anonymous",
                    input={"user_message": user_message, "system_prompt": system_prompt},
                    metadata={
                        "agent_name": agent_name,
                        "source": "execution-facade",
                    },
                )

            agent_instance, servers_to_unregister = await self._prepare_agent_for_run(
                agent_name, user_message, system_prompt, final_session_id, force_include_history
            )

            # Pass trace to agent if available
            if trace:
                agent_instance.trace = trace

            logger.info(
                colored(
                    f"Facade: Running conversation for Agent '{agent_name}'...",
                    "blue",
                    attrs=["bold"],
                )
            )
            run_result = await agent_instance.run_conversation()
            logger.info(
                colored(
                    f"Facade: Agent '{agent_name}' conversation finished with status: {run_result.status}.",
                    "blue",
                    attrs=["bold"],
                )
            )

            # Manually set the agent_name on the result, as the agent itself doesn't know its registered name.
            run_result.agent_name = agent_name

            # Save complete execution result regardless of the outcome, as it's valuable for debugging.
            if agent_instance and agent_instance.config.include_history and final_session_id and self._session_manager:
                self._session_manager.save_agent_result(
                    session_id=final_session_id, agent_result=run_result, base_session_id=final_base_session_id
                )
                logger.info(
                    f"Facade: Saved complete execution result for agent '{agent_name}', session '{final_session_id}'."
                )

            return run_result
        except Exception as e:
            error_msg = (
                f"Unexpected error in ExecutionFacade while running Agent '{agent_name}': {type(e).__name__}: {str(e)}"
            )
            logger.error(f"Facade: {error_msg}", exc_info=True)
            raise AgentExecutionError(error_msg) from e
        finally:
            # Don't unregister servers - keep them available for future use
            # This allows tools to remain available after agent execution
            if servers_to_unregister:
                logger.debug(
                    f"Keeping {len(servers_to_unregister)} dynamically registered servers active: {servers_to_unregister}"
                )

    async def run_linear_workflow(
        self,
        workflow_name: str,
        initial_input: Any,
        session_id: Optional[str] = None,
        trace: Optional["StatefulTraceClient"] = None,
    ) -> LinearWorkflowExecutionResult:
        logger.info(f"Facade: Received request to run Linear Workflow '{workflow_name}' with session_id: {session_id}")
        # Flush Langfuse trace if enabled
        if self.langfuse and trace:
            self.langfuse.flush()
        try:
            workflow_config_dict = self._config_manager.get_config("linear_workflow", workflow_name)
            if not workflow_config_dict:
                raise ConfigurationError(f"Linear Workflow '{workflow_name}' not found.")

            from ..config.config_models import WorkflowConfig

            workflow_config = WorkflowConfig(**workflow_config_dict)

            # --- Session ID Management ---
            final_session_id = session_id
            base_session_id = session_id  # Capture the original ID
            if workflow_config.include_history:
                if final_session_id:
                    if not final_session_id.startswith("workflow-"):
                        final_session_id = f"workflow-{final_session_id}"
                else:
                    final_session_id = f"workflow-{uuid.uuid4().hex[:8]}"
                    base_session_id = final_session_id  # The generated ID is the base
                    logger.info(f"Auto-generated session_id for workflow '{workflow_name}': {final_session_id}")
            # --- End Session ID Management ---

            workflow_executor = LinearWorkflowExecutor(
                config=workflow_config,
                facade=self,
            )

            result = await workflow_executor.execute(
                initial_input=initial_input, session_id=final_session_id, base_session_id=base_session_id
            )
            logger.info(f"Facade: Linear Workflow '{workflow_name}' execution finished.")

            # Save the complete workflow execution result if it has a session_id
            if result.session_id and self._session_manager:
                self._session_manager.save_workflow_result(
                    session_id=result.session_id, workflow_result=result, base_session_id=base_session_id
                )
                logger.info(
                    f"Facade: Saved complete workflow execution result for '{workflow_name}', session '{result.session_id}'."
                )

            return result
        except ConfigurationError as e:
            # Re-raise configuration errors directly
            raise e
        except Exception as e:
            error_msg = f"Unexpected error running Linear Workflow '{workflow_name}': {e}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            raise WorkflowExecutionError(error_msg) from e

    async def run_custom_workflow(
        self, workflow_name: str, initial_input: Any, session_id: Optional[str] = None
    ) -> Any:
        logger.info(f"Facade: Received request to run Custom Workflow '{workflow_name}'")
        try:
            workflow_config_dict = self._config_manager.get_config("custom_workflow", workflow_name)
            if not workflow_config_dict:
                raise ConfigurationError(f"Custom Workflow '{workflow_name}' not found.")

            from ..config.config_models import CustomWorkflowConfig

            workflow_config = CustomWorkflowConfig(**workflow_config_dict)

            workflow_executor = CustomWorkflowExecutor(config=workflow_config)

            result = await workflow_executor.execute(initial_input=initial_input, executor=self, session_id=session_id)
            logger.info(f"Facade: Custom Workflow '{workflow_name}' execution finished.")
            return result
        except ConfigurationError as e:
            # Re-raise configuration errors directly
            raise e
        except Exception as e:
            error_msg = f"Unexpected error running Custom Workflow '{workflow_name}': {e}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            raise WorkflowExecutionError(error_msg) from e

    async def get_custom_workflow_input_type(self, workflow_name: str) -> Any:
        logger.info(f"Facade: Received request for input type of Custom Workflow '{workflow_name}'")
        try:
            workflow_config_dict = self._config_manager.get_config("custom_workflow", workflow_name)
            if not workflow_config_dict:
                raise ConfigurationError(f"Custom Workflow '{workflow_name}' not found.")

            from ..config.config_models import CustomWorkflowConfig

            workflow_config = CustomWorkflowConfig(**workflow_config_dict)

            workflow_executor = CustomWorkflowExecutor(config=workflow_config)
            return workflow_executor.get_input_type()
        except ConfigurationError as e:
            raise e
        except Exception as e:
            error_msg = f"Unexpected error getting input type for Custom Workflow '{workflow_name}': {e}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            raise WorkflowExecutionError(error_msg) from e

    async def get_custom_workflow_output_type(self, workflow_name: str) -> Any:
        logger.info(f"Facade: Received request for output type of Custom Workflow '{workflow_name}'")
        try:
            workflow_config_dict = self._config_manager.get_config("custom_workflow", workflow_name)
            if not workflow_config_dict:
                raise ConfigurationError(f"Custom Workflow '{workflow_name}' not found.")

            from ..config.config_models import CustomWorkflowConfig

            workflow_config = CustomWorkflowConfig(**workflow_config_dict)

            workflow_executor = CustomWorkflowExecutor(config=workflow_config)
            return workflow_executor.get_output_type()
        except ConfigurationError as e:
            raise e
        except Exception as e:
            error_msg = f"Unexpected error getting output type for Custom Workflow '{workflow_name}': {e}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            raise WorkflowExecutionError(error_msg) from e

    # --- Pass-through Methods to SessionManager ---

    def get_session_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self._session_manager:
            return self._session_manager.get_session_result(session_id)
        return None

    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        if self._session_manager:
            return self._session_manager.get_session_history(session_id)
        return None

    def get_sessions_list(
        self, agent_name: Optional[str] = None, workflow_name: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        if self._session_manager:
            return self._session_manager.get_sessions_list(
                agent_name=agent_name, workflow_name=workflow_name, limit=limit, offset=offset
            )
        return {"sessions": [], "total": 0, "offset": offset, "limit": limit}

    def delete_session(self, session_id: str) -> bool:
        if self._session_manager:
            return self._session_manager.delete_session(session_id)
        return False

    def get_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        if self._session_manager:
            return self._session_manager.get_session_metadata(session_id)
        return None

    def cleanup_old_sessions(self, days: int = 30, max_sessions: int = 50):
        if self._session_manager:
            self._session_manager.cleanup_old_sessions(days=days, max_sessions=max_sessions)
