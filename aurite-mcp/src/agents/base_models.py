from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set, TypeVar, Generic
import time
import logging
from pydantic import BaseModel, ConfigDict, create_model

from .base_utils import validate_required_fields, summarize_execution_results

# Set up logging
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


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
        required_fields: Optional[Set[str]] = None,
    ):
        # Set up the data model
        if data is None:
            self.data = AgentData()
        else:
            try:
                if isinstance(data, dict) and not isinstance(data, BaseModel):
                    # Convert dict to AgentData
                    self.data = AgentData(**data)
                else:
                    self.data = data
            except TypeError as e:
                # If we can't properly initialize with the data, use a simpler approach
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to initialize AgentData properly: {e}. Using fallback.")
                self.data = data  # Just use as-is and handle later

        # Metadata about the execution (not used directly in processing)
        self.metadata: Dict[str, Any] = metadata or {}

        # Fields that must be present in data for execution to start
        self.required_fields: Set[str] = required_fields or set()

        # For workflow tracking
        self.step_results: Dict[str, StepResult] = {}

        # For performance tracking
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None

        # References to the tool manager and host - set by the workflow
        self.tool_manager = None
        self.host = None

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
                context_name="Context",
            )
        else:
            # Fallback for non-Pydantic data (should not happen with proper typing)
            return validate_required_fields(
                data=self.data,
                required_fields=self.required_fields,
                context_name="Context",
            )

    def get_data_dict(self) -> Dict[str, Any]:
        """
        Get the context data as a dictionary.

        Returns:
            Dictionary representation of the context data
        """
        # First check if we have a fallback dictionary
        if hasattr(self, '_fallback_dict'):
            return self._fallback_dict.copy()  # Return a copy to avoid mutations
            
        # Try the normal path
        try:
            if isinstance(self.data, BaseModel):
                return self.data.model_dump()
            elif isinstance(self.data, dict):
                return self.data
            elif hasattr(self.data, "__dict__"):
                # For non-Pydantic objects with __dict__
                return {k: v for k, v in self.data.__dict__.items() if not k.startswith("_")}
            else:
                # Last resort, convert to string
                return {"data": str(self.data)}
        except TypeError as e:
            # Handle serialization errors with MockValSer objects
            logger.warning(f"Serialization error in get_data_dict: {e}")
            
            # Create a result dictionary
            result = {}
            
            # Try to extract information from the data object
            if hasattr(self.data, "__dict__"):
                for key, value in self.data.__dict__.items():
                    if key.startswith("_"):
                        continue
                    if hasattr(value, "__dict__"):
                        # For nested objects, convert them to simple strings
                        result[key] = str(value)
                    else:
                        result[key] = value
            
            # If we couldn't extract anything, return empty dict
            if not result:
                return {"error": "Failed to convert data to dictionary"}
                
            return result

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
        # First check our fallback dictionary if it exists
        # This is the most reliable source for data when working with mock objects
        if hasattr(self, '_fallback_dict'):
            if key in self._fallback_dict:
                # Log when we successfully retrieve from fallback dict
                logger.debug(f"Retrieved '{key}' from _fallback_dict")
                return self._fallback_dict[key]
            else:
                # Make this extra visible in logs
                logger.warning(f"KEY NOT FOUND: '{key}' not in _fallback_dict. Available keys: {list(self._fallback_dict.keys())}")
            
        # Try the normal path
        try:
            if isinstance(self.data, BaseModel):
                try:
                    value = getattr(self.data, key)
                    logger.debug(f"Retrieved '{key}' from BaseModel data")
                    return value
                except AttributeError:
                    logger.warning(f"KEY NOT FOUND: '{key}' not in BaseModel attributes")
                    return default
            else:
                # Fallback for dict-like access
                if hasattr(self.data, "get"):
                    value = self.data.get(key, default)
                    if value != default:
                        logger.debug(f"Retrieved '{key}' using dict-like access")
                    else:
                        logger.warning(f"KEY NOT FOUND: '{key}' using dict-like access")
                    return value
                elif hasattr(self.data, "__getitem__"):
                    try:
                        value = self.data[key]
                        logger.debug(f"Retrieved '{key}' using __getitem__")
                        return value
                    except (KeyError, IndexError):
                        logger.warning(f"KEY NOT FOUND: '{key}' using __getitem__")
                        return default
                else:
                    logger.warning(f"No way to access '{key}' in data of type {type(self.data)}")
                    return default
        except Exception as e:
            # Log the specific exception
            logger.warning(f"Exception when getting '{key}': {type(e).__name__}: {e}")
            # If all else fails, return the default
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the context data.

        Args:
            key: The key to set
            value: The value to store
        """
        try:
            if isinstance(self.data, BaseModel):
                setattr(self.data, key, value)
            else:
                # Fallback for dict-like access
                if hasattr(self.data, "__setitem__"):
                    self.data[key] = value
                else:
                    setattr(self.data, key, value)
        except (TypeError, AttributeError) as e:
            # Handle serialization errors with MockValSer objects
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to set attribute {key} directly: {e}. Using fallback dictionary.")
            
            # Create a backup dictionary if we don't have one yet
            if not hasattr(self, '_fallback_dict'):
                self._fallback_dict = {}
                # Try to populate from existing data
                try:
                    if hasattr(self.data, '__dict__'):
                        for k, v in self.data.__dict__.items():
                            if not k.startswith('_'):
                                self._fallback_dict[k] = v
                except Exception:
                    pass
            
            # Update the fallback dictionary
            self._fallback_dict[key] = value

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
        data_dict = (
            self.data.model_dump() if isinstance(self.data, BaseModel) else self.data
        )

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
        DataModel = create_model(
            "CustomAgentData", **field_definitions, __base__=AgentData
        )

        # Return a new context instance with the custom model
        return lambda **kwargs: cls(data=DataModel(**kwargs))
