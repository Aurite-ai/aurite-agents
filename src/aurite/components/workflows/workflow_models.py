"""
Pydantic models for Workflow execution inputs and outputs.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union
from ..agents.agent_models import AgentExecutionResult


class SimpleWorkflowStepResult(BaseModel):
    """
    Represents the output of a single step in a Simple Workflow.
    This model can hold the result from an Agent, a nested Simple Workflow,
    or a Custom Workflow.
    """

    step_name: str = Field(
        description="The name of the component that was executed in this step."
    )
    step_type: str = Field(
        description="The type of the component (e.g., 'agent', 'simple_workflow')."
    )

    # The 'result' field will hold the specific output model for the component type
    # We use a Union to allow for different types of results.
    # We will need to define SimpleWorkflowExecutionResult shortly.
    result: Union["AgentExecutionResult", "SimpleWorkflowExecutionResult", Any] = Field(
        description="The execution result from the step's component."
    )


class SimpleWorkflowExecutionResult(BaseModel):
    """
    Standardized Pydantic model for the output of a Simple Workflow execution.
    """

    workflow_name: str = Field(description="The name of the executed workflow.")
    status: str = Field(
        description="The final status of the workflow (e.g., 'completed', 'failed')."
    )

    # A list of step results to provide a full execution trace
    step_results: List[SimpleWorkflowStepResult] = Field(
        default_factory=list,
        description="A list containing the result of each step in the workflow.",
    )

    # The final output from the last step in the workflow
    final_output: Optional[Any] = Field(
        None, description="The final output from the last step of the workflow."
    )

    error: Optional[str] = Field(
        None, description="An error message if the workflow execution failed."
    )

    @property
    def final_message(self) -> Optional[str]:
        """
        A convenience property to extract the primary text if the final output
        was from an agent, for easy display.
        """
        if isinstance(self.final_output, AgentExecutionResult):
            return self.final_output.primary_text
        elif isinstance(self.final_output, str):
            return self.final_output
        return None  # Or a sensible default


# This is needed to allow the recursive type hint in SimpleWorkflowStepResult
SimpleWorkflowStepResult.model_rebuild()
