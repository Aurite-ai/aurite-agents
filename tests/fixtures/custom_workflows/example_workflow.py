# tests/fixtures/custom_workflows/example_workflow.py
import logging
from typing import Any

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
# from src.host.host import MCPHost # No longer needed directly
# from src.agents.agent import Agent # Agent execution handled by facade
from typing import TYPE_CHECKING

# Type hint for ExecutionFacade to avoid circular import
if TYPE_CHECKING:
    from src.execution.facade import ExecutionFacade

logger = logging.getLogger(__name__)


class ExampleCustomWorkflow:
    """
    A simple example custom workflow that uses the ExecutionFacade.
    """

    async def execute_workflow(
        self, initial_input: Any, executor: "ExecutionFacade"
    ) -> Any:
        """
        Executes the example workflow using the provided facade.

        Args:
            initial_input: The input data for the workflow.
            executor: The ExecutionFacade instance to run other components.

        Returns:
            A dictionary containing the result or an error.
        """
        logger.info(f"ExampleCustomWorkflow started with input: {initial_input}")

        # Example: Use the facade to run an agent
        try:
            # Ensure this agent name matches one in your testing_config.json
            agent_name = "Weather Agent"

            # Construct a user message based on the input
            # Use a simpler message for testing facade call
            city = initial_input.get("city", "Unknown City")
            user_message = f"What is the weather in {city}?"
            logger.info(
                f"Calling executor.run_agent for '{agent_name}' with message: '{user_message}'"
            )

            # Use the executor to run the agent
            agent_result = await executor.run_agent(
                agent_name=agent_name, user_message=user_message
            )
            logger.info(f"Agent result received: {agent_result}")

            # Basic extraction - assumes final_response and text content exist
            final_message = "Agent execution failed or returned no text."
            if agent_result and not agent_result.get("error"):
                final_message = "No text content found in agent response."
            if (
                agent_result.get("final_response")
                and agent_result["final_response"].content
            ):
                # Find the first text block
                text_block = next(
                    (
                        block
                        for block in agent_result["final_response"].content
                        if block.type == "text"
                    ),
                    None,
                )
                if text_block:
                    final_message = text_block.text

            logger.info("ExampleCustomWorkflow finished successfully.")
            # Return a slightly different structure to confirm this version ran
            return {
                "status": "completed",  # Changed from 'success' for consistency? Or keep success? Let's use completed.
                "error": None,
                "result": {
                    "status": "success",  # Keep internal success marker
                    "message": f"Example custom workflow executed for {city}.",
                    "input_received": initial_input,
                    "agent_result_text": final_message,
                },
            }

        except KeyError as e:
            # This might now happen in the facade if agent_name is invalid
            logger.error(f"Error running agent '{agent_name}': {e}")
            return {
                "status": "failed",
                "error": f"Failed to run agent '{agent_name}': {e}",
            }
        except Exception as e:
            logger.error(
                f"Error within ExampleCustomWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
