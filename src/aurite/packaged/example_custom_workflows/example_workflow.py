import logging
from typing import Any, Optional

from aurite.execution.facade import ExecutionFacade
from aurite.components.agents.agent_models import AgentRunResult


logger = logging.getLogger(__name__)


class ExampleCustomWorkflow:
    """
    A simple example of a custom workflow that demonstrates how to use the
    ExecutionFacade to run a pre-configured agent.
    """

    async def execute_workflow(
        self,
        initial_input: Any,
        executor: "ExecutionFacade",
        session_id: Optional[str] = None,
    ) -> Any:
        """
        Executes a simple workflow that runs a single agent.

        This workflow expects an `initial_input` dictionary with a "city" key,
        e.g., `{"city": "New York"}`. It uses this to query the "Weather Agent".

        Args:
            initial_input: The input data for the workflow.
            executor: The ExecutionFacade instance to run other components.
            session_id: The session ID for the execution.

        Returns:
            The primary text output from the agent, or an error message.
        """
        logger.info(f"ExampleCustomWorkflow started with input: {initial_input}")

        # 1. Define which agent to run and prepare the input.
        agent_name = "Weather Agent"
        if isinstance(initial_input, dict):
            city = initial_input.get("city", "London")
        elif isinstance(initial_input, str):
            city = initial_input or "London"
        else:
            city = "London"
        user_message = f"What is the weather in {city}?"

        logger.info(f"Running agent '{agent_name}' with message: '{user_message}'")

        # 2. Use the executor to run the agent.
        agent_result: AgentRunResult = await executor.run_agent(
            agent_name=agent_name,
            user_message=user_message,
            session_id=session_id,
        )

        # 3. Process and return the result.
        if agent_result.status == "success":
            if agent_result.final_response and agent_result.final_response.content:
                logger.info(
                    f"Workflow finished successfully. Returning: {agent_result.final_response.content}"
                )
                return {
                    "status": "completed",
                    "result": agent_result.final_response.content,
                }
            else:
                logger.error("Agent succeeded but returned no response.")
                return {
                    "status": "failed",
                    "error": "Agent succeeded but returned no response.",
                }
        else:
            logger.error(f"Agent execution failed: {agent_result.error_message}")
            return {"status": "failed", "error": agent_result.error_message}

    def get_input_type(self):
        """Specifies the expected input type for this workflow."""
        return dict

    def get_output_type(self):
        """Specifies the output type of this workflow."""
        return dict
