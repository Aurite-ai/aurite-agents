"""
Executor for Simple Sequential Workflows.
"""

import logging
from typing import Dict, Any, Optional

# Relative imports assuming this file is in src/workflows/
from ..host.models import WorkflowConfig, AgentConfig
from ..host.host import MCPHost
from ..agents.agent import Agent

logger = logging.getLogger(__name__)


class SimpleWorkflowExecutor:
    """
    Executes a simple sequential workflow defined by a WorkflowConfig.
    """

    def __init__(
        self,
        config: WorkflowConfig,
        agent_configs: Dict[str, AgentConfig],
        host_instance: MCPHost,
    ):
        """
        Initializes the SimpleWorkflowExecutor.

        Args:
            config: The configuration for the specific workflow to execute.
            agent_configs: A dictionary containing all available agent configurations,
                           keyed by agent name. Needed to look up configs for steps.
            host_instance: The initialized MCPHost instance.
        """
        if not isinstance(config, WorkflowConfig):
            raise TypeError("config must be an instance of WorkflowConfig")
        if not isinstance(agent_configs, dict):
            raise TypeError("agent_configs must be a dictionary")
        if not isinstance(host_instance, MCPHost):
            raise TypeError("host_instance must be an instance of MCPHost")

        self.config = config
        self._agent_configs = agent_configs
        self._host = host_instance
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

        if not self._host:
            # This check might be redundant if __init__ validates, but good practice
            logger.error(
                f"MCPHost instance not available for workflow '{workflow_name}'."
            )
            # Should ideally not happen if initialized correctly
            raise RuntimeError(
                f"MCPHost instance not available for workflow '{workflow_name}'."
            )

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
                logger.info(
                    f"Executing workflow '{workflow_name}' step {step_num}: Agent '{agent_name}'"
                )

                try:
                    # 1. Retrieve AgentConfig for the current step
                    agent_config = self._agent_configs[agent_name]
                    logger.debug(
                        f"Step {step_num}: Found AgentConfig for '{agent_name}'"
                    )

                    # 2. Instantiate Agent
                    agent = Agent(config=agent_config)
                    logger.debug(f"Step {step_num}: Instantiated Agent '{agent_name}'")

                    # 3. Execute the agent step
                    # Note: We pass the host instance stored in the executor
                    result = await agent.execute_agent(
                        user_message=current_message, host_instance=self._host
                    )

                    # 4. Process Agent Result
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

                    # 5. Extract Output for Next Step (Handle potential missing text/content)
                    try:
                        if (
                            result.get("final_response")
                            and result["final_response"].content
                        ):
                            text_content = next(
                                (
                                    block.text
                                    for block in result["final_response"].content
                                    if block.type == "text"
                                ),
                                None,
                            )
                            if text_content is not None:
                                current_message = text_content
                                logger.debug(
                                    f"Step {step_num}: Output message for next step: '{current_message[:100]}...'"
                                )
                            else:
                                # Agent responded, but no text block found. What should happen?
                                # Option 1: Fail the workflow
                                # error_message = f"Agent '{agent_name}' (step {step_num}) response content has no text block."
                                # logger.error(error_message)
                                # break
                                # Option 2: Pass an empty string or placeholder? Let's pass empty string for now.
                                current_message = ""
                                logger.warning(
                                    f"Agent '{agent_name}' (step {step_num}) response content has no text block. Passing empty string to next step."
                                )
                        else:
                            # Agent result structure is missing expected parts
                            error_message = f"Agent '{agent_name}' (step {step_num}) returned unexpected result structure (missing final_response or content)."
                            logger.error(error_message)
                            break

                    except (AttributeError, TypeError) as e:
                        # Catch errors if the result structure is malformed
                        error_message = f"Error processing agent '{agent_name}' (step {step_num}) response structure: {e}"
                        logger.error(error_message, exc_info=True)
                        break

                except KeyError:
                    # This occurs if agent_name is not found in self._agent_configs
                    error_message = f"Configuration error in workflow '{workflow_name}': Agent '{agent_name}' (step {step_num}) not found in provided agent configurations."
                    logger.error(error_message)
                    # Stop workflow execution
                    break
                except Exception as agent_exec_e:
                    # Catch other unexpected errors from Agent instantiation or execution
                    error_message = f"Unexpected error during agent '{agent_name}' (step {step_num}) execution within workflow '{workflow_name}': {agent_exec_e}"
                    logger.error(error_message, exc_info=True)
                    # Stop workflow execution
                    break

            # Determine final status after loop finishes or breaks
            if error_message is None:
                final_status = "completed"
                logger.info(f"Workflow '{workflow_name}' completed successfully.")
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
