"""
Executor for Simple Sequential Workflows.
"""

import logging
from typing import Dict, Any, TYPE_CHECKING  # Added TYPE_CHECKING

# Relative imports assuming this file is in src/workflows/
from ..config.config_models import WorkflowConfig, AgentConfig  # Updated import path

# Import LLM client and Facade for type hinting only
if TYPE_CHECKING:
    from ..execution.facade import ExecutionFacade  # Added Facade import

logger = logging.getLogger(__name__)


class SimpleWorkflowExecutor:
    """
    Executes a simple sequential workflow defined by a WorkflowConfig.
    """

    def __init__(
        self,
        config: WorkflowConfig,
        agent_configs: Dict[
            str, AgentConfig
        ],  # This is passed by Facade from current_project
        facade: "ExecutionFacade",
    ):
        """
        Initializes the SimpleWorkflowExecutor.

        Args:
            config: The configuration for the specific workflow to execute.
            agent_configs: A dictionary containing all available agent configurations
                           from the current project, keyed by agent name.
                           (Used by the facade when it runs agents for this workflow).
            facade: The ExecutionFacade instance, used to run agents.
        """
        if not isinstance(config, WorkflowConfig):
            raise TypeError("config must be an instance of WorkflowConfig")
        if not isinstance(agent_configs, dict):
            raise TypeError("agent_configs must be a dictionary")
        if not facade:
            raise ValueError("ExecutionFacade instance is required.")

        self.config = config
        # _agent_configs is not strictly needed by SimpleWorkflowExecutor itself if facade handles agent lookup,
        # but keeping it for now as it was passed by the updated facade.
        # If facade.run_agent can fully resolve agents using its own _current_project.agent_configs,
        # this could potentially be removed too. For now, it's harmless.
        self._agent_configs = agent_configs
        self.facade = facade
        logger.debug(
            f"SimpleWorkflowExecutor initialized for workflow: {self.config.name}"
        )

    async def execute(self, initial_input: str) -> Dict[str, Any]:
        """
        Executes the configured simple workflow sequentially.

        Args:
            initial_input: The initial input message for the first agent in the sequence.

        Returns:
            A dictionary containing the final status, the final message from the last agent,
            and any error message encountered.
        """
        workflow_name = self.config.name
        logger.info(f"Executing simple workflow: {workflow_name}")

        current_message = initial_input
        final_status = "failed"  # Default status
        error_message = None

        try:
            if not self.config.steps:
                logger.warning(f"Workflow '{workflow_name}' has no steps to execute.")
                return {
                    "workflow_name": workflow_name,
                    "status": "completed_empty",
                    "final_message": current_message,
                    "error": None,
                }

            # Loop through steps (agents)
            for i, agent_name in enumerate(self.config.steps):
                step_num = i + 1
                logger.debug(  # INFO -> DEBUG
                    f"Executing workflow '{workflow_name}' step {step_num}: Agent '{agent_name}'"
                )

                try:
                    # 1. Execute Agent via Facade
                    # Facade handles config lookup, LLM client resolution, agent instantiation, and execution.
                    # TODO: Consider passing session_id if workflows need state persistence
                    result_dict: Dict[str, Any] = await self.facade.run_agent(
                        agent_name=agent_name,
                        user_message=current_message,
                        # system_prompt=None, # Use agent's default
                        # session_id=None, # Add session management if needed
                    )

                    # 2. Process Agent Result (Dictionary)
                    agent_error = result_dict.get("error")
                    if agent_error:
                        error_message = f"Agent '{agent_name}' (step {step_num}) failed: {agent_error}"
                        logger.error(error_message)
                        break  # Stop workflow execution

                    final_response_dict = result_dict.get("final_response")
                    if not final_response_dict:
                        error_message = f"Agent '{agent_name}' (step {step_num}) did not return a final response structure."
                        logger.error(error_message)
                        break  # Stop workflow execution

                    # 3. Extract Output for Next Step (from Dictionary)
                    final_content_blocks = final_response_dict.get("content", [])
                    if not final_content_blocks:
                        error_message = f"Agent '{agent_name}' (step {step_num}) final response has no content."
                        logger.error(error_message)
                        break  # Stop workflow execution

                    text_content = next(
                        (
                            block.get("text")
                            for block in final_content_blocks
                            if isinstance(block, dict) and block.get("type") == "text"
                        ),
                        None,
                    )

                    if text_content is not None:
                        current_message = text_content
                        logger.debug(
                            f"Step {step_num}: Output message for next step: '{current_message[:100]}...'"
                        )
                    else:
                        # Agent responded, but no text block found.
                        current_message = ""  # Pass empty string
                        logger.warning(
                            f"Agent '{agent_name}' (step {step_num}) response content has no text block. Passing empty string to next step."
                        )

                except KeyError:
                    # This occurs if agent_name is not found in self._agent_configs (should be caught by facade now, but keep as fallback)
                    error_message = f"Configuration error in workflow '{workflow_name}': Agent '{agent_name}' (step {step_num}) not found."
                    logger.error(error_message)
                    break  # Stop workflow execution
                except Exception as agent_exec_e:
                    # Catch other unexpected errors during facade call or result processing
                    error_message = f"Unexpected error during agent '{agent_name}' (step {step_num}) execution via facade within workflow '{workflow_name}': {agent_exec_e}"
                    logger.error(error_message, exc_info=True)
                    break  # Stop workflow execution

            # Determine final status after loop finishes or breaks
            if error_message is None:
                final_status = "completed"
                logger.info(
                    f"Workflow '{workflow_name}' completed successfully."
                )  # Keep final success as INFO
            else:
                # Ensure status remains 'failed' if loop broke due to error
                final_status = "failed"
                logger.error(
                    f"Workflow '{workflow_name}' failed due to error: {error_message}"
                )

        except Exception as e:
            # Catch any other unexpected errors during workflow orchestration within the executor
            logger.error(
                f"Unexpected error during workflow '{workflow_name}' execution in SimpleWorkflowExecutor: {e}",
                exc_info=True,
            )
            error_message = (
                error_message or f"Internal error during workflow execution: {str(e)}"
            )
            final_status = "failed"

        # Return final result
        return {
            "workflow_name": workflow_name,
            "status": final_status,
            "final_message": current_message if final_status == "completed" else None,
            "error": error_message,
        }
