"""
QA Testing Utility Functions for the Aurite Testing Framework.

This module provides pure utility functions for Quality Assurance testing,
including schema validation, LLM output cleaning, and conversation formatting.
"""

import json
import logging
from typing import Any, Dict

import jsonschema

from .qa_models import SchemaValidationResult

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
    index = output.find("{")
    if index > 0:
        output = output[index:]

    # Remove newlines for cleaner parsing
    output = output.replace("\n", " ")

    return output.strip()


def format_agent_conversation_history(result) -> str:
    """
    Format the full conversation history from an AgentRunResult for evaluation.

    Args:
        result: AgentRunResult containing conversation history

    Returns:
        Formatted string representation of the full conversation including tool calls
    """
    formatted_output = []

    # Add conversation history if available
    if hasattr(result, "conversation_history") and result.conversation_history:
        formatted_output.append("=== FULL CONVERSATION HISTORY ===\n")

        for _i, message in enumerate(result.conversation_history):
            role = message.get("role", "unknown")
            content = message.get("content", "")

            # Format based on role
            if role == "user":
                formatted_output.append(f"USER: {content}\n")
            elif role == "assistant":
                formatted_output.append(f"ASSISTANT: {content}\n")
            elif role == "tool":
                # Tool responses
                tool_name = message.get("name", "unknown_tool")
                formatted_output.append(f"TOOL RESPONSE ({tool_name}): {content}\n")

            # Check for tool calls in assistant messages
            if role == "assistant" and "tool_calls" in message:
                for tool_call in message["tool_calls"]:
                    if isinstance(tool_call, dict):
                        function = tool_call.get("function", {})
                        tool_name = function.get("name", "unknown")
                        tool_args = function.get("arguments", "{}")
                        formatted_output.append(f"TOOL CALL: {tool_name}\n")
                        formatted_output.append(f"ARGUMENTS: {tool_args}\n")

        formatted_output.append("\n=== FINAL RESPONSE ===\n")

    # Add the final response
    if hasattr(result, "primary_text") and result.primary_text:
        formatted_output.append(result.primary_text)
    elif hasattr(result, "final_response") and result.final_response:
        formatted_output.append(
            str(result.final_response.content if hasattr(result.final_response, "content") else result.final_response)
        )

    return "".join(formatted_output)
