"""
Provides a unified facade for executing Agents, Simple Workflows, and Custom Workflows.
"""

import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional, Tuple

from langfuse import Langfuse
from termcolor import colored

from ..components.agents.agent import Agent
from ..components.agents.agent_models import AgentRunResult
from ..components.llm.providers.litellm_client import LiteLLMClient
from ..components.workflows.custom_workflow import CustomWorkflowExecutor
from ..components.workflows.simple_workflow import SimpleWorkflowExecutor
from ..components.workflows.workflow_models import SimpleWorkflowExecutionResult
from ..config.config_manager import ConfigManager
from ..config.config_models import (
    AgentConfig,
    ClientConfig,
    LLMConfig,
    LLMConfigOverrides,
)
from ..errors import (
    AgentExecutionError,
    ConfigurationError,
    WorkflowExecutionError,
)
from ..host.host import MCPHost
from ..storage.cache_manager import CacheManager
from ..storage.db_manager import StorageManager

if TYPE_CHECKING:
    from langfuse.client import StatefulTraceClient

logger = logging.getLogger(__name__)


class ExecutionFacade:
    """
    A facade that simplifies the execution of different component types
    (Agents, Simple Workflows, Custom Workflows) managed by the Aurite.
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
        self._cache_manager = cache_manager
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

        initial_messages: List[Dict[str, Any]] = []
        if agent_config_for_run.include_history and session_id:
            history = None
            if self._storage_manager:
                history = self._storage_manager.load_history(agent_name, session_id)
            elif self._cache_manager:
                history = self._cache_manager.get_history(session_id)

            if history:
                initial_messages.extend(history)

        # Add current user message
        current_user_message = {"role": "user", "content": user_message}
        initial_messages.append(current_user_message)

        # Immediately update the cache with the current user message
        # so the agent can reference it as part of the conversation history
        if agent_config_for_run.include_history and session_id and self._cache_manager:
            # Get the existing history again to make sure we have the latest
            existing_history = self._cache_manager.get_history(session_id) or []
            # Add only the current user message to the existing history
            updated_history = existing_history + [current_user_message]
            self._cache_manager.save_history(session_id, updated_history, agent_name)

        if system_prompt_override:
            if agent_config_for_run.llm is None:
                agent_config_for_run.llm = LLMConfigOverrides()
            agent_config_for_run.llm.system_prompt = system_prompt_override

        agent_instance = Agent(
            agent_config=agent_config_for_run,
            base_llm_config=base_llm_config,
            host_instance=self._host,
            initial_messages=initial_messages,
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
        agent_instance = None
        servers_to_unregister: List[str] = []
        trace: Optional["StatefulTraceClient"] = None
        try:
            # Create trace if Langfuse is enabled
            if self.langfuse:
                trace = self.langfuse.trace(
                    name=f"agent-run-{agent_name}",
                    session_id=session_id,
                    user_id=session_id or "anonymous",
                    metadata={
                        "agent_name": agent_name,
                        "source": "execution-facade",
                    },
                )

            agent_instance, servers_to_unregister = await self._prepare_agent_for_run(
                agent_name, user_message, system_prompt, session_id
            )

            # Pass trace to agent if available
            if trace:
                agent_instance.trace = trace

            logger.info(f"Facade: Streaming conversation for Agent '{agent_name}'...")
            async for event in agent_instance.stream_conversation():
                yield event
        except Exception as e:
            error_msg = (
                f"Error during streaming setup or execution for Agent '{agent_name}': {type(e).__name__}: {str(e)}"
            )
            logger.error(f"Facade: {error_msg}", exc_info=True)
            yield {"type": "error", "data": {"message": error_msg}}
            # Re-raise to be caught by the final `finally` block for cleanup
            raise AgentExecutionError(error_msg) from e
        finally:
            # Save history at the end of the stream
            if agent_instance and agent_instance.config.include_history and session_id:
                if self._storage_manager:
                    try:
                        self._storage_manager.save_full_history(
                            agent_name=agent_name,
                            session_id=session_id,
                            conversation=agent_instance.conversation_history,
                        )
                        logger.info(
                            f"Facade: Saved {len(agent_instance.conversation_history)} history turns for agent '{agent_name}', session '{session_id}' to database."
                        )
                    except Exception as e:
                        logger.error(
                            f"Facade: Failed to save history for agent '{agent_name}', session '{session_id}' to database: {e}",
                            exc_info=True,
                        )
                elif self._cache_manager:
                    self._cache_manager.save_history(session_id, agent_instance.conversation_history, agent_name)
                    logger.info(
                        f"Facade: Saved {len(agent_instance.conversation_history)} history turns for agent '{agent_name}', session '{session_id}' to file-based cache."
                    )

            # Don't unregister servers - keep them available for future use
            # This allows tools to remain available after agent execution
            if servers_to_unregister:
                logger.debug(
                    f"Keeping {len(servers_to_unregister)} dynamically registered servers active: {servers_to_unregister}"
                )

            # Flush Langfuse trace if enabled
            if self.langfuse and trace:
                self.langfuse.flush()

    async def run_agent(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AgentRunResult:
        agent_instance = None
        servers_to_unregister: List[str] = []
        trace: Optional["StatefulTraceClient"] = None
        try:
            # Create trace if Langfuse is enabled
            if self.langfuse:
                trace = self.langfuse.trace(
                    name=f"agent-run-{agent_name}",
                    session_id=session_id,
                    user_id=session_id or "anonymous",
                    metadata={
                        "agent_name": agent_name,
                        "source": "execution-facade",
                    },
                )

            agent_instance, servers_to_unregister = await self._prepare_agent_for_run(
                agent_name, user_message, system_prompt, session_id
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

            # Save history regardless of the outcome, as it's valuable for debugging.
            if agent_instance and agent_instance.config.include_history and session_id:
                if self._storage_manager:
                    try:
                        self._storage_manager.save_full_history(
                            agent_name=agent_name,
                            session_id=session_id,
                            conversation=run_result.conversation_history,
                        )
                        logger.info(
                            f"Facade: Saved {len(run_result.conversation_history)} history turns for agent '{agent_name}', session '{session_id}' to database."
                        )
                    except Exception as e:
                        logger.error(
                            f"Facade: Failed to save history for agent '{agent_name}', session '{session_id}' to database: {e}",
                            exc_info=True,
                        )
                elif self._cache_manager:
                    self._cache_manager.save_history(session_id, run_result.conversation_history, agent_name)
                    logger.info(
                        f"Facade: Saved {len(run_result.conversation_history)} history turns for agent '{agent_name}', session '{session_id}' to file-based cache."
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

            # Flush Langfuse trace if enabled
            if self.langfuse and trace:
                self.langfuse.flush()

    async def run_simple_workflow(self, workflow_name: str, initial_input: Any) -> SimpleWorkflowExecutionResult:
        logger.info(f"Facade: Received request to run Simple Workflow '{workflow_name}'")
        try:
            workflow_config_dict = self._config_manager.get_config("simple_workflow", workflow_name)
            if not workflow_config_dict:
                raise ConfigurationError(f"Simple Workflow '{workflow_name}' not found.")

            from ..config.config_models import WorkflowConfig

            workflow_config = WorkflowConfig(**workflow_config_dict)

            workflow_executor = SimpleWorkflowExecutor(
                config=workflow_config,
                facade=self,
            )

            result = await workflow_executor.execute(initial_input=initial_input)
            logger.info(f"Facade: Simple Workflow '{workflow_name}' execution finished.")
            return result
        except ConfigurationError as e:
            # Re-raise configuration errors directly
            raise e
        except Exception as e:
            error_msg = f"Unexpected error running Simple Workflow '{workflow_name}': {e}"
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

    # --- History Management Methods ---

    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get history for a specific session regardless of agent.
        Delegates to StorageManager if available, otherwise CacheManager.
        """
        if self._storage_manager:
            return self._storage_manager.get_session_history(session_id)
        elif self._cache_manager:
            return self._cache_manager.get_history(session_id)
        else:
            logger.warning("No storage backend available for session history")
            return None

    def get_sessions_list(self, agent_name: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Get list of sessions with optional filtering by agent.
        Returns paginated results.
        """

        if agent_name:
            # Get sessions for specific agent
            if self._storage_manager:
                sessions = self._storage_manager.get_sessions_by_agent(agent_name, limit=limit + offset)
            elif self._cache_manager:
                sessions = self._cache_manager.get_sessions_by_agent(agent_name, limit=limit + offset)
            else:
                sessions = []
        else:
            # Get all sessions - need to aggregate from all agents
            if self._storage_manager:
                # For StorageManager, we'd need a new method to get all sessions
                # For now, return empty as this is not implemented
                logger.warning("Getting all sessions not yet implemented for StorageManager")
                sessions = []
            elif self._cache_manager:
                # For CacheManager, get all sessions from metadata
                sessions = []
                for session_id, metadata in self._cache_manager._metadata_cache.items():
                    sessions.append({"session_id": session_id, **metadata})
                # Sort by last_updated descending
                sessions.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
            else:
                sessions = []

        # Apply pagination
        total = len(sessions)
        paginated_sessions = sessions[offset : offset + limit] if sessions else []

        return {"sessions": paginated_sessions, "total": total, "offset": offset, "limit": limit}

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session's history.
        Returns True if deleted, False if not found.
        """
        if self._storage_manager:
            return self._storage_manager.delete_session(session_id)
        elif self._cache_manager:
            return self._cache_manager.delete_session(session_id)
        else:
            logger.warning("No storage backend available for session deletion")
            return False

    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a session.
        """
        if self._storage_manager:
            return self._storage_manager.get_session_metadata(session_id)
        elif self._cache_manager:
            return self._cache_manager.get_session_metadata(session_id)
        else:
            logger.warning("No storage backend available for session metadata")
            return None

    def cleanup_old_sessions(self, days: int = 30, max_sessions: int = 50):
        """
        Clean up old sessions based on retention policy.
        """
        if self._storage_manager:
            self._storage_manager.cleanup_old_sessions(days=days, max_sessions=max_sessions)
        if self._cache_manager:
            self._cache_manager.cleanup_old_sessions(days=days, max_sessions=max_sessions)
