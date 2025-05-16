# src/aurite/packaged/example_custom_workflow_src/example_workflow.py
import logging
from typing import Any, Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from aurite.execution.facade import ExecutionFacade

logger = logging.getLogger(__name__)


class ExampleCustomWorkflow:
    """
    An example custom workflow demonstrating how to use the ExecutionFacade
    to run other Aurite components like agents and simple workflows.
    """

    async def execute_workflow(
        self,
        initial_input: Dict[str, Any],
        executor: "ExecutionFacade",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the example workflow.

        Args:
            initial_input: Input data for the workflow. Expected to have a "city" key
                           for the weather agent, and "plan_topic" for the simple workflow.
            executor: The ExecutionFacade instance to run other components.
            session_id: Optional session ID for context/history tracking.

        Returns:
            A dictionary containing the results of the executed components.
        """
        logger.info(f"MyPackagedCustomWorkflow started with input: {initial_input}")
        results = {}

        # 1. Run an Agent
        city = initial_input.get(
            "city", "San Francisco"
        )  # Default city if not provided
        weather_agent_name = "Weather Agent"
        weather_query = f"What is the weather in {city}?"

        logger.info(
            f"Running agent '{weather_agent_name}' with query: '{weather_query}'"
        )
        try:
            agent_result = await executor.run_agent(
                agent_name=weather_agent_name,
                user_message=weather_query,
                session_id=session_id,  # Optional session ID
            )
            results["weather_agent_output"] = agent_result
            logger.info(f"Agent '{weather_agent_name}' completed.")
        except Exception as e:
            logger.error(
                f"Error running agent '{weather_agent_name}': {e}", exc_info=True
            )
            results["weather_agent_output"] = {"error": str(e)}

        # 2. Run a Simple Workflow
        simple_workflow_name = "Weather Planning Workflow"
        # The "Weather Planning Workflow" is designed to take the output of "Weather Agent"
        # For this example, we'll use a static input or derive from agent_result if successful.

        plan_input_data = f"The weather in {city} is pleasant. "  # Default input
        if results.get("weather_agent_output") and not results[
            "weather_agent_output"
        ].get("error"):
            try:
                # Attempt to extract text from agent's final response
                content_list = (
                    results["weather_agent_output"]
                    .get("final_response", {})
                    .get("content", [])
                )
                text_block = next(
                    (item for item in content_list if item.get("type") == "text"), None
                )
                if text_block:
                    plan_input_data = text_block.get("text", plan_input_data)
            except Exception:
                logger.warning(
                    "Could not extract text from weather agent for simple workflow input, using default."
                )

        logger.info(
            f"Running simple workflow '{simple_workflow_name}' with input: '{plan_input_data}'"
        )
        try:
            simple_workflow_result = await executor.run_simple_workflow(
                workflow_name=simple_workflow_name,
                initial_input=plan_input_data,  # Simple workflows often take string input
            )
            results["simple_workflow_output"] = simple_workflow_result
            logger.info(f"Simple workflow '{simple_workflow_name}' completed.")
        except Exception as e:
            logger.error(
                f"Error running simple workflow '{simple_workflow_name}': {e}",
                exc_info=True,
            )
            results["simple_workflow_output"] = {"error": str(e)}

        # (Optional) Example of running another Custom Workflow (if one was defined and suitable for chaining)
        # For now, we'll skip this to keep the example focused.
        # chained_custom_workflow_name = "AnotherExampleWorkflow"
        # logger.info(f"Running chained custom workflow '{chained_custom_workflow_name}'")
        # try:
        #     custom_workflow_result = await executor.run_custom_workflow(
        #         workflow_name=chained_custom_workflow_name,
        #         initial_input={"data_from_previous_step": results.get("simple_workflow_output")},
        #         session_id=session_id,
        #     )
        #     results["chained_custom_workflow_output"] = custom_workflow_result
        # except Exception as e:
        #     logger.error(f"Error running chained custom workflow '{chained_custom_workflow_name}': {e}", exc_info=True)
        #     results["chained_custom_workflow_output"] = {"error": str(e)}

        logger.info("MyPackagedCustomWorkflow finished.")
        return {
            "status": "completed",
            "initial_input_received": initial_input,
            "results": results,
        }
