"""
Executor for Simple Sequential Workflows.
"""

import logging
import json
from typing import Dict, Any, TYPE_CHECKING
from pydantic import BaseModel

# Relative imports assuming this file is in src/workflows/
from ...config.config_models import (
    WorkflowConfig,
    AgentConfig,
    WorkflowComponent,
)
from .workflow_models import SimpleWorkflowExecutionResult, SimpleWorkflowStepResult

# Import LLM client and Facade for type hinting only
# Import AgentExecutionResult for type hinting the result from facade.run_agent()
if TYPE_CHECKING:
    from ...execution.facade import ExecutionFacade
    from ..agents.agent_models import AgentExecutionResult  # Added import

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
        agent_configs: Dict[
            str, AgentConfig
        ],  # This is passed by Facade from current_project
        facade: "ExecutionFacade",
    ):
        """
        Initializes the SimpleWorkflowExecutor.

        Args:
            config: The configuration for the specific workflow to execute.
            agent_configs: A dictionary containing all available agent configurations
                           from the current project, keyed by agent name.
                           (Used by the facade when it runs agents for this workflow).
            facade: The ExecutionFacade instance, used to run agents.
        """
        if not isinstance(config, WorkflowConfig):
            raise TypeError("config must be an instance of WorkflowConfig")
        if not isinstance(agent_configs, dict):
            raise TypeError("agent_configs must be a dictionary")
        if not facade:
            raise ValueError("ExecutionFacade instance is required.")

        self.config = config
        # _agent_configs is not strictly needed by SimpleWorkflowExecutor itself if facade handles agent lookup,
        # but keeping it for now as it was passed by the updated facade.
        # If facade.run_agent can fully resolve agents using its own _current_project.agent_configs,
        # this could potentially be removed too. For now, it's harmless.
        self._agent_configs = agent_configs
        self.facade = facade
        logger.debug(
            f"SimpleWorkflowExecutor initialized for workflow: {self.config.name}"
        )

    async def execute(self, initial_input: str) -> SimpleWorkflowExecutionResult:
        """
        Executes the configured simple workflow sequentially.

        Args:
            initial_input: The initial input message for the first agent in the sequence.

        Returns:
            A SimpleWorkflowExecutionResult object containing the final status,
            step-by-step results, the final output, and any error message.
        """
        workflow_name = self.config.name
        logger.info(f"Executing simple workflow: {workflow_name}")
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

                            agent_result_model: "AgentExecutionResult" = (
                                await self.facade.run_agent(
                                    agent_name=component.name,
                                    user_message=str(current_message),
                                )
                            )

                            if agent_result_model.has_error:
                                raise Exception(
                                    f"Agent '{component.name}' reported an error: {agent_result_model.error}"
                                )

                            component_output = agent_result_model
                            current_message = agent_result_model.primary_text or ""

                        case "simple_workflow":
                            workflow_result = await self.facade.run_simple_workflow(
                                workflow_name=component.name,
                                initial_input=current_message,
                            )
                            if workflow_result.error:
                                raise Exception(
                                    f"Nested workflow '{component.name}' failed: {workflow_result.error}"
                                )

                            component_output = workflow_result
                            current_message = workflow_result.final_output

                        case "custom_workflow":
                            input_type = (
                                await self.facade.get_custom_workflow_input_type(
                                    workflow_name=component.name
                                )
                            )
                            if isinstance(current_message, str) and input_type is dict:
                                current_message = json.loads(current_message)
                            elif (
                                isinstance(current_message, dict) and input_type is str
                            ):
                                current_message = json.dumps(current_message)

                            custom_workflow_output = (
                                await self.facade.run_custom_workflow(
                                    workflow_name=component.name,
                                    initial_input=current_message,
                                )
                            )
                            component_output = custom_workflow_output
                            current_message = custom_workflow_output

                        case _:
                            raise ValueError(
                                f"Component type not recognized: {component.type}"
                            )

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

        project_config = self.facade.get_project_config()

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
            raise ValueError(
                f"Component with name {component_name} found in multiple types ({', '.join(possible_types)}). Please specify this step with a 'name' and 'type' to remove ambiguity."
            )

        raise ValueError(f"No components found with name {component_name}")
