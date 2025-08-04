from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

__all__ = [
    "AgentRunRequest",
    "WorkflowRunRequest",
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

    user_message: str
    system_prompt: Optional[str] = None
    session_id: Optional[str] = None


class WorkflowRunRequest(BaseModel):
    """Request model for running a workflow."""

    initial_input: Any
    session_id: Optional[str] = None


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
