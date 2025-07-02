"""
Provides a unified facade for executing Agents, Simple Workflows, and Custom Workflows.
"""

import logging
from typing import Any, Dict, Optional, List, AsyncGenerator

from termcolor import colored

from ..components.llm.providers.litellm_client import LiteLLMClient
from ..components.agents.agent import Agent
from ..components.agents.agent_models import AgentRunResult
from ..components.workflows.simple_workflow import SimpleWorkflowExecutor
from ..components.workflows.workflow_models import SimpleWorkflowExecutionResult
from ..components.workflows.custom_workflow import CustomWorkflowExecutor
from ..host.host import MCPHost
from ..storage.db_manager import StorageManager
from ..config.config_models import ProjectConfig

logger = logging.getLogger(__name__)


class ExecutionFacade:
    """
    A facade that simplifies the execution of different component types
    (Agents, Simple Workflows, Custom Workflows) managed by the Aurite.
    """

    def __init__(
        self,
        host_instance: "MCPHost",
        current_project: "ProjectConfig",
        storage_manager: Optional["StorageManager"] = None,
    ):
        if not host_instance:
            raise ValueError("MCPHost instance is required for ExecutionFacade.")
        if not current_project:
            raise ValueError("Current ProjectConfig is required for ExecutionFacade.")

        self._host = host_instance
        self._current_project = current_project
        self._storage_manager = storage_manager
        self._llm_client_cache: Dict[str, "LiteLLMClient"] = {}
        logger.debug(
            f"ExecutionFacade initialized with project '{current_project.name}' (StorageManager {'present' if storage_manager else 'absent'})."
        )

    # --- Private Helper Methods ---

    async def _prepare_agent_for_run(
        self,
        agent_name: str,
        user_message: str,
        system_prompt_override: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Agent:
        if not self._current_project.agents:
            raise KeyError("Agent configurations not found in project.")

        agent_config_list = [
            a for a in self._current_project.agents if a.name == agent_name
        ]
        if not agent_config_list:
            raise KeyError(f"Agent configuration '{agent_name}' not found.")
        original_agent_config = agent_config_list[0]

        agent_config_for_run = original_agent_config

        # TODO: Dynamic tool selection needs to be re-evaluated in light of the new model.
        # if original_agent_config.auto:
        #     logger.info(
        #         f"Agent '{agent_name}' has 'auto=True'. Attempting dynamic tool selection."
        #     )
        #     tool_selector_client = self._get_llm_client(
        #         original_agent_config.llm_config_id
        #     )
        #     system_prompt_for_tool_selector = tool_selector_client.system_prompt

        #     selected_client_ids = await select_tools_for_agent(
        #         agent_config=original_agent_config,
        #         user_message=user_message,
        #         system_prompt_for_agent=system_prompt_for_tool_selector,
        #         current_project=self._current_project,
        #         llm_client_cache=self._llm_client_cache,
        #     )
        #     if selected_client_ids is not None:
        #         agent_config_for_run = copy.deepcopy(original_agent_config)
        #         agent_config_for_run.mcp_servers = selected_client_ids
        #         logger.info(
        #             f"Dynamically selected mcp_servers for agent '{agent_name}': {selected_client_ids}"
        #         )
        #     else:
        #         logger.warning(
        #             f"Dynamic tool selection failed for agent '{agent_name}'. Falling back to static mcp_servers: {original_agent_config.mcp_servers or 'None'}."
        #         )

        # The Agent is now responsible for its own LLM configuration and client.
        # The Facade's role is to gather the necessary configs.
        if not agent_config_for_run.llm_config_id:
            raise ValueError(f"Agent '{agent_name}' must have an llm_config_id.")

        llm_config_list = [
            llm_config
            for llm_config in self._current_project.llms
            if llm_config.name == agent_config_for_run.llm_config_id
        ]
        if not llm_config_list:
            raise ValueError(
                f"LLM configuration '{agent_config_for_run.llm_config_id}' not found in project."
            )
        base_llm_config = llm_config_list[0]

        initial_messages: List[Dict[str, Any]] = []
        if (
            agent_config_for_run.include_history
            and self._storage_manager
            and session_id
        ):
            history = self._storage_manager.load_history(agent_name, session_id)
            if history:
                initial_messages.extend(history)

        initial_messages.append({"role": "user", "content": user_message})

        # The system_prompt_override is now handled inside the Agent's constructor
        if system_prompt_override:
            if agent_config_for_run.llm is None:
                from ..config.config_models import LLMConfigOverrides

                agent_config_for_run.llm = LLMConfigOverrides()
            agent_config_for_run.llm.system_prompt = system_prompt_override

        return Agent(
            agent_config=agent_config_for_run,
            base_llm_config=base_llm_config,
            host_instance=self._host,
            initial_messages=initial_messages,
        )

    # --- Public Execution Methods ---

    async def stream_agent_run(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(f"Facade: Received request to STREAM agent '{agent_name}'")
        try:
            agent_instance = await self._prepare_agent_for_run(
                agent_name, user_message, system_prompt, session_id
            )
            logger.info(f"Facade: Streaming conversation for Agent '{agent_name}'...")
            async for event in agent_instance.stream_conversation():
                yield event
        except Exception as e:
            error_msg = f"Error during streaming setup or execution for Agent '{agent_name}': {type(e).__name__}: {str(e)}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            yield {"type": "error", "data": {"message": error_msg}}

    async def run_agent(
        self,
        agent_name: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AgentRunResult:
        try:
            agent_instance = await self._prepare_agent_for_run(
                agent_name, user_message, system_prompt, session_id
            )

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
            if (
                agent_instance.config.include_history
                and self._storage_manager
                and session_id
            ):
                try:
                    self._storage_manager.save_full_history(
                        agent_name=agent_name,
                        session_id=session_id,
                        conversation=run_result.conversation_history,
                    )
                    logger.info(
                        f"Facade: Saved {len(run_result.conversation_history)} history turns for agent '{agent_name}', session '{session_id}'."
                    )
                except Exception as e:
                    logger.error(
                        f"Facade: Failed to save history for agent '{agent_name}', session '{session_id}': {e}",
                        exc_info=True,
                    )

            return run_result
        except Exception as e:
            error_msg = f"Unexpected error in ExecutionFacade while running Agent '{agent_name}': {type(e).__name__}: {str(e)}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            # Return a consistent error format
            return AgentRunResult(
                status="error",
                final_response=None,
                conversation_history=[],  # History might not be available if setup failed
                error_message=error_msg,
            )

    async def run_simple_workflow(
        self, workflow_name: str, initial_input: Any
    ) -> SimpleWorkflowExecutionResult:
        logger.info(
            f"Facade: Received request to run Simple Workflow '{workflow_name}'"
        )
        try:
            if not self._current_project.simple_workflows:
                raise KeyError("No simple workflows found in the project.")

            workflow_config_list = [
                w
                for w in self._current_project.simple_workflows
                if w.name == workflow_name
            ]
            if not workflow_config_list:
                raise KeyError(f"Simple Workflow '{workflow_name}' not found.")
            workflow_config = workflow_config_list[0]

            # The executor now expects a dictionary of agents.
            agents_dict = {a.name: a for a in self._current_project.agents if a.name}
            workflow_executor = SimpleWorkflowExecutor(
                config=workflow_config,
                agent_configs=agents_dict,
                facade=self,
            )

            result = await workflow_executor.execute(initial_input=initial_input)
            logger.info(
                f"Facade: Simple Workflow '{workflow_name}' execution finished."
            )
            return result
        except (KeyError, ValueError) as e:
            error_msg = f"Configuration or setup error for Simple Workflow '{workflow_name}': {e}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return SimpleWorkflowExecutionResult(
                workflow_name=workflow_name,
                status="failed",
                final_output=None,
                error=error_msg,
            )
        except Exception as e:
            error_msg = (
                f"Unexpected error running Simple Workflow '{workflow_name}': {e}"
            )
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return SimpleWorkflowExecutionResult(
                workflow_name=workflow_name,
                status="failed",
                final_output=None,
                error=error_msg,
            )

    async def run_custom_workflow(
        self, workflow_name: str, initial_input: Any, session_id: Optional[str] = None
    ) -> Any:
        logger.info(
            f"Facade: Received request to run Custom Workflow '{workflow_name}'"
        )
        try:
            if not self._current_project.custom_workflows:
                raise KeyError("No custom workflows found in the project.")

            workflow_config_list = [
                w
                for w in self._current_project.custom_workflows
                if w.name == workflow_name
            ]
            if not workflow_config_list:
                raise KeyError(f"Custom Workflow '{workflow_name}' not found.")
            workflow_config = workflow_config_list[0]

            workflow_executor = CustomWorkflowExecutor(config=workflow_config)

            result = await workflow_executor.execute(
                initial_input=initial_input, executor=self, session_id=session_id
            )
            logger.info(
                f"Facade: Custom Workflow '{workflow_name}' execution finished."
            )
            return result
        except (KeyError, ValueError, ImportError) as e:
            error_msg = f"Configuration or setup error for Custom Workflow '{workflow_name}': {e}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return {"status": "failed", "error": error_msg}
        except Exception as e:
            error_msg = (
                f"Unexpected error running Custom Workflow '{workflow_name}': {e}"
            )
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return {"status": "failed", "error": error_msg}

    def get_project_config(self) -> "ProjectConfig":
        return self._current_project

    async def get_custom_workflow_input_type(self, workflow_name: str) -> Any:
        logger.info(
            f"Facade: Received request for input type of Custom Workflow '{workflow_name}'"
        )
        try:
            if not self._current_project.custom_workflows:
                raise KeyError("No custom workflows found in the project.")

            workflow_config_list = [
                w
                for w in self._current_project.custom_workflows
                if w.name == workflow_name
            ]
            if not workflow_config_list:
                raise KeyError(f"Custom Workflow '{workflow_name}' not found.")
            workflow_config = workflow_config_list[0]

            workflow_executor = CustomWorkflowExecutor(config=workflow_config)
            return workflow_executor.get_input_type()
        except (KeyError, ValueError, ImportError) as e:
            error_msg = (
                f"Could not get input type for Custom Workflow '{workflow_name}': {e}"
            )
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return {"status": "failed", "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error getting input type for Custom Workflow '{workflow_name}': {e}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return {"status": "failed", "error": error_msg}

    async def get_custom_workflow_output_type(self, workflow_name: str) -> Any:
        logger.info(
            f"Facade: Received request for output type of Custom Workflow '{workflow_name}'"
        )
        try:
            if not self._current_project.custom_workflows:
                raise KeyError("No custom workflows found in the project.")

            workflow_config_list = [
                w
                for w in self._current_project.custom_workflows
                if w.name == workflow_name
            ]
            if not workflow_config_list:
                raise KeyError(f"Custom Workflow '{workflow_name}' not found.")
            workflow_config = workflow_config_list[0]

            workflow_executor = CustomWorkflowExecutor(config=workflow_config)
            return workflow_executor.get_output_type()
        except (KeyError, ValueError, ImportError) as e:
            error_msg = (
                f"Could not get output type for Custom Workflow '{workflow_name}': {e}"
            )
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return {"status": "failed", "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error getting output type for Custom Workflow '{workflow_name}': {e}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return {"status": "failed", "error": error_msg}
