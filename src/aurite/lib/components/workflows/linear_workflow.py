"""
Executor for Linear Sequential Workflows.
"""

import json
import logging
import uuid
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel

from ...models.api.responses import AgentRunResult, LinearWorkflowExecutionResult, LinearWorkflowStepResult

# Relative imports assuming this file is in src/workflows/
from ...models.config.components import WorkflowComponent, WorkflowConfig

# Import LLM client and Facade for type hinting only
if TYPE_CHECKING:
    from ....execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)


class ComponentWorkflowInput(BaseModel):
    workflow: list[WorkflowComponent | str]
    input: Any


class LinearWorkflowExecutor:
    """
    Executes a linear sequential workflow defined by a WorkflowConfig.
    """

    def __init__(
        self,
        config: WorkflowConfig,
        engine: "AuriteEngine",
    ):
        """
        Initializes the LinearWorkflowExecutor.

        Args:
            config: The configuration for the specific workflow to execute.
            engine: The AuriteEngine instance, used to run agents.
        """
        if not isinstance(config, WorkflowConfig):
            raise TypeError("config must be an instance of WorkflowConfig")
        if not engine:
            raise ValueError("AuriteEngine instance is required.")

        self.config = config
        self.engine = engine
        logger.debug(f"LinearWorkflowExecutor initialized for workflow: {self.config.name}")

    async def execute(
        self,
        initial_input: str,
        session_id: Optional[str] = None,
        base_session_id: Optional[str] = None,
        force_logging: Optional[bool] = None,
    ) -> LinearWorkflowExecutionResult:
        """
        Executes the configured linear workflow sequentially.

        Args:
            initial_input: The initial input message for the first agent in the sequence.
            session_id: Optional session ID to use for conversation history tracking.
            base_session_id: The original, user-provided session ID for the workflow.

        Returns:
            A LinearWorkflowExecutionResult object containing the final status,
            step-by-step results, the final output, and any error message.
        """
        workflow_name = self.config.name

        if not session_id and self.config.include_history:
            session_id = f"workflow-{uuid.uuid4().hex[:8]}"
            logger.info(f"Auto-generated session_id for workflow '{workflow_name}': {session_id}")

        logger.info(f"Executing linear workflow: '{workflow_name}' with session_id: {session_id}")

        step_results: list[LinearWorkflowStepResult] = []
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

            for step_index, component in enumerate(processed_workflow):
                component_output: Any = None
                try:
                    logging.info(
                        f"Component Workflow: {component.name} ({component.type}) operating with input: {str(current_message)[:200]}..."
                    )
                    match component.type.lower():
                        case "agent":
                            if isinstance(current_message, dict):
                                current_message = json.dumps(current_message)

                            # The engine is now responsible for handling session ID generation for agent steps.
                            agent_run_result: AgentRunResult = await self.engine.run_agent(
                                agent_name=component.name,
                                user_message=str(current_message),
                                session_id=f"{session_id}-{step_index}" if session_id else None,
                                force_include_history=self.config.include_history,
                                base_session_id=base_session_id,
                                force_logging=force_logging,
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

                        case "linear_workflow":
                            workflow_result = await self.engine.run_linear_workflow(
                                workflow_name=component.name,
                                initial_input=current_message,
                                session_id=session_id,
                                force_logging=force_logging,
                            )
                            if workflow_result.error:
                                raise Exception(f"Nested workflow '{component.name}' failed: {workflow_result.error}")

                            component_output = workflow_result
                            current_message = workflow_result.final_output

                        case "custom_workflow":
                            input_type = await self.engine.get_custom_workflow_input_type(workflow_name=component.name)
                            if isinstance(current_message, str) and input_type is dict:
                                current_message = json.loads(current_message)
                            elif isinstance(current_message, dict) and input_type is str:
                                current_message = json.dumps(current_message)

                            custom_workflow_output = await self.engine.run_custom_workflow(
                                workflow_name=component.name,
                                initial_input=current_message,
                                session_id=session_id,
                            )
                            component_output = custom_workflow_output
                            current_message = custom_workflow_output

                        case _:
                            raise ValueError(f"Component type not recognized: {component.type}")

                    step_results.append(
                        LinearWorkflowStepResult(
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
                    return LinearWorkflowExecutionResult(
                        workflow_name=workflow_name,
                        status="failed",
                        step_results=step_results,
                        final_output=current_message,
                        error=f"Error processing component '{component.name}': {str(e)}",
                        session_id=session_id,
                    )

            return LinearWorkflowExecutionResult(
                workflow_name=workflow_name,
                status="completed",
                step_results=step_results,
                final_output=current_message,
                error=None,
                session_id=session_id,
            )

        except Exception as e:
            logger.error(f"Error within linear workflow execution: {e}", exc_info=True)
            return LinearWorkflowExecutionResult(
                workflow_name=workflow_name,
                status="failed",
                step_results=step_results,
                final_output=current_message,
                error=f"Workflow setup error: {str(e)}",
                session_id=session_id,
            )

    def _infer_component_type(self, component_name: str):
        """Search through the project's defined components to find the type of a component"""
        possible_types = []
        if self.engine._config_manager.get_config("agent", component_name):
            possible_types.append("agent")
        if self.engine._config_manager.get_config("linear_workflow", component_name):
            possible_types.append("linear_workflow")
        if self.engine._config_manager.get_config("custom_workflow", component_name):
            possible_types.append("custom_workflow")

        if len(possible_types) == 1:
            return possible_types[0]

        if len(possible_types) > 1:
            raise ValueError(
                f"Component with name {component_name} found in multiple types ({', '.join(possible_types)}). Please specify this step with a 'name' and 'type' to remove ambiguity."
            )

        raise ValueError(f"No components found with name {component_name}")
