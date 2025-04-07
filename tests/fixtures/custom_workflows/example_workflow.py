# tests/fixtures/custom_workflows/example_workflow.py
import logging
from typing import Any

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from src.host.host import MCPHost
from src.agents.agent import Agent

logger = logging.getLogger(__name__)


class ExampleCustomWorkflow:
    """
    A simple example custom workflow that uses an agent.
    """

    async def execute_workflow(self, initial_input: Any, host_instance: MCPHost) -> Any:
        """
        Executes the example workflow.

        Args:
            initial_input: The input data for the workflow.
            host_instance: The MCPHost instance to interact with agents/tools.

        Returns:
            A dictionary containing the result or an error.
        """
        logger.info(f"ExampleCustomWorkflow started with input: {initial_input}")

        # Example: Use an agent defined in config
        try:
            # Ensure this agent name matches one in your testing_config.json
            agent_name = "Weather Agent"
            agent_config = host_instance.get_agent_config(agent_name)
            agent = Agent(config=agent_config)

            # Construct a user message based on the input
            user_message = f"Get weather based on input: {initial_input}"

            agent_result = await agent.execute_agent(
                user_message=user_message,
                host_instance=host_instance,
                filter_client_ids=agent_config.client_ids,
            )

            # Basic extraction - assumes final_response and text content exist
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
            return {
                "status": "success",
                "input_received": initial_input,
                "agent_result_text": final_message,
            }

        except KeyError as e:
            logger.error(f"Error getting agent config '{agent_name}': {e}")
            return {
                "status": "failed",
                "error": f"Agent configuration '{agent_name}' not found.",
            }
        except Exception as e:
            logger.error(
                f"Error within ExampleCustomWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
