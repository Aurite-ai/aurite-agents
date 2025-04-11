# tests/fixtures/custom_workflows/memory_workflow.py
import logging
from typing import Any

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from src.host.host import MCPHost
from src.agents.agent import Agent

logger = logging.getLogger(__name__)


class MemoryCustomWorkflow:
    def _get_message_from_response(self, agent_result) -> str:
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
        return final_message

    async def execute_workflow(self, initial_input: Any, host_instance: MCPHost) -> Any:
        """
        Executes the workflow.

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
            pref_agent_name = "Preferences Agent"
            pref_agent_config = host_instance.get_agent_config(pref_agent_name)
            pref_agent = Agent(config=pref_agent_config)

            # Construct a user message based on the input
            user_message = f"{initial_input}"

            pref_result = await pref_agent.execute_agent(
                user_message=user_message,
                host_instance=host_instance,
                filter_client_ids=pref_agent_config.client_ids,
            )

            # Basic extraction - assumes final_response and text content exist
            pref_message = self._get_message_from_response(pref_result)
            
            logger.info(f"Result from Preferences Agent: {pref_message}")
            
            mem_agent_name = "Memory Agent"
            mem_agent_config = host_instance.get_agent_config(mem_agent_name)
            mem_agent = Agent(config=mem_agent_config)
            
            mem_result = await mem_agent.execute_agent(
                user_message=f"user_id: default_user\n\n{pref_message}",
                host_instance=host_instance,
                filter_client_ids=mem_agent_config.client_ids,
            )
            
            mem_message = self._get_message_from_response(mem_result)

            logger.info("MemoryWorkflow finished successfully.")
            return_value = {
                "status": "success",
                "input_received": initial_input,
                "agent_result_text": mem_message,
            }
            # Add detailed log before returning
            logger.debug(
                f"MemoryWorkflow returning: type={type(return_value)}, value={return_value}"
            )
            return return_value

        except KeyError as e:
            logger.error(f"Error getting agent config: {e}")
            return {
                "status": "failed",
                "error": "Agent configuration not found.",
            }
        except Exception as e:
            logger.error(
                f"Error within MemoryWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
