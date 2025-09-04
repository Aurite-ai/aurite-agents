from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

__all__ = [
    "AgentRunRequest",
    "WorkflowRunRequest",
    "EvaluationRequest",
    "ComponentCreate",
    "ComponentUpdate",
    "FileCreateRequest",
    "FileUpdateRequest",
    "ProjectCreate",
    "ProjectUpdate",
    "ToolCallArgs",
]


# --- Component Execution Request Models ---
class AgentRunRequest(BaseModel):
    """Request model for running an agent."""

    user_message: Optional[str] = None
    messages: Optional[list[dict[str, Any]]] = None
    system_prompt: Optional[str] = None
    session_id: Optional[str] = None


class WorkflowRunRequest(BaseModel):
    """Request model for running a workflow."""

    initial_input: Any
    session_id: Optional[str] = None


class EvaluationCase(BaseModel):
    id: UUID = Field(default_factory=uuid4, description="A unique id for this evaluation test case")
    input: str = Field(description="The user input supplied in this case")
    output: Optional[Any] = Field(default=None, description="The response from the component")
    expectations: list[str] = Field(
        description='A list of expectations about the output, like "The output contains the temperature in Celcius" or "The get_weather tool was called once".'
    )


class EvaluationRequest(BaseModel):
    test_cases: list[EvaluationCase] = Field(description="A list of evaluation test cases")
    run_agent: Optional[Callable[[EvaluationCase], Any] | Callable[[EvaluationCase], Awaitable[Any]] | str] = Field(
        default=None,
        description="""A function that takes an EvaluationCase and returns the result of calling the agent. This will be used for cases that do not have an output.
        If str, it will be treated as the filepath to a python file with the function named 'run'""",
    )
    eval_name: Optional[str] = Field(
        default=None,
        description="The name of the component being evaluated, if testing an Aurite component. Will be automatically ran if no run_agent is supplied",
    )
    eval_type: Optional[Literal["agent", "linear_workflow", "custom_workflow"]] = Field(
        default=None, description="The type of component being evaluated, if testing an Aurite component."
    )
    review_llm: Optional[str] = Field(
        default=None, description="The name of the llm to use to review the component's output"
    )
    expected_schema: Optional[dict[str, Any]] = Field(
        default=None,
        description="The JSON schema the component output is expected to have.",
    )


# --- Component Configuration Request Models ---


class ComponentCreate(BaseModel):
    """Request model for creating a new component"""

    name: str = Field(..., description="Unique name for the component")
    config: Dict[str, Any] = Field(..., description="Component configuration")


class ComponentUpdate(BaseModel):
    """Request model for updating an existing component"""

    config: Dict[str, Any] = Field(..., description="Updated component configuration")


# -- File Management Request Models ---
class FileCreateRequest(BaseModel):
    source_name: str
    relative_path: str
    content: str


class FileUpdateRequest(BaseModel):
    content: str


# --- Project Management Request Models ---
class ProjectCreate(BaseModel):
    """Request model for creating a new project"""

    name: str = Field(..., pattern="^[a-zA-Z0-9_-]+$", description="Project name")
    description: Optional[str] = Field(None, description="Project description")


class ProjectUpdate(BaseModel):
    """Request model for updating a project"""

    description: Optional[str] = Field(None, description="Project description")
    include_configs: Optional[List[str]] = Field(None, description="Configuration directories")
    new_name: Optional[str] = Field(None, pattern="^[a-zA-Z0-9_-]+$", description="New project name for renaming")


# Tools


class ToolCallArgs(BaseModel):
    args: Dict[str, Any]
