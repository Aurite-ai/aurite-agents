"""
QA Testing Utility Functions for the Aurite Testing Framework.

This module provides pure utility functions for Quality Assurance testing,
including schema validation, LLM output cleaning, and conversation formatting.
"""

import json
import logging
from typing import Any, Dict

import jsonschema

from ..qa_models import SchemaValidationResult

logger = logging.getLogger(__name__)


def validate_schema(output: Any, expected_schema: Dict[str, Any]) -> SchemaValidationResult:
    """
    Validate output against an expected JSON schema.

    Args:
        output: The output to validate
        expected_schema: The JSON schema to validate against

    Returns:
        SchemaValidationResult with validation details
    """
    try:
        # Convert output to JSON if it's a string
        if isinstance(output, str):
            try:
                data_to_validate = json.loads(output)
            except json.JSONDecodeError:
                return SchemaValidationResult(
                    is_valid=False,
                    error_message="Output is not valid JSON",
                    validation_errors=["Failed to parse output as JSON"],
                )
        elif isinstance(output, dict):
            data_to_validate = output
        else:
            return SchemaValidationResult(
                is_valid=False,
                error_message="Output is not a string or dictionary",
                validation_errors=[f"Unexpected output type: {type(output).__name__}"],
            )

        # Validate against schema
        jsonschema.validate(instance=data_to_validate, schema=expected_schema)

        return SchemaValidationResult(is_valid=True, error_message=None, validation_errors=[])

    except jsonschema.ValidationError as e:
        return SchemaValidationResult(is_valid=False, error_message=e.message, validation_errors=[e.message])
    except jsonschema.SchemaError as e:
        return SchemaValidationResult(
            is_valid=False,
            error_message=f"Invalid schema: {e.message}",
            validation_errors=[f"Schema error: {e.message}"],
        )
    except Exception as e:
        return SchemaValidationResult(is_valid=False, error_message=str(e), validation_errors=[str(e)])


def clean_llm_output(output: str) -> str:
    """
    Clean LLM output to extract JSON.

    Removes thinking tags and other preambles to get clean JSON.
    Also handles trailing content after the JSON object.

    Args:
        output: Raw LLM output

    Returns:
        Cleaned JSON string
    """
    # Remove thinking tags if present
    if "</thinking>" in output:
        index = output.rfind("</thinking>")
        output = output[index + len("</thinking>") :]

    # Find the first curly brace
    start_index = output.find("{")
    if start_index == -1:
        # No JSON found
        return output.strip()

    # Find the matching closing brace using brace counting
    brace_count = 0
    end_index = -1
    in_string = False
    escape_next = False

    for i in range(start_index, len(output)):
        char = output[i]

        # Handle string literals to avoid counting braces inside strings
        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        # Only count braces outside of strings
        if not in_string:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    # Found the matching closing brace
                    end_index = i
                    break

    if end_index != -1:
        # Extract just the JSON portion
        output = output[start_index : end_index + 1]
    else:
        # Fallback to original behavior if we couldn't find matching brace
        output = output[start_index:]

    # Remove newlines for cleaner parsing
    output = output.replace("\n", " ")

    return output.strip()


def filter_test_cases(test_cases: list, filter_str: str) -> list:
    """
    Filter test cases based on the provided filter string.

    Supports:
    - Comma-separated names: "test1,test2"
    - Index ranges: "0-2" (indices 0, 1, 2)
    - Single indices: "0,2,4"
    - Mixed: "test1,0-2,test5"
    - Regex patterns: "/pattern/" or "regex:pattern"

    Args:
        test_cases: List of test case dictionaries
        filter_str: Filter string

    Returns:
        Filtered list of test cases
    """
    import re

    filtered = []
    filters = [f.strip() for f in filter_str.split(",")]

    for filter_item in filters:
        # Check for regex pattern
        if filter_item.startswith("/") and filter_item.endswith("/"):
            # Regex pattern
            pattern = filter_item[1:-1]
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                for case in test_cases:
                    name = case.get("name", "")
                    if regex.search(name) and case not in filtered:
                        filtered.append(case)
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")

        elif filter_item.startswith("regex:"):
            # Alternative regex syntax
            pattern = filter_item[6:]
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                for case in test_cases:
                    name = case.get("name", "")
                    if regex.search(name) and case not in filtered:
                        filtered.append(case)
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")

        elif "-" in filter_item and filter_item.replace("-", "").isdigit():
            # Index range (e.g., "0-2")
            parts = filter_item.split("-")
            if len(parts) == 2:
                try:
                    start = int(parts[0])
                    end = int(parts[1])
                    for i in range(start, min(end + 1, len(test_cases))):
                        if test_cases[i] not in filtered:
                            filtered.append(test_cases[i])
                except (ValueError, IndexError) as e:
                    logger.warning(f"Invalid index range '{filter_item}': {e}")

        elif filter_item.isdigit():
            # Single index
            try:
                idx = int(filter_item)
                if 0 <= idx < len(test_cases) and test_cases[idx] not in filtered:
                    filtered.append(test_cases[idx])
            except (ValueError, IndexError) as e:
                logger.warning(f"Invalid index '{filter_item}': {e}")

        else:
            # Test case name
            for case in test_cases:
                if case.get("name", "") == filter_item and case not in filtered:
                    filtered.append(case)

    # Preserve original order
    return [case for case in test_cases if case in filtered]
