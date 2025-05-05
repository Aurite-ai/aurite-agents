# tests/fixtures/custom_workflows/example_workflow.py
import logging
from typing import Any, Optional # Added Optional

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
        self, initial_input: Any, executor: "ExecutionFacade", session_id: Optional[str] = None # Added session_id
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

            # Use the executor to run the agent, passing the session_id
            agent_result = await executor.run_agent(
                agent_name=agent_name, user_message=user_message, session_id=session_id # Pass session_id
            )
            logger.info(
                f"Agent result received (type: {type(agent_result)}): {agent_result}"
            )

            # More robust extraction and error handling
            final_message = "Agent execution failed or returned unexpected format."  # Default error message
            agent_error = None
            workflow_status = "failed"  # Default to failed unless explicitly successful

            if isinstance(agent_result, dict):
                agent_error = agent_result.get("error")
                if not agent_error:
                    # Attempt extraction only if no agent error
                    final_message = "No text content found in agent response."  # Default if no error but no text found
                    try:
                        # Check structure carefully before accessing attributes
                        if (
                            agent_result.get("final_response")
                            and hasattr(agent_result["final_response"], "content")
                            and isinstance(agent_result["final_response"].content, list)
                        ):
                            # Find the first text block safely
                            text_block = next(
                                (
                                    block
                                    for block in agent_result["final_response"].content
                                    if hasattr(block, "type")
                                    and block.type == "text"
                                    and hasattr(block, "text")
                                ),
                                None,
                            )
                            if text_block:
                                final_message = text_block.text
                                workflow_status = (
                                    "completed"  # Mark as completed only if text found
                                )
                                logger.info(
                                    "Successfully extracted text from agent response."
                                )
                            else:
                                logger.warning(
                                    "No text block found in agent response content."
                                )
                                # Keep workflow_status as failed if no text? Or completed? Let's mark completed but message indicates no text.
                                workflow_status = "completed"
                        else:
                            logger.warning(
                                "Agent result missing expected final_response or content structure."
                            )
                            # Keep workflow_status as failed
                    except Exception as extraction_err:
                        # Catch potential errors during extraction itself
                        logger.error(
                            f"Error extracting text from agent result: {extraction_err}",
                            exc_info=True,
                        )
                        final_message = (
                            f"Error processing agent response: {extraction_err}"
                        )
                        # Keep workflow_status as failed
                else:
                    # Agent returned an error
                    final_message = f"Agent execution failed: {agent_error}"
                    logger.error(final_message)
                    # Keep workflow_status as failed
            else:
                # agent_result was not a dict
                logger.error(
                    f"Agent returned unexpected result format: {type(agent_result)}"
                )
                # Keep workflow_status as failed and final_message as default

            # Log final status before returning
            if workflow_status == "completed":
                logger.info("ExampleCustomWorkflow finished successfully.")
            else:
                logger.error(
                    f"ExampleCustomWorkflow finished with status: {workflow_status}. Message: {final_message}"
                )

            # --- DEBUG LOGGING ---
            logger.debug(f"Final determined workflow_status: {workflow_status}")
            logger.debug(f"Final determined agent_error: {agent_error}")
            logger.debug(f"Final determined final_message: {final_message}")
            # --- END DEBUG LOGGING ---

            # Return structure based on workflow_status
            return {
                "status": workflow_status,
                "error": agent_error
                if workflow_status == "failed"
                else None,  # Return agent error if workflow failed due to it
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
