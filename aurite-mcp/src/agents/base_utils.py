"""
Utility functions for agent implementations.

This module provides:
1. Reusable utilities for validating inputs/outputs
2. Function for generating standardized descriptions
3. Results summarization functionality
4. Retry decorator for async functions
"""

import logging
import asyncio
import time
import functools
from typing import (
    Dict,
    List,
    Any,
    Set,
    Optional,
    Callable,
    TypeVar,
    Awaitable,
)
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


async def run_hooks_with_error_handling(
    hooks: List[Callable], hook_type: str, *args, **kwargs
) -> None:
    """
    Run a list of hooks with error handling.

    Args:
        hooks: List of hook functions to run
        hook_type: Type of hook for error messaging
        *args: Arguments to pass to each hook
        **kwargs: Keyword arguments to pass to each hook
    """
    for hook in hooks:
        try:
            # Check if the hook is awaitable
            if asyncio.iscoroutinefunction(hook):
                await hook(*args, **kwargs)
            else:
                hook(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {hook_type} hook: {e}")


def validate_required_fields(
    data: Dict[str, Any], required_fields: Set[str], context_name: str = "Context"
) -> bool:
    """
    Validate that all required fields are present in a data dictionary.

    Args:
        data: The data dictionary to validate
        required_fields: Set of field names that must be present
        context_name: Name to use in error messages (e.g., "Step", "Context")

    Returns:
        True if all required fields are present, False otherwise
    """
    for field_name in required_fields:
        if field_name not in data:
            logger.error(f"{context_name} missing required field: {field_name}")
            return False
    return True


def validate_provided_outputs(
    outputs: Dict[str, Any], provided_outputs: Set[str], context_name: str = "Step"
) -> bool:
    """
    Validate that all promised outputs are present in the result.

    Args:
        outputs: The outputs produced
        provided_outputs: Set of output names that must be provided
        context_name: Name to use in error messages

    Returns:
        True if all promised outputs are present, False otherwise
    """
    for output_key in provided_outputs:
        if output_key not in outputs:
            logger.error(f"{context_name} missing promised output: {output_key}")
            return False
    return True


def generate_object_description(
    name: str,
    description: str,
    required_inputs: Optional[Set[str]] = None,
    provided_outputs: Optional[Set[str]] = None,
    required_tools: Optional[Set[str]] = None,
    tags: Optional[Set[str]] = None,
    has_condition: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
    **additional_fields,
) -> Dict[str, Any]:
    """
    Generate a standardized description dictionary for an object.
    Useful for documenting steps, agents, and other components.

    Args:
        name: The name of the object
        description: A description of the object
        required_inputs: Optional set of required input fields
        provided_outputs: Optional set of provided output fields
        required_tools: Optional set of required tools
        tags: Optional set of tags for categorization
        has_condition: Whether the object has an execution condition
        metadata: Optional metadata dictionary
        additional_fields: Additional fields to include in the description

    Returns:
        Dictionary describing the object
    """
    result = {
        "name": name,
        "description": description,
    }

    if required_inputs is not None:
        result["required_inputs"] = list(required_inputs)

    if provided_outputs is not None:
        result["provided_outputs"] = list(provided_outputs)

    if required_tools is not None:
        result["required_tools"] = list(required_tools)

    if tags is not None:
        result["tags"] = list(tags)

    if has_condition:
        result["has_condition"] = has_condition

    if metadata is not None:
        result["metadata"] = metadata

    # Add any additional fields
    result.update(additional_fields)

    return result


def summarize_execution_results(
    step_results: Dict[str, Any],
    data: Dict[str, Any],
    execution_time: float,
    status_enum: Optional[Enum] = None,
    completed_status: Any = None,
    failed_status: Any = None,
    skipped_status: Any = None,
) -> Dict[str, Any]:
    """
    Create a summary of execution results.
    Works with both workflow execution and other agent executions.

    Args:
        step_results: Dictionary of step/action results
        data: The final data state
        execution_time: Total execution time in seconds
        status_enum: Optional Enum class for status values
        completed_status: Status value for completed steps (default uses 'COMPLETED')
        failed_status: Status value for failed steps (default uses 'FAILED')
        skipped_status: Status value for skipped steps (default uses 'SKIPPED')

    Returns:
        Dictionary summarizing the execution results
    """
    # If no enum provided, use string matching
    if status_enum is None:
        # Count based on string values if enum not provided
        def count_by_status(status_value):
            return len(
                [
                    r
                    for r in step_results.values()
                    if getattr(r, "status", None) == status_value
                    or r.get("status") == status_value
                ]
            )

        completed = completed_status or "COMPLETED"
        failed = failed_status or "FAILED"
        skipped = skipped_status or "SKIPPED"

        steps_completed = count_by_status(completed)
        steps_failed = count_by_status(failed)
        steps_skipped = count_by_status(skipped)
    else:
        # Count based on enum values
        _completed = completed_status or getattr(status_enum, "COMPLETED", None)
        _failed = failed_status or getattr(status_enum, "FAILED", None)
        _skipped = skipped_status or getattr(status_enum, "SKIPPED", None)

        steps_completed = len(
            [
                r
                for r in step_results.values()
                if getattr(r, "status", None) == _completed
            ]
        )
        steps_failed = len(
            [r for r in step_results.values() if getattr(r, "status", None) == _failed]
        )
        steps_skipped = len(
            [r for r in step_results.values() if getattr(r, "status", None) == _skipped]
        )

    # Determine overall success
    success = steps_failed == 0 and steps_completed > 0

    return {
        "success": success,
        "execution_time": execution_time,
        "steps_completed": steps_completed,
        "steps_failed": steps_failed,
        "steps_skipped": steps_skipped,
        "data": data,
    }


def with_retries(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    exponential_backoff: bool = True,
    timeout: Optional[float] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    on_timeout: Optional[Callable[[float], None]] = None,
    on_success: Optional[Callable[[Any, float], None]] = None,
    should_retry: Optional[Callable[[Exception], bool]] = None,
):
    """
    Decorator for adding retry behavior to async functions.

    Args:
        max_retries: Maximum number of retry attempts (not counting the initial attempt)
        retry_delay: Base delay between retries (in seconds)
        exponential_backoff: Whether to use exponential backoff for delays
        timeout: Optional timeout for each attempt (in seconds)
        on_retry: Optional callback when a retry occurs
        on_timeout: Optional callback when a timeout occurs
        on_success: Optional callback when the function succeeds
        should_retry: Optional function to determine if a specific exception should trigger a retry

    Returns:
        A decorator that adds retry behavior to the decorated function

    Usage:
        @with_retries(max_retries=3, retry_delay=2.0)
        async def my_function():
            # Function that might fail and need retries
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            last_exception = None

            while attempts <= max_retries:
                # Record start time
                start_time = time.time()
                attempts += 1

                try:
                    # Handle timeout if provided
                    if timeout:
                        task = asyncio.create_task(func(*args, **kwargs))
                        result = await asyncio.wait_for(task, timeout=timeout)
                    else:
                        result = await func(*args, **kwargs)

                    # Calculate execution time
                    execution_time = time.time() - start_time

                    # Call on_success callback if provided
                    if on_success:
                        on_success(result, execution_time)

                    return result

                except asyncio.TimeoutError as e:
                    logger.warning(
                        f"Function '{func.__name__}' timed out after {timeout} seconds"
                    )

                    # Call on_timeout callback if provided
                    if on_timeout:
                        on_timeout(timeout)

                    last_exception = e

                    # Don't retry on the last attempt
                    if attempts > max_retries:
                        break

                except Exception as e:
                    logger.warning(
                        f"Function '{func.__name__}' failed on attempt {attempts}: {e}"
                    )
                    last_exception = e

                    # Check if we should retry for this exception
                    if should_retry and not should_retry(e):
                        logger.info(
                            f"Not retrying '{func.__name__}': exception {type(e).__name__} not eligible for retry"
                        )
                        break

                    # Don't retry on the last attempt
                    if attempts > max_retries:
                        break

                    # Call on_retry callback if provided
                    if on_retry:
                        on_retry(e, attempts)

                # Wait before retrying
                if attempts <= max_retries:
                    if exponential_backoff:
                        # Use exponential backoff formula: delay * 2^(attempt-1)
                        current_delay = retry_delay * (2 ** (attempts - 1))
                    else:
                        current_delay = retry_delay

                    logger.info(
                        f"Retrying '{func.__name__}' in {current_delay:.2f} seconds"
                    )
                    await asyncio.sleep(current_delay)

            # If we got here, all attempts failed
            if last_exception:
                raise last_exception

        return wrapper  # type: ignore

    return decorator
