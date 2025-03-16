"""
BaseWorkflow module for implementing sequential workflow agents.

This module provides:
1. WorkflowStep - Building block for workflow-based agents
2. BaseWorkflow - Implementation for linear/sequential workflows

These classes work with AgentContext (from base_models.py) to provide a
complete framework for building sequential workflows. Both are designed
to be reusable across different agent implementations (workflow, hybrid,
and dynamic).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Set, Awaitable
import asyncio
import logging
import time

from ..host.resources.tools import ToolManager
from .base_models import StepStatus, StepResult, AgentContext, AgentData
from .base_utils import (
    validate_required_fields,
    validate_provided_outputs,
    generate_object_description,
    with_retries,
    run_hooks_with_error_handling,
)

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

    # Child steps for composition support
    _child_steps: List["WorkflowStep"] = field(default_factory=list)

    @abstractmethod
    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """
        Execute the step with the given context.

        Args:
            context: The current workflow context (contains tools via context.tool_manager)

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
        return validate_required_fields(
            data=context,
            required_fields=self.required_inputs,
            context_name=f"Step '{self.name}'",
        )

    def validate_outputs(self, outputs: Dict[str, Any]) -> bool:
        """
        Validate that all promised outputs are present in the result.

        Args:
            outputs: The outputs produced by this step

        Returns:
            True if all promised outputs are present, False otherwise
        """
        return validate_provided_outputs(
            outputs=outputs,
            provided_outputs=self.provided_outputs,
            context_name=f"Step '{self.name}'",
        )

    def get_description(self) -> Dict[str, Any]:
        """
        Get a complete description of this step.
        Useful for documentation or dynamic agent planning.

        Returns:
            Dictionary describing the step
        """
        description = generate_object_description(
            name=self.name,
            description=self.description,
            required_inputs=self.required_inputs,
            provided_outputs=self.provided_outputs,
            required_tools=self.required_tools,
            tags=self.tags,
            has_condition=self.condition is not None,
            metadata=self.metadata,
        )

        # Add information about child steps if this is a composite step
        if self._child_steps:
            description["composite"] = True
            description["child_steps"] = [
                step.get_description() for step in self._child_steps
            ]
        else:
            description["composite"] = False

        return description

    def add_child_step(self, step: "WorkflowStep") -> "WorkflowStep":
        """
        Add a child step to this step for composition.

        Args:
            step: The child step to add

        Returns:
            Self, for method chaining
        """
        self._child_steps.append(step)
        return self

    def add_child_steps(self, steps: List["WorkflowStep"]) -> "WorkflowStep":
        """
        Add multiple child steps to this step for composition.

        Args:
            steps: The child steps to add

        Returns:
            Self, for method chaining
        """
        self._child_steps.extend(steps)
        return self

    @property
    def child_steps(self) -> List["WorkflowStep"]:
        """
        Get the child steps of this step.

        Returns:
            List of child steps
        """
        return self._child_steps

    @property
    def is_composite(self) -> bool:
        """
        Check if this step is a composite step.

        Returns:
            True if this step has child steps, False otherwise
        """
        return len(self._child_steps) > 0


class CompositeStep(WorkflowStep):
    """
    A workflow step that executes a sequence of child steps.

    This provides composition capability, allowing complex workflows
    to be built from simpler steps.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        steps: Optional[List[WorkflowStep]] = None,
        **kwargs,
    ):
        """
        Initialize a composite step.

        Args:
            name: The name of the step
            description: A description of the step
            steps: Optional list of child steps
            **kwargs: Additional arguments to pass to the parent constructor
        """
        super().__init__(name=name, description=description, **kwargs)

        if steps:
            self.add_child_steps(steps)

        # Update inputs/outputs/tools based on child steps
        self._update_contracts()

    def _update_contracts(self):
        """Update the contracts (inputs/outputs/tools) based on child steps"""
        if not self._child_steps:
            return

        # Start with empty sets
        all_inputs = set()
        all_outputs = set()
        all_tools = set()

        # Collect from all child steps
        for step in self._child_steps:
            all_inputs.update(step.required_inputs)
            all_outputs.update(step.provided_outputs)
            all_tools.update(step.required_tools)

        # Track outputs that are provided by steps
        provided_so_far = set()
        for step in self._child_steps:
            # Add this step's outputs to provided outputs so far
            provided_so_far.update(step.provided_outputs)

        # Update the composite step's contracts
        # Required inputs are any inputs needed by child steps that aren't provided by earlier steps
        self.required_inputs = all_inputs - provided_so_far
        # Provided outputs are all outputs from all child steps
        self.provided_outputs = all_outputs
        # Required tools are all tools from all child steps
        self.required_tools = all_tools

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """
        Execute all child steps in sequence.

        Args:
            context: The context for execution

        Returns:
            Combined outputs from all child steps
        """
        if not self._child_steps:
            logger.warning(f"CompositeStep '{self.name}' has no child steps")
            return {}

        all_outputs = {}

        # Execute each child step in sequence
        for step in self._child_steps:
            # Check if step should be executed based on its condition
            context_data = context.get_data_dict()
            if not await step.should_execute(context_data):
                logger.info(f"Skipping step '{step.name}' due to condition")
                continue

            # Execute the step
            outputs = await step.execute(context)

            # Add outputs to accumulated outputs
            all_outputs.update(outputs)

        return all_outputs


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

    def __init__(self, tool_manager: ToolManager, name: str = "unnamed_workflow"):
        """
        Initialize the workflow with a tool manager.
        
        Args:
            tool_manager: The tool manager for tool access
            name: Name of the workflow
        """
        self.name = name
        self.description = ""  # Can be overridden by subclasses
        self.steps: List[WorkflowStep] = []
        self.error_handlers: Dict[
            str, Callable[[WorkflowStep, Exception, Dict[str, Any]], None]
        ] = {}
        self.global_error_handler: Optional[
            Callable[[WorkflowStep, Exception, Dict[str, Any]], None]
        ] = None
        self.on_workflow_complete: Optional[Callable[[AgentContext], None]] = None
        self.context_validators: List[Callable[[Dict[str, Any]], bool]] = []

        # Store the tool manager
        self.tool_manager = tool_manager

        # Middleware hooks
        self.before_workflow_hooks: List[Callable[[AgentContext], Awaitable[None]]] = []
        self.after_workflow_hooks: List[Callable[[AgentContext], Awaitable[None]]] = []
        self.before_step_hooks: List[
            Callable[[WorkflowStep, AgentContext], Awaitable[None]]
        ] = []
        self.after_step_hooks: List[
            Callable[[WorkflowStep, AgentContext, StepResult], Awaitable[None]]
        ] = []

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

        # Check if tools are available through tool manager
        unavailable_tools = []
        for tool in all_required_tools:
            if not self.tool_manager.has_tool(tool):
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

    def add_before_workflow_hook(self, hook: Callable[[AgentContext], Awaitable[None]]):
        """
        Add a hook to run before workflow execution.

        Args:
            hook: The hook function to run before workflow execution
        """
        self.before_workflow_hooks.append(hook)

    def add_after_workflow_hook(self, hook: Callable[[AgentContext], Awaitable[None]]):
        """
        Add a hook to run after workflow execution.

        Args:
            hook: The hook function to run after workflow execution
        """
        self.after_workflow_hooks.append(hook)

    def add_before_step_hook(
        self, hook: Callable[[WorkflowStep, AgentContext], Awaitable[None]]
    ):
        """
        Add a hook to run before each step execution.

        Args:
            hook: The hook function to run before step execution
        """
        self.before_step_hooks.append(hook)

    def add_after_step_hook(
        self, hook: Callable[[WorkflowStep, AgentContext, StepResult], Awaitable[None]]
    ):
        """
        Add a hook to run after each step execution.

        Args:
            hook: The hook function to run after step execution
        """
        self.after_step_hooks.append(hook)

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

        # Define the actual execution function
        async def execute_with_validation():
            # Create a context for the step with tool_manager already set
            step_context = AgentContext(data=AgentData(**context_data.copy()))
            step_context.tool_manager = self.tool_manager

            # Execute step
            outputs = await step.execute(step_context)

            # Validate outputs
            if not step.validate_outputs(outputs):
                raise ValueError(f"Step '{step.name}' missing promised outputs")

            return outputs

        # Handle error callback
        async def handle_error(error: Exception, attempt: int):
            await self.handle_step_error(step, error, context_data)

        # Use the retry decorator
        try:
            start_time = time.time()

            # Apply the decorator dynamically
            decorated_execute = with_retries(
                max_retries=step.max_retries,
                retry_delay=step.retry_delay,
                exponential_backoff=True,
                timeout=step.timeout,
                on_retry=lambda e, a: asyncio.create_task(handle_error(e, a)),
            )(execute_with_validation)

            # Execute with retries
            outputs = await decorated_execute()

            # Calculate execution time
            execution_time = time.time() - start_time

            # Return successful result
            return StepResult(
                status=StepStatus.COMPLETED,
                outputs=outputs,
                execution_time=execution_time,
            )

        except asyncio.TimeoutError:
            return StepResult(
                status=StepStatus.FAILED,
                error=asyncio.TimeoutError(
                    f"Step '{step.name}' timed out after {step.timeout} seconds"
                ),
            )

        except Exception as e:
            return StepResult(status=StepStatus.FAILED, error=e)

    async def execute(
        self, input_data: Dict[str, Any], metadata: Dict[str, Any] = None
    ) -> AgentContext:
        """
        Execute the workflow with the given input data.

        Args:
            input_data: Initial data for the workflow
            metadata: Optional metadata for the workflow

        Returns:
            The final workflow context
        """
        # Initialize context with dictionary data for backward compatibility
        agent_context = AgentContext(
            data=AgentData(**input_data), metadata=metadata.copy() if metadata else {}
        )

        # Set the tool_manager reference
        agent_context.tool_manager = self.tool_manager

        logger.info(f"Starting execution of workflow: {self.name}")

        # Run before workflow hooks
        await run_hooks_with_error_handling(
            self.before_workflow_hooks, "before workflow", agent_context
        )

        # Validate initial context
        context_data = agent_context.get_data_dict()
        if not self.validate_context(context_data):
            logger.error("Initial context failed validation")
            agent_context.add_step_result(
                "context_validation",
                StepResult(
                    status=StepStatus.FAILED,
                    error=ValueError("Initial context failed validation"),
                ),
            )
            agent_context.complete()
            return agent_context

        # Execute each step in sequence
        for step in self.steps:
            # Check if step should be executed based on its condition
            context_data = agent_context.get_data_dict()
            if not await step.should_execute(context_data):
                logger.info(f"Skipping step '{step.name}' due to condition")
                agent_context.add_step_result(
                    step.name, StepResult(status=StepStatus.SKIPPED)
                )
                continue

            # Log step execution
            logger.info(f"Executing step: {step.name}")

            # Run before step hooks
            await run_hooks_with_error_handling(
                self.before_step_hooks, f"before step {step.name}", step, agent_context
            )
            result = await self.execute_step(step, context_data)

            # Store result in context
            agent_context.add_step_result(step.name, result)

            # Run after step hooks
            await run_hooks_with_error_handling(
                self.after_step_hooks,
                f"after step {step.name}",
                step,
                agent_context,
                result,
            )

            # If step failed, stop workflow execution
            if result.status == StepStatus.FAILED:
                logger.error(
                    f"Workflow '{self.name}' stopped due to failed step: {step.name}"
                )
                agent_context.complete()
                return agent_context

            # If step completed successfully, update context with outputs
            if result.status == StepStatus.COMPLETED:
                # For Pydantic models, update each attribute individually
                for key, value in result.outputs.items():
                    agent_context.set(key, value)

        # Mark workflow as complete
        agent_context.complete()

        # Call completion callback if set
        if self.on_workflow_complete:
            await run_hooks_with_error_handling(
                [self.on_workflow_complete],
                "workflow completion callback",
                agent_context,
            )

        # Run after workflow hooks
        await run_hooks_with_error_handling(
            self.after_workflow_hooks, "after workflow", agent_context
        )

        logger.info(
            f"Workflow '{self.name}' completed in {agent_context.get_execution_time():.2f} seconds"
        )
        return agent_context

    async def shutdown(self):
        """Clean up resources used by the workflow"""
        logger.info(f"Shutting down workflow: {self.name}")
