"""
BaseWorkflow module for implementing sequential workflow agents.

This module provides:
1. WorkflowContext - Shared context model used by all agent types
2. WorkflowStep - Building block for workflow-based agents
3. BaseWorkflow - Implementation for linear/sequential workflows

The WorkflowContext and WorkflowStep classes are designed to be reusable
across different agent implementations (workflow, hybrid, and dynamic).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Set
import asyncio
import logging
import time

from ..host.host import MCPHost
from .base_models import StepStatus, StepResult, WorkflowContext

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep(ABC):
    """
    Abstract base class for workflow steps.

    A WorkflowStep is a reusable component that:
    1. Defines clear inputs and outputs (contract)
    2. Performs a specific piece of work
    3. Can be composed into different workflow patterns
    4. Can include optional execution conditions

    Used by both sequential workflows and hybrid agents.
    """

    name: str
    description: str = ""
    required_inputs: Set[str] = field(default_factory=set)
    provided_outputs: Set[str] = field(default_factory=set)
    required_tools: Set[str] = field(default_factory=set)
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    timeout: float = 60.0  # seconds

    # Tags for categorization and filtering
    tags: Set[str] = field(default_factory=set)

    # Optional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Optional condition for execution
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None

    @abstractmethod
    async def execute(self, context: WorkflowContext, host: MCPHost) -> Dict[str, Any]:
        """
        Execute the step with the given context.

        Args:
            context: The current workflow context
            host: The MCP host for tool access

        Returns:
            Dictionary of outputs produced by this step
        """
        pass

    async def should_execute(self, context: Dict[str, Any]) -> bool:
        """
        Determine if the step should be executed based on its condition.

        Args:
            context: The current workflow context data

        Returns:
            True if the step should be executed, False otherwise
        """
        # No condition means always execute
        if self.condition is None:
            return True

        try:
            return self.condition(context)
        except Exception as e:
            logger.error(f"Error evaluating condition for step '{self.name}': {e}")
            return False

    def validate_inputs(self, context: Dict[str, Any]) -> bool:
        """
        Validate that all required inputs are present in the context.

        Args:
            context: The current workflow context data dictionary

        Returns:
            True if all required inputs are present, False otherwise
        """
        for input_key in self.required_inputs:
            if input_key not in context:
                logger.error(f"Step '{self.name}' missing required input: {input_key}")
                return False
        return True

    def validate_outputs(self, outputs: Dict[str, Any]) -> bool:
        """
        Validate that all promised outputs are present in the result.

        Args:
            outputs: The outputs produced by this step

        Returns:
            True if all promised outputs are present, False otherwise
        """
        for output_key in self.provided_outputs:
            if output_key not in outputs:
                logger.error(
                    f"Step '{self.name}' missing promised output: {output_key}"
                )
                return False
        return True

    def get_description(self) -> Dict[str, Any]:
        """
        Get a complete description of this step.
        Useful for documentation or dynamic agent planning.

        Returns:
            Dictionary describing the step
        """
        return {
            "name": self.name,
            "description": self.description,
            "required_inputs": list(self.required_inputs),
            "provided_outputs": list(self.provided_outputs),
            "required_tools": list(self.required_tools),
            "tags": list(self.tags),
            "has_condition": self.condition is not None,
            "metadata": self.metadata,
        }


class BaseWorkflow(ABC):
    """
    Base class for implementing strictly sequential workflow agents.

    This class focuses specifically on linear workflows where:
    1. Steps are executed in a predefined sequence
    2. Each step has access to specific tools
    3. Data flows from one step to the next via the context
    4. Steps can be conditionally executed but not reordered dynamically

    For more complex workflows with branching or dynamic behavior,
    consider combining this with elements from BaseAgent or creating
    a hybrid implementation.
    """

    def __init__(self, host: MCPHost, name: str = "unnamed_workflow"):
        self.host = host
        self.name = name
        self.steps: List[WorkflowStep] = []
        self.error_handlers: Dict[
            str, Callable[[WorkflowStep, Exception, Dict[str, Any]], None]
        ] = {}
        self.global_error_handler: Optional[
            Callable[[WorkflowStep, Exception, Dict[str, Any]], None]
        ] = None
        self.on_workflow_complete: Optional[Callable[[WorkflowContext], None]] = None
        self.context_validators: List[Callable[[Dict[str, Any]], bool]] = []

    async def initialize(self):
        """Initialize the workflow"""
        logger.info(f"Initializing workflow: {self.name}")

        # Validate that all required tools are available
        await self._validate_tools()

    async def _validate_tools(self):
        """Validate that all required tools are available"""
        all_required_tools = set()

        # Collect all required tools from steps
        for step in self.steps:
            all_required_tools.update(step.required_tools)

        # Check if tools are available through host
        unavailable_tools = []
        for tool in all_required_tools:
            if tool not in self.host._tools:
                unavailable_tools.append(tool)

        if unavailable_tools:
            error_msg = f"Required tools not available: {', '.join(unavailable_tools)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def add_step(
        self,
        step: WorkflowStep,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ):
        """
        Add a step to the workflow.

        Args:
            step: The workflow step to add
            condition: Optional condition to determine if the step should be executed
        """
        if condition:
            # Set the condition directly on the step
            step.condition = condition

        self.steps.append(step)

    def add_error_handler(
        self,
        step_name: str,
        handler: Callable[[WorkflowStep, Exception, Dict[str, Any]], None],
    ):
        """
        Add an error handler for a specific step.

        Args:
            step_name: The name of the step to handle errors for
            handler: The error handler function
        """
        self.error_handlers[step_name] = handler

    def set_global_error_handler(
        self, handler: Callable[[WorkflowStep, Exception, Dict[str, Any]], None]
    ):
        """
        Set a global error handler for all steps.

        Args:
            handler: The error handler function
        """
        self.global_error_handler = handler

    def add_context_validator(self, validator: Callable[[Dict[str, Any]], bool]):
        """
        Add a validator for the workflow context.

        Args:
            validator: The validator function
        """
        self.context_validators.append(validator)

    def validate_context(self, context: Dict[str, Any]) -> bool:
        """
        Validate the workflow context using all registered validators.

        Args:
            context: The context to validate

        Returns:
            True if all validators pass, False otherwise
        """
        for validator in self.context_validators:
            if not validator(context):
                return False
        return True

    async def handle_step_error(
        self, step: WorkflowStep, error: Exception, context: Dict[str, Any]
    ):
        """
        Handle an error that occurred during step execution.

        Args:
            step: The step that failed
            error: The exception that was raised
            context: The current workflow context
        """
        # First try step-specific handler
        if step.name in self.error_handlers:
            try:
                self.error_handlers[step.name](step, error, context)
                return
            except Exception as e:
                logger.error(f"Error in error handler for step '{step.name}': {e}")

        # Fall back to global handler if available
        if self.global_error_handler:
            try:
                self.global_error_handler(step, error, context)
                return
            except Exception as e:
                logger.error(f"Error in global error handler: {e}")

        # Default behavior: log error
        logger.error(f"Unhandled error in step '{step.name}': {error}")

    async def execute_step(
        self, step: WorkflowStep, context_data: Dict[str, Any]
    ) -> StepResult:
        """
        Execute a single workflow step with retries.

        Args:
            step: The step to execute
            context_data: The current workflow context data dictionary

        Returns:
            The result of the step execution
        """
        # First validate inputs
        if not step.validate_inputs(context_data):
            return StepResult(
                status=StepStatus.FAILED,
                error=ValueError(f"Step '{step.name}' missing required inputs"),
            )

        # Try to execute the step with retries
        attempts = 0
        while attempts <= step.max_retries:
            attempts += 1

            # Record start time
            start_time = time.time()

            try:
                # Create a workflow context for the step
                step_context = WorkflowContext(data=context_data.copy())

                # Execute step with timeout
                step_task = asyncio.create_task(step.execute(step_context, self.host))
                outputs = await asyncio.wait_for(step_task, timeout=step.timeout)

                # Calculate execution time
                execution_time = time.time() - start_time

                # Validate outputs
                if not step.validate_outputs(outputs):
                    raise ValueError(f"Step '{step.name}' missing promised outputs")

                # Return successful result
                return StepResult(
                    status=StepStatus.COMPLETED,
                    outputs=outputs,
                    execution_time=execution_time,
                )

            except asyncio.TimeoutError:
                logger.warning(
                    f"Step '{step.name}' timed out after {step.timeout} seconds"
                )
                # If this was the last attempt, return failure
                if attempts > step.max_retries:
                    return StepResult(
                        status=StepStatus.FAILED,
                        error=asyncio.TimeoutError(
                            f"Step '{step.name}' timed out after {step.timeout} seconds"
                        ),
                    )

            except Exception as e:
                logger.warning(f"Step '{step.name}' failed on attempt {attempts}: {e}")
                # Handle the error
                await self.handle_step_error(step, e, context_data)

                # If this was the last attempt, return failure
                if attempts > step.max_retries:
                    return StepResult(status=StepStatus.FAILED, error=e)

            # Wait before retrying
            if attempts <= step.max_retries:
                retry_delay = step.retry_delay * (
                    2 ** (attempts - 1)
                )  # Exponential backoff
                logger.info(f"Retrying step '{step.name}' in {retry_delay} seconds")
                await asyncio.sleep(retry_delay)

        # Should never reach here, but just in case
        return StepResult(
            status=StepStatus.FAILED,
            error=RuntimeError(
                f"Step '{step.name}' failed after {step.max_retries} retries"
            ),
        )

    async def execute(
        self, input_data: Dict[str, Any], metadata: Dict[str, Any] = None
    ) -> WorkflowContext:
        """
        Execute the workflow with the given input data.

        Args:
            input_data: Initial data for the workflow
            metadata: Optional metadata for the workflow

        Returns:
            The final workflow context
        """
        # Initialize context
        workflow_context = WorkflowContext(
            data=input_data.copy(), metadata=metadata.copy() if metadata else {}
        )

        logger.info(f"Starting execution of workflow: {self.name}")

        # Validate initial context
        if not self.validate_context(workflow_context.data):
            logger.error("Initial workflow context failed validation")
            workflow_context.add_step_result(
                "context_validation",
                StepResult(
                    status=StepStatus.FAILED,
                    error=ValueError("Initial workflow context failed validation"),
                ),
            )
            workflow_context.complete()
            return workflow_context

        # Execute each step in sequence
        for step in self.steps:
            # Check if step should be executed based on its condition
            if not await step.should_execute(workflow_context.data):
                logger.info(f"Skipping step '{step.name}' due to condition")
                workflow_context.add_step_result(
                    step.name, StepResult(status=StepStatus.SKIPPED)
                )
                continue

            # Log step execution
            logger.info(f"Executing step: {step.name}")

            # Execute the step
            result = await self.execute_step(step, workflow_context.data)

            # Store result in context
            workflow_context.add_step_result(step.name, result)

            # If step failed, stop workflow execution
            if result.status == StepStatus.FAILED:
                logger.error(
                    f"Workflow '{self.name}' stopped due to failed step: {step.name}"
                )
                workflow_context.complete()
                return workflow_context

            # If step completed successfully, update context with outputs
            if result.status == StepStatus.COMPLETED:
                workflow_context.data.update(result.outputs)

        # Mark workflow as complete
        workflow_context.complete()

        # Call completion callback if set
        if self.on_workflow_complete:
            try:
                self.on_workflow_complete(workflow_context)
            except Exception as e:
                logger.error(f"Error in workflow completion callback: {e}")

        logger.info(
            f"Workflow '{self.name}' completed in {workflow_context.get_execution_time():.2f} seconds"
        )
        return workflow_context

    async def shutdown(self):
        """Clean up resources used by the workflow"""
        logger.info(f"Shutting down workflow: {self.name}")
