"""
Executor for Simple Sequential Workflows.
"""

import json
import logging
import uuid
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel

# Relative imports assuming this file is in src/workflows/
from ...config.config_models import (
    WorkflowComponent,
    WorkflowConfig,
)
from ..agents.agent_models import AgentRunResult
from .workflow_models import SimpleWorkflowExecutionResult, SimpleWorkflowStepResult

# Import LLM client and Facade for type hinting only
if TYPE_CHECKING:
    from ...execution.facade import ExecutionFacade

logger = logging.getLogger(__name__)


class ComponentWorkflowInput(BaseModel):
    workflow: list[WorkflowComponent | str]
    input: Any


class SimpleWorkflowExecutor:
    """
    Executes a simple sequential workflow defined by a WorkflowConfig.
    """

    def __init__(
        self,
        config: WorkflowConfig,
        facade: "ExecutionFacade",
    ):
        """
        Initializes the SimpleWorkflowExecutor.

        Args:
            config: The configuration for the specific workflow to execute.
            facade: The ExecutionFacade instance, used to run agents.
        """
        if not isinstance(config, WorkflowConfig):
            raise TypeError("config must be an instance of WorkflowConfig")
        if not facade:
            raise ValueError("ExecutionFacade instance is required.")

        self.config = config
        self.facade = facade
        logger.debug(f"SimpleWorkflowExecutor initialized for workflow: {self.config.name}")

    async def execute(self, initial_input: str, session_id: Optional[str] = None) -> SimpleWorkflowExecutionResult:
        """
        Executes the configured simple workflow sequentially.

        Args:
            initial_input: The initial input message for the first agent in the sequence.
            session_id: Optional session ID to use for conversation history tracking.

        Returns:
            A SimpleWorkflowExecutionResult object containing the final status,
            step-by-step results, the final output, and any error message.
        """
        workflow_name = self.config.name
        
        # Auto-generate session_id if workflow wants history but none provided
        if self.config.include_history and not session_id:
            session_id = f"workflow-{workflow_name}-{uuid.uuid4().hex[:8]}"
            logger.info(f"Auto-generated session_id for workflow with include_history=true: {session_id}")
        
        logger.info(f"Executing simple workflow: {workflow_name} with session_id: {session_id}")
        
        # Save a parent session for the workflow itself
        if self.config.include_history and session_id and self.facade._cache_manager:
            self.facade._cache_manager.save_history(
                session_id=session_id,
                conversation=[],  # No conversation, just metadata
                workflow_name=workflow_name,
            )

        step_results: list[SimpleWorkflowStepResult] = []
        current_message: Any = initial_input

        try:
            # Ensure all steps are WorkflowComponent objects
            processed_workflow: list[WorkflowComponent] = []
            for step in self.config.steps:
                if isinstance(step, str):
                    processed_workflow.append(
                        WorkflowComponent(
                            name=step,
                            type=self._infer_component_type(component_name=step),
                        )
                    )
                else:
                    processed_workflow.append(step)

            for component in processed_workflow:
                component_output: Any = None
                try:
                    logging.info(
                        f"Component Workflow: {component.name} ({component.type}) operating with input: {str(current_message)[:200]}..."
                    )
                    match component.type.lower():
                        case "agent":
                            if isinstance(current_message, dict):
                                current_message = json.dumps(current_message)

                            # Generate a unique session ID for each agent step, linked to the workflow session
                            agent_session_id = None
                            force_include_history = self.config.include_history

                            if self.config.include_history and session_id:
                                # Create a unique, traceable session ID for this specific agent run
                                agent_session_id = f"{session_id}-{len(step_results)}-{component.name.replace(' ', '')}"
                            
                            # The facade's run_agent now returns a structured AgentRunResult
                            agent_run_result: AgentRunResult = await self.facade.run_agent(
                                agent_name=component.name,
                                user_message=str(current_message),
                                session_id=agent_session_id,
                                force_include_history=force_include_history,
                                workflow_name=workflow_name,
                                workflow_session_id=session_id,  # Pass the parent workflow session ID
                            )

                            # Check the status of the agent run
                            if agent_run_result.status != "success":
                                error_detail = (
                                    agent_run_result.error_message
                                    or f"Agent finished with status: {agent_run_result.status}"
                                )
                                raise Exception(
                                    f"Agent '{component.name}' failed to execute successfully. Details: {error_detail}"
                                )

                            if agent_run_result.final_response is None:
                                raise Exception(f"Agent '{component.name}' succeeded but produced no response.")

                            # The output for the step is the full result object for better logging
                            component_output = agent_run_result.model_dump()
                            # The input for the next step is the agent's final text response
                            current_message = agent_run_result.final_response.content

                        case "simple_workflow":
                            workflow_result = await self.facade.run_simple_workflow(
                                workflow_name=component.name,
                                initial_input=current_message,
                                session_id=session_id,
                            )
                            if workflow_result.error:
                                raise Exception(f"Nested workflow '{component.name}' failed: {workflow_result.error}")

                            component_output = workflow_result
                            current_message = workflow_result.final_output

                        case "custom_workflow":
                            input_type = await self.facade.get_custom_workflow_input_type(workflow_name=component.name)
                            if isinstance(current_message, str) and input_type is dict:
                                current_message = json.loads(current_message)
                            elif isinstance(current_message, dict) and input_type is str:
                                current_message = json.dumps(current_message)

                            custom_workflow_output = await self.facade.run_custom_workflow(
                                workflow_name=component.name,
                                initial_input=current_message,
                                session_id=session_id,
                            )
                            component_output = custom_workflow_output
                            current_message = custom_workflow_output

                        case _:
                            raise ValueError(f"Component type not recognized: {component.type}")

                    step_results.append(
                        SimpleWorkflowStepResult(
                            step_name=component.name,
                            step_type=component.type,
                            result=component_output,
                        )
                    )

                except Exception as e:
                    logger.error(
                        f"Error processing component '{component.name}': {e}",
                        exc_info=True,
                    )
                    return SimpleWorkflowExecutionResult(
                        workflow_name=workflow_name,
                        status="failed",
                        step_results=step_results,
                        final_output=current_message,
                        error=f"Error processing component '{component.name}': {str(e)}",
                    )

            return SimpleWorkflowExecutionResult(
                workflow_name=workflow_name,
                status="completed",
                step_results=step_results,
                final_output=current_message,
                error=None,
            )

        except Exception as e:
            logger.error(f"Error within simple workflow execution: {e}", exc_info=True)
            return SimpleWorkflowExecutionResult(
                workflow_name=workflow_name,
                status="failed",
                step_results=step_results,
                final_output=current_message,
                error=f"Workflow setup error: {str(e)}",
            )

    def _infer_component_type(self, component_name: str):
        """Search through the project's defined components to find the type of a component"""
        possible_types = []
        if self.facade._config_manager.get_config("agent", component_name):
            possible_types.append("agent")
        if self.facade._config_manager.get_config("simple_workflow", component_name):
            possible_types.append("simple_workflow")
        if self.facade._config_manager.get_config("custom_workflow", component_name):
            possible_types.append("custom_workflow")

        if len(possible_types) == 1:
            return possible_types[0]

        if len(possible_types) > 1:
            raise ValueError(
                f"Component with name {component_name} found in multiple types ({', '.join(possible_types)}). Please specify this step with a 'name' and 'type' to remove ambiguity."
            )

        raise ValueError(f"No components found with name {component_name}")
