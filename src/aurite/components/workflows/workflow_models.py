"""
Pydantic models for Workflow execution inputs and outputs.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ...execution.facade import ExecutionFacade
    from ..agents.agent_models import AgentRunResult


class SimpleWorkflowStepResult(BaseModel):
    """
    Represents the output of a single step in a Simple Workflow.
    This model can hold the result from an Agent, a nested Simple Workflow,
    or a Custom Workflow.
    """

    step_name: str = Field(description="The name of the component that was executed in this step.")
    step_type: str = Field(description="The type of the component (e.g., 'agent', 'simple_workflow').")

    # The 'result' field will hold the specific output model for the component type.
    # Agent results are now stored as dicts from model_dump().
    result: Union[Dict[str, Any], "SimpleWorkflowExecutionResult", Any] = Field(
        description="The execution result from the step's component."
    )


class SimpleWorkflowExecutionResult(BaseModel):
    """
    Standardized Pydantic model for the output of a Simple Workflow execution.
    """

    workflow_name: str = Field(description="The name of the executed workflow.")
    status: str = Field(description="The final status of the workflow (e.g., 'completed', 'failed').")

    # A list of step results to provide a full execution trace
    step_results: List[SimpleWorkflowStepResult] = Field(
        default_factory=list,
        description="A list containing the result of each step in the workflow.",
    )

    # The final output from the last step in the workflow
    final_output: Optional[Any] = Field(None, description="The final output from the last step of the workflow.")

    error: Optional[str] = Field(None, description="An error message if the workflow execution failed.")

    @property
    def final_message(self) -> Optional[str]:
        """
        A convenience property to extract the primary text if the final output
        was from an agent, for easy display.
        """
        if isinstance(self.final_output, str):
            return self.final_output
        # The final output from an agent step is now just the content string.
        # If the whole workflow's final_output is the result of an agent step,
        # it will be a string.
        return str(self.final_output) if self.final_output is not None else None


# This is needed to allow the recursive type hint in SimpleWorkflowStepResult
SimpleWorkflowStepResult.model_rebuild()


class BaseCustomWorkflow:
    """
    Abstract base class for custom Python-based workflows.

    Users should subclass this and implement the `execute` method.
    The `run_agent` method is provided to allow the workflow to easily
    call agents managed by the framework.
    """

    def __init__(self):
        self._executor: Optional["ExecutionFacade"] = None

    @property
    def executor(self) -> "ExecutionFacade":
        if self._executor is None:
            raise RuntimeError("Executor not set. This workflow must be run via the Aurite ExecutionFacade.")
        return self._executor

    def set_executor(self, executor: "ExecutionFacade"):
        """
        Called by the framework to provide the workflow with an execution facade.
        """
        self._executor = executor

    async def run_agent(
        self,
        agent_name: str,
        user_message: str,
        session_id: Optional[str] = None,
    ) -> "AgentRunResult":
        """
        A helper method for the workflow to execute an agent.
        """
        return await self.executor.run_agent(
            agent_name=agent_name,
            user_message=user_message,
            session_id=session_id,
        )

    async def run(self, initial_input: Any) -> Any:
        """
        The main entry point for the workflow's logic.
        This method must be implemented by the subclass.
        """
        raise NotImplementedError
