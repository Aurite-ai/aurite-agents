from typing import Any, Dict, List, Literal, Optional

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


class EvaluationRequest(BaseModel):
    eval_name: str = Field(description="The name of the component being evaluated")
    eval_type: Literal["agent", "linear_workflow", "custom_workflow"] = Field(
        description="The type of component being evaluated"
    )
    user_input: str = Field(description="The user input to be fed to the component")
    expected_output: str = Field(description="A semantic description of the expected output of the component")
    review_llm: Optional[str] = Field(
        default=None, description="The name of the llm to use to review the component's output"
    )
    expected_schema: Optional[dict[str, Any]] = Field(
        default=None,
        description="The JSON schema the component output is expected to have.",
    )
    conversation_instructions: Optional[str] = Field(
        default=None,
        description="Instructions to be given to a conversation agent, to test a continued conversation with the tested agent. Ignored if eval_type is not 'agent'",
    )
    conversation_turns: int = Field(
        default=0,
        ge=0,
        description="The number of conversation turns to process with the conversation agent, after the initial response from the tested agent. Ignored if eval_type is not 'agent'",
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
