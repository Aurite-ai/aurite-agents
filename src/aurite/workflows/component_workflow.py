# tests/fixtures/custom_workflows/example_workflow.py
import logging
import json

from pydantic import BaseModel
# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from typing import TYPE_CHECKING, Optional, Any
# Type hint for ExecutionFacade to avoid circular import
if TYPE_CHECKING:
    from src.execution.facade import ExecutionFacade

logger = logging.getLogger(__name__)

class Component(BaseModel):
    name: str
    type: str

class ComponentWorkflowInput(BaseModel):
    workflow: list[Component]
    input: Any

class ComponentWorkflow:
    """
    Custom workflow for linear chains of components
    """

    async def execute_workflow(
        self, 
        initial_input: Any, 
        executor: "ExecutionFacade",
        session_id: Optional[str] = None,
    ) -> Any:
        """
        Executes the prompt validation workflow.

        Args:
            initial_input: An object with "workflow", a list of components to execute which each have a "name" and "type", and "input", the input to give the first of these components
            executor: The Execution Facade

        Returns:
            A dictionary containing the result or an error.
        """
        
        try:
            initial_input = ComponentWorkflowInput.model_validate(
                initial_input, strict=True
            )
            
            current_message = initial_input.input
            
            for component in initial_input.workflow:
                try:
                    logging.info(f"Component Workflow: {component.name} ({component.type}) operating with input: {current_message}")
                    match component.type.lower():
                        case "agent":
                            if type(current_message) is dict:
                                current_message = json.dumps(current_message)
                            
                            component_output = await executor.run_agent(agent_name=component.name, user_message=current_message)
                            
                            current_message = component_output.get("final_response", {}).get("content", [{}])[0].get("text", "")
                        case "simple_workflow":
                            component_output = await executor.run_simple_workflow(workflow_name=component.name, initial_input=current_message)
                            
                            current_message = component_output.get("final_message", "")
                        case "custom_workflow":
                            if type(current_message) is str:
                                current_message = json.loads(current_message)
                            
                            component_output = await executor.run_custom_workflow(workflow_name=component.name, initial_input=current_message)
                            
                            current_message = component_output
                        case _:
                            raise ValueError(f"Component type not recognized: {component.type}")
                except Exception as e:
                    return {"status": "failed", "error": f"Error occured while processing component '{component.name}': {str(e)}"} 
            
            return_value = {
                "status": "success",
                "final_message": current_message
            }
            
            logging.info(f"Component Workflow returning with {return_value}")

            return return_value
        except Exception as e:
            logger.error(
                f"Error within ComponentWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
