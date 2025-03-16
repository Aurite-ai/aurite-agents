from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set
import time
from loguru import logger


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


@dataclass
class WorkflowContext:
    """
    Context for agent execution.

    Designed to be reusable across all agent types:
    - Sequential workflows: Tracks step execution and results
    - Hybrid agents: Manages branching and decision points
    - Dynamic agents: Stores planning and memory data

    The context maintains all state during execution and serves as both
    the input carrier and output container.
    """

    # Core data that flows through the execution
    data: Dict[str, Any] = field(default_factory=dict)

    # Metadata about the execution (not used directly in processing)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Fields that must be present in data for execution to start
    required_fields: Set[str] = field(default_factory=set)

    # For workflow tracking
    step_results: Dict[str, StepResult] = field(default_factory=dict)

    # For performance tracking
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def validate(self) -> bool:
        """
        Validate that all required fields are present in the context data.
        Used by all agent types to ensure preconditions are met.

        Returns:
            True if all required fields are present, False otherwise
        """
        for field_name in self.required_fields:
            if field_name not in self.data:
                logger.error(f"Context missing required field: {field_name}")
                return False
        return True

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
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the context data.

        Args:
            key: The key to set
            value: The value to store
        """
        self.data[key] = value

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
        return {
            "success": all(
                r.status == StepStatus.COMPLETED for r in self.step_results.values()
            ),
            "execution_time": self.get_execution_time(),
            "steps_completed": len(
                [
                    r
                    for r in self.step_results.values()
                    if r.status == StepStatus.COMPLETED
                ]
            ),
            "steps_failed": len(
                [r for r in self.step_results.values() if r.status == StepStatus.FAILED]
            ),
            "steps_skipped": len(
                [
                    r
                    for r in self.step_results.values()
                    if r.status == StepStatus.SKIPPED
                ]
            ),
            "data": self.data,
        }
