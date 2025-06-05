# tests/fixtures/custom_workflows/example_workflow.py
import logging
from typing import Any, Optional  # Added Optional

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
# from aurite.host.host import MCPHost # No longer needed directly
# from aurite.components.agents.agent import Agent # Agent execution handled by facade
from typing import TYPE_CHECKING

# Type hint for ExecutionFacade to avoid circular import
if TYPE_CHECKING:
    from aurite.execution.facade import ExecutionFacade

logger = logging.getLogger(__name__)


class ExampleCustomWorkflow:
    """
    A simple example custom workflow that uses the ExecutionFacade.
    """

    async def execute_workflow(
        self,
        initial_input: Any,
        executor: "ExecutionFacade",
        session_id: Optional[str] = None,  # Added session_id
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
                agent_name=agent_name,
                user_message=user_message,
                session_id=session_id,  # Pass session_id
            )
            logger.info(
                f"Agent result received (type: {type(agent_result)}): {agent_result}"
            )

            # More robust extraction and error handling
            final_message = "Agent execution failed or returned unexpected format."  # Default error message
            agent_error = None
            workflow_status = "failed"  # Default to failed unless explicitly successful

            agent_error_str: Optional[str] = None
            final_text_content = "Agent execution failed or returned unexpected format."
            workflow_status = "failed"  # Default to failed

            # agent_result is an AgentExecutionResult object
            if agent_result.error:
                agent_error_str = agent_result.error
                final_text_content = f"Agent execution failed: {agent_error_str}"
                logger.error(final_text_content)
                # workflow_status remains "failed"
            elif agent_result.final_response and agent_result.final_response.content:
                final_response_obj = agent_result.final_response
                text_block_found = False
                for block in final_response_obj.content:
                    if block.type == "text" and block.text is not None:
                        final_text_content = block.text
                        text_block_found = True
                        workflow_status = "completed"  # Success!
                        logger.info("Successfully extracted text from agent response.")
                        break
                if not text_block_found:
                    final_text_content = (
                        "No text block found in agent response content."
                    )
                    logger.warning(final_text_content)
                    # Consider this success as the agent ran, but didn't return text as expected by this workflow
                    workflow_status = "completed"  # Or "failed" if text is strictly required by workflow logic
            else:
                final_text_content = "Agent result missing final_response or content."
                logger.warning(final_text_content)
                # workflow_status remains "failed"

            # Log final status before returning
            if workflow_status == "completed":
                logger.info(
                    f"ExampleCustomWorkflow finished with status: {workflow_status}"
                )
            else:
                logger.error(
                    f"ExampleCustomWorkflow finished with status: {workflow_status}. Message: {final_text_content}"
                )

            # Return structure - the outer 'status' reflects the workflow's success in running
            # The inner 'result' contains details including the extracted text or error message.
            return {
                "status": workflow_status,  # Outer status reflects workflow completion
                "error": agent_error_str
                if workflow_status == "failed"
                else None,  # Use the extracted error string
                "result": {
                    "status": "success"
                    if workflow_status == "completed"
                    else "failed",  # Inner status reflects outcome
                    "message": f"Example custom workflow executed for {city}.",
                    "input_received": initial_input,
                    "agent_result_text": final_text_content,  # Contains extracted text or error info
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

    def get_input_type(self):
        return dict

    def get_output_type(self):
        return dict
