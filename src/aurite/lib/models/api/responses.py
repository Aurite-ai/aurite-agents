from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from openai.types.chat import ChatCompletionMessage
from pydantic import BaseModel, Field


class AgentRunResult(BaseModel):
    """
    Standardized Pydantic model for the output of an Agent's conversation run.
    """

    status: Literal["success", "error", "max_iterations_reached"] = Field(
        description="The final status of the agent run."
    )
    final_response: Optional[ChatCompletionMessage] = Field(
        None,
        description="The final message from the assistant, if the run was successful.",
    )
    conversation_history: List[Dict[str, Any]] = Field(
        description="The complete conversation history as a list of dictionaries, compliant with OpenAI's message format."
    )
    error_message: Optional[str] = Field(None, description="An error message if the agent execution failed.")
    session_id: Optional[str] = Field(None, description="The session ID used for this agent run.")
    agent_name: Optional[str] = Field(None, description="The name of the agent that was run.")
    exception: Optional[Any] = Field(None, description="The exception if the agent execution failed.")

    @property
    def primary_text(self) -> Optional[str]:
        """
        Returns the primary text content from the final response, if available.
        """
        if self.final_response and self.final_response.content:
            return self.final_response.content
        return None

    @property
    def has_error(self) -> bool:
        """Checks if the run resulted in an error."""
        return self.status == "error"


class LinearWorkflowStepResult(BaseModel):
    """
    Represents the output of a single step in a Linear Workflow.
    This model can hold the result from an Agent, a nested Linear Workflow,
    or a Custom Workflow.
    """

    step_name: str = Field(description="The name of the component that was executed in this step.")
    step_type: str = Field(description="The type of the component (e.g., 'agent', 'linear_workflow').")

    # The 'result' field will hold the specific output model for the component type.
    # Agent results are now stored as dicts from model_dump().
    result: Union[Dict[str, Any], "LinearWorkflowExecutionResult", Any] = Field(
        description="The execution result from the step's component."
    )


class LinearWorkflowExecutionResult(BaseModel):
    """
    Standardized Pydantic model for the output of a Linear Workflow execution.
    """

    workflow_name: str = Field(description="The name of the executed workflow.")
    status: str = Field(description="The final status of the workflow (e.g., 'completed', 'failed').")

    # A list of step results to provide a full execution trace
    step_results: List[LinearWorkflowStepResult] = Field(
        default_factory=list,
        description="A list containing the result of each step in the workflow.",
    )

    # The final output from the last step in the workflow
    final_output: Optional[Any] = Field(None, description="The final output from the last step of the workflow.")

    error: Optional[str] = Field(None, description="An error message if the workflow execution failed.")

    session_id: Optional[str] = Field(None, description="The session ID used for this workflow run.")

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


# This is needed to allow the recursive type hint in LinearWorkflowStepResult
LinearWorkflowStepResult.model_rebuild()

# -- Session and Execution History Response Models --


class SessionMetadata(BaseModel):
    session_id: str
    name: str  # Name of the agent or workflow
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
    message_count: Optional[int] = None
    is_workflow: bool = False  # Indicates if this is a workflow session
    # Now stores a mapping of session_id -> agent_name
    agents_involved: Optional[Dict[str, str]] = None
    base_session_id: Optional[str] = None


class SessionListResponse(BaseModel):
    sessions: List[SessionMetadata]
    total: int
    offset: int
    limit: int


class ExecutionHistoryResponse(BaseModel):
    """Unified response model for both agent and workflow execution history"""

    result_type: str  # "agent" or "workflow"
    execution_result: Dict[str, Any]  # The complete AgentRunResult or LinearWorkflowExecutionResult
    metadata: SessionMetadata


# --- Project and Workspace Response Models ---
class ProjectInfo(BaseModel):
    """Response model for project information"""

    name: str
    path: str
    is_active: bool
    include_configs: List[str]
    description: Optional[str] = None
    created_at: Optional[float] = None


class WorkspaceInfo(BaseModel):
    """Response model for workspace information"""

    name: str
    path: str
    projects: List[str]
    include_configs: List[str]
    is_active: bool
    description: Optional[str] = None


# --- Server and Tool Response Models --
class ToolDetails(BaseModel):
    """Detailed information about a specific tool."""

    name: str
    description: str
    server_name: str
    inputSchema: Dict[str, Any]


class ServerDetailedStatus(BaseModel):
    """Detailed runtime status for a specific MCP server."""

    name: str
    registered: bool
    status: str
    transport_type: Optional[str]
    tools: List[str]
    registration_time: Optional[datetime]
    session_active: bool


class ServerTestResult(BaseModel):
    """Result of testing an MCP server configuration."""

    status: str  # "success" or "failed"
    server_name: str
    connection_time: Optional[float]
    tools_discovered: Optional[List[str]]
    test_tool_result: Optional[Dict[str, Any]]
    error: Optional[str]


class ServerRuntimeInfo(BaseModel):
    """Runtime information about a registered MCP server."""

    name: str
    status: str = "active"
    transport_type: str
    tools_count: int
    registration_time: datetime
