from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set, TypeVar, Generic, ClassVar
import time
from pydantic import BaseModel, ConfigDict, Field, create_model
from typing import get_type_hints

from .base_utils import validate_required_fields, summarize_execution_results

T = TypeVar('T', bound=BaseModel)


class StepStatus(Enum):
    """Status of a workflow step"""

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class StepResult:
    """Result of a workflow step execution"""

    status: StepStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None
    execution_time: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)


class AgentData(BaseModel):
    """
    Base model for agent context data.
    
    This can be extended to create specific data models for different agent types.
    """
    model_config = ConfigDict(extra="allow")  # Allow extra fields


class AgentContext(Generic[T]):
    """
    Context for agent execution.

    Designed to be reusable across all agent types:
    - Sequential workflows: Tracks step execution and results
    - Hybrid agents: Manages branching and decision points
    - Dynamic agents: Stores planning and memory data

    The context maintains all state during execution and serves as both
    the input carrier and output container.
    
    Can be used with a specific data model:
    context = AgentContext[CustomDataModel](data=CustomDataModel(...))
    
    Or with the default AgentData model:
    context = AgentContext(data=AgentData(field1="value"))
    """

    def __init__(
        self, 
        data: Optional[T] = None, 
        metadata: Optional[Dict[str, Any]] = None,
        required_fields: Optional[Set[str]] = None
    ):
        # Set up the data model
        if data is None:
            self.data = AgentData()
        else:
            self.data = data
            
        # Metadata about the execution (not used directly in processing)
        self.metadata: Dict[str, Any] = metadata or {}
        
        # Fields that must be present in data for execution to start
        self.required_fields: Set[str] = required_fields or set()
        
        # For workflow tracking
        self.step_results: Dict[str, StepResult] = {}
        
        # For performance tracking
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None

    def validate(self) -> bool:
        """
        Validate that all required fields are present in the context data.
        Used by all agent types to ensure preconditions are met.

        Returns:
            True if all required fields are present, False otherwise
        """
        if isinstance(self.data, BaseModel):
            # Use Pydantic's built-in validation if data is a BaseModel
            data_dict = self.data.model_dump()
            return validate_required_fields(
                data=data_dict, 
                required_fields=self.required_fields, 
                context_name="Context"
            )
        else:
            # Fallback for non-Pydantic data (should not happen with proper typing)
            return validate_required_fields(
                data=self.data, 
                required_fields=self.required_fields, 
                context_name="Context"
            )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the context data.
        Provides a safe way to access context values with defaults.

        Args:
            key: The key to retrieve
            default: Value to return if key doesn't exist

        Returns:
            The value associated with the key, or the default
        """
        if isinstance(self.data, BaseModel):
            try:
                return getattr(self.data, key)
            except AttributeError:
                return default
        else:
            # Fallback for dict-like access
            return getattr(self.data, "get", lambda k, d: d)(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the context data.

        Args:
            key: The key to set
            value: The value to store
        """
        if isinstance(self.data, BaseModel):
            setattr(self.data, key, value)
        else:
            # Fallback for dict-like access
            if hasattr(self.data, "__setitem__"):
                self.data[key] = value
            else:
                setattr(self.data, key, value)

    def add_step_result(self, step_name: str, result: StepResult):
        """
        Add a step result to the context.
        Used by workflow and hybrid agents to track step execution.

        Args:
            step_name: The name of the step
            result: The result of the step execution
        """
        self.step_results[step_name] = result

    def get_step_result(self, step_name: str) -> Optional[StepResult]:
        """
        Get a step result from the context.

        Args:
            step_name: The name of the step

        Returns:
            The step result, or None if not found
        """
        return self.step_results.get(step_name)

    def get_execution_time(self) -> float:
        """
        Get the total execution time.

        Returns:
            Execution time in seconds
        """
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def complete(self):
        """Mark the execution as complete"""
        self.end_time = time.time()

    def summarize_results(self) -> Dict[str, Any]:
        """
        Create a summary of execution results.
        Useful for returning results to calling code.

        Returns:
            Dictionary summarizing the execution results
        """
        # Convert Pydantic model to dict if needed
        data_dict = self.data.model_dump() if isinstance(self.data, BaseModel) else self.data
        
        return summarize_execution_results(
            step_results=self.step_results,
            data=data_dict,
            execution_time=self.get_execution_time(),
            status_enum=StepStatus,
        )
        
    @classmethod
    def create_model(cls, **field_definitions):
        """
        Create a custom AgentData model with the given field definitions.
        
        Usage:
            CustomContext = AgentContext.create_model(
                name=str,
                age=int,
                email=(str, ...),  # Required field
            )
            context = CustomContext(data={"name": "Alice", "age": 30, "email": "alice@example.com"})
            
        Returns:
            An AgentContext class with a custom data model
        """
        # Create a Pydantic model with the given fields
        DataModel = create_model("CustomAgentData", **field_definitions, __base__=AgentData)
        
        # Return a new context instance with the custom model
        return lambda **kwargs: cls(data=DataModel(**kwargs))
