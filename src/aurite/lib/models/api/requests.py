from typing import Any, Awaitable, Callable, Dict, List, Optional
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
    name: Optional[str] = Field(default=None, description="User-friendly name for this test case")
    input: str = Field(description="The user input supplied in this case")
    output: Optional[Any] = Field(default=None, description="The response from the component")
    expectations: list[str] = Field(
        description='A list of expectations about the output, like "The output contains the temperature in Celcius" or "The get_weather tool was called once".'
    )


class EvaluationRequest(BaseModel):
    """Request model for QA testing."""

    component_type: Optional[str] = Field(
        default=None, description="Type of component being tested (agent, llm, mcp_server, workflow)"
    )
    component_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Configuration of the component being tested"
    )
    test_cases: List[EvaluationCase] = Field(description="List of test cases to evaluate")
    framework: Optional[str] = Field(
        default="aurite", description="Framework to use for testing (aurite, langchain, autogen, etc.)"
    )
    review_llm: Optional[str] = Field(
        default=None, description="LLM configuration ID to use for reviewing test results"
    )
    expected_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="JSON schema to validate output against"
    )
    component_refs: Optional[List[str]] = Field(
        default=None, description="List of component names to evaluate (for multi-component testing)"
    )
    run_agent: Optional[Callable[..., Any] | Callable[..., Awaitable[Any]] | str] = Field(
        default=None,
        description="""A function that takes a string input and any number of additional arguments (see run_agent_kwargs) and returns the result of calling the agent.
        This will be used for cases that do not have an output. If str, it will be treated as the filepath to a python file with the function named 'run'""",
    )
    run_agent_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional keyword arguments to pass to the run_agent function beyond the required input string first argument",
    )
    # Caching configuration
    use_cache: bool = Field(
        default=True, description="Whether to use cached results for test cases that have been evaluated before"
    )
    cache_ttl: int = Field(default=3600, description="Time-to-live for cached results in seconds (default: 1 hour)")
    force_refresh: bool = Field(default=False, description="Force re-execution of all test cases, bypassing cache")
    evaluation_config_id: Optional[str] = Field(
        default=None, description="ID of the evaluation configuration (used for cache key generation)"
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
