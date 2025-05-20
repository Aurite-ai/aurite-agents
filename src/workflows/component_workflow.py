# tests/fixtures/custom_workflows/example_workflow.py
import logging
import json

from pydantic import BaseModel
# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from typing import TYPE_CHECKING, Optional, Any, Literal
# Type hint for ExecutionFacade to avoid circular import
if TYPE_CHECKING:
    from src.execution.facade import ExecutionFacade
    
from src.config.config_models import WorkflowComponent

logger = logging.getLogger(__name__)

class ComponentWorkflowInput(BaseModel):
    workflow: list[WorkflowComponent | str]
    input: Any

class ComponentWorkflow:
    """
    Custom workflow for linear chains of components
    """
    
    def _infer_component_type(self, component_name: str, executor: "ExecutionFacade"):
        """Search through the project's defined components to find the type of a component"""
        
        project_config = executor.get_project_config()
        
        possible_types = []
        if component_name in project_config.agents:
            possible_types.append("agent")
        if component_name in project_config.simple_workflows:
            possible_types.append("simple_workflow")
        if component_name in project_config.custom_workflows:
            possible_types.append("custom_workflow")
            
        if len(possible_types) == 1:
            return possible_types[0]

        if len(possible_types) > 1:
            raise ValueError(f"Component with name {component_name} found in multiple types ({', '.join(possible_types)}). Please specify this step with a 'name' and 'type' to remove ambiguity.")
        
        raise ValueError(f"No components found with name {component_name}")

    async def execute_workflow(
        self, 
        initial_input: Any, 
        executor: "ExecutionFacade",
        session_id: Optional[str] = None,
    ) -> Any:
        """
        Executes the prompt validation workflow.

        Args:
            initial_input: An object with "workflow", a list of components to execute (either strings for their name or objects which each have a "name" and "type"), and "input", the input to give the first of these components
            executor: The Execution Facade

        Returns:
            A dictionary containing the result or an error.
        """
        
        try:
            initial_input = ComponentWorkflowInput.model_validate(
                initial_input, strict=True
            )
            
            # find the type for all components defined with only a name
            for i in range(len(initial_input.workflow)):
                if type(initial_input.workflow[i]) is str:
                    initial_input.workflow[i] = WorkflowComponent(name=initial_input.workflow[i], type=self._infer_component_type(component_name=initial_input.workflow[i], executor=executor))
            
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
                "status": "completed",
                "final_message": current_message
            }
            
            logging.info(f"Component Workflow returning with {return_value}")

            return return_value
        except Exception as e:
            logger.error(
                f"Error within ComponentWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Workflow error: {str(e)}"}
