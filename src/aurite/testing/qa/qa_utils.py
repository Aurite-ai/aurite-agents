"""
QA Testing Utilities for the Aurite Testing Framework.

This module provides shared utilities for Quality Assurance testing,
including component execution, schema validation, expectation analysis,
and result processing.
"""

import inspect
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import jsonschema

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.models.config.components import LLMConfig

from ..runners.agent_runner import AgentRunner
from .qa_models import ExpectationAnalysisResult, SchemaValidationResult

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine
    from aurite.lib.models.api.requests import EvaluationCase

    from .qa_models import QATestRequest

logger = logging.getLogger(__name__)


async def execute_component(
    case: "EvaluationCase",
    request: "QATestRequest",
    executor: Optional["AuriteEngine"] = None,
) -> Any:
    """
    Generic component execution supporting multiple execution patterns.

    This function handles:
    1. Pre-recorded outputs (case.output is provided)
    2. Custom execution functions (run_agent parameter)
    3. Standard component execution via AuriteEngine

    Args:
        case: The test case to execute
        request: The QA test request containing execution parameters
        executor: Optional AuriteEngine for standard component execution

    Returns:
        The output from the component execution

    Raises:
        ValueError: If no execution method is available or configured
    """
    # If output is already provided, use it
    if case.output is not None:
        logger.debug(f"Using pre-recorded output for case {case.id}")
        return case.output

    # Check for custom execution function (legacy run_agent support)
    run_agent = getattr(request, "run_agent", None)
    if run_agent:
        logger.debug(f"Using custom execution function for case {case.id}")
        run_agent_kwargs = getattr(request, "run_agent_kwargs", {})

        if isinstance(run_agent, str):
            # It's an agent name
            runner = AgentRunner(run_agent)
            return await runner.execute(case.input, **run_agent_kwargs)
        elif inspect.iscoroutinefunction(run_agent):
            # It's an async function
            return await run_agent(case.input, **run_agent_kwargs)
        else:
            # It's a regular callable
            return run_agent(case.input, **run_agent_kwargs)

    # Standard component execution via AuriteEngine
    if not executor:
        raise ValueError(f"Case {case.id}: No output provided and no executor available to run component")

    # Get component name from component_config or component_refs
    component_name = request.component_config.get("name")
    if not component_name and hasattr(request, "component_refs") and request.component_refs:
        # For multi-component requests, use the first component name as fallback
        component_name = request.component_refs[0]

    if not component_name:
        raise ValueError(f"Case {case.id}: No component name specified for execution")

    component_type = request.component_type
    logger.debug(f"Executing {component_type} '{component_name}' for case {case.id}")

    # Execute based on component type
    if component_type == "agent":
        result = await executor.run_agent(
            agent_name=component_name,
            user_message=case.input,
        )
        # Return formatted conversation history for agents
        return _format_agent_conversation_history(result)

    elif component_type in ["workflow", "linear_workflow"]:
        return await executor.run_linear_workflow(
            workflow_name=component_name,
            initial_input=case.input,
        )

    elif component_type == "custom_workflow":
        return await executor.run_custom_workflow(
            workflow_name=component_name,
            initial_input=case.input,
        )

    else:
        raise ValueError(f"Unsupported component type for execution: {component_type}")


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


async def analyze_expectations(
    case: "EvaluationCase",
    output: Any,
    llm_client: LiteLLMClient,
    component_context: Optional[Dict[str, Any]] = None,
) -> ExpectationAnalysisResult:
    """
    Use an LLM to analyze whether the output meets the expectations.

    Args:
        case: The test case with expectations
        output: The output to analyze
        llm_client: The LLM client to use for analysis
        component_context: Optional context about the component being tested

    Returns:
        ExpectationAnalysisResult with the analysis
    """
    expectations_str = "\n".join(case.expectations)

    # Build system prompt based on component context
    system_prompt = _build_analysis_system_prompt(component_context)

    analysis_output = await llm_client.create_message(
        messages=[
            {
                "role": "user",
                "content": f"Expectations:\n{expectations_str}\n\nInput: {case.input}\n\nOutput: {output}",
            }
        ],
        tools=None,
        system_prompt_override=system_prompt,
    )

    analysis_text = analysis_output.content

    if analysis_text is None:
        raise ValueError("Evaluation LLM returned no content")

    try:
        # Clean the output and parse JSON
        cleaned_output = clean_llm_output(analysis_text)
        analysis_json = json.loads(cleaned_output)

        return ExpectationAnalysisResult(
            analysis=analysis_json.get("analysis", "No analysis provided"),
            expectations_broken=analysis_json.get("expectations_broken", []),
        )

    except Exception as e:
        logger.error(f"Error parsing LLM analysis output: {e}")
        # Return a failed analysis
        return ExpectationAnalysisResult(
            analysis=f"Failed to parse LLM output: {str(e)}",
            expectations_broken=case.expectations,  # Assume all failed if we can't parse
        )


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


async def get_llm_client(
    review_llm: Optional[str] = None,
    config_manager=None,
) -> LiteLLMClient:
    """
    Get or create an LLM client for evaluation.

    Args:
        review_llm: Optional LLM configuration ID to use
        config_manager: Optional ConfigManager for loading LLM configs

    Returns:
        LiteLLMClient for evaluation
    """
    if review_llm and config_manager:
        # Use the specified LLM configuration
        llm_config = config_manager.get_config(component_type="llm", component_id=review_llm)

        if not llm_config:
            raise ValueError(f"No config found for LLM: {review_llm}")

        return LiteLLMClient(LLMConfig(**llm_config))
    else:
        # Use default Anthropic configuration
        default_config = LLMConfig(
            name="Default QA Evaluator",
            type="llm",
            model="claude-3-5-sonnet-20241022",
            provider="anthropic",
            temperature=0.1,
        )
        return LiteLLMClient(default_config)


def generate_basic_recommendations(results: List, component_type: Optional[str] = None) -> List[str]:
    """
    Generate basic recommendations based on test results.

    Args:
        results: List of case evaluation results
        component_type: Optional component type for context

    Returns:
        List of basic recommendation strings
    """
    if not results:
        return []

    recommendations = []

    # Calculate statistics
    failed_cases = [r for r in results if r.grade == "FAIL"]

    if not failed_cases:
        recommendations.append("All test cases passed successfully.")
        return recommendations

    # Analyze failure patterns
    failure_rate = len(failed_cases) / len(results)

    if failure_rate > 0.5:
        recommendations.append(
            f"High failure rate ({failure_rate:.1%}). Consider reviewing the component's core functionality."
        )

    # Check for schema failures
    schema_failures = [r for r in failed_cases if not r.schema_valid]
    if schema_failures:
        recommendations.append(
            f"{len(schema_failures)} cases failed schema validation. "
            "Ensure the component outputs data in the expected format."
        )

    # Analyze broken expectations
    all_broken_expectations = []
    for result in failed_cases:
        all_broken_expectations.extend(result.expectations_broken)

    if all_broken_expectations:
        # Find most common broken expectations
        from collections import Counter

        expectation_counts = Counter(all_broken_expectations)
        most_common = expectation_counts.most_common(3)

        for expectation, count in most_common:
            if count > 1:
                recommendations.append(f"Expectation '{expectation}' failed in {count} cases.")

    return recommendations


def _format_agent_conversation_history(result) -> str:
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


def _build_analysis_system_prompt(component_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Build a system prompt for expectation analysis based on component context.

    Args:
        component_context: Optional context about the component being tested

    Returns:
        System prompt string for the LLM
    """
    base_prompt = """You are an expert Quality Assurance Engineer. Your job is to review the output from a component and make sure it meets a list of expectations.
Your output should be your analysis of its performance, and a list of which expectations were broken (if any). These strings should be identical to the original expectation strings.

Format your output as JSON. IMPORTANT: Do not include any other text before or after, and do NOT format it as a code block (```). Here is a template: {
"analysis": "<your analysis here>",
"expectations_broken": ["<broken expectation 1>", "<broken expectation 2>", "etc"]
}"""

    if not component_context:
        return base_prompt

    # Add component-specific context
    component_type = component_context.get("type", "component")
    component_name = component_context.get("name", "Unknown")

    context_prompt = f"""You are an expert Quality Assurance Engineer specializing in {component_type} evaluation.

You are evaluating a {component_type} with the following configuration:
- Component Name: {component_name}
- Component Type: {component_type}"""

    # Add type-specific context
    if component_type == "agent":
        system_prompt_text = component_context.get("system_prompt", "Not specified")
        truncated_prompt = system_prompt_text[:200] + "..." if len(system_prompt_text) > 200 else system_prompt_text

        context_prompt += f"""
- System Prompt: {truncated_prompt}
- Tools Available: {", ".join(component_context.get("tools", [])) or "None"}
- Temperature: {component_context.get("temperature", "Not specified")}

Focus on:
1. Goal Achievement: Did the agent accomplish what was asked?
2. Response Quality: Is the response coherent, relevant, and complete?
3. Tool Usage: If tools were available, were they used appropriately?
4. System Prompt Adherence: Does the response follow the agent's behavioral guidelines?"""

    elif component_type in ["workflow", "linear_workflow", "custom_workflow"]:
        steps = component_context.get("steps", [])
        step_names = []
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict):
                    step_names.append(step.get("name", "unnamed"))
                elif isinstance(step, str):
                    step_names.append(step)

        context_prompt += f"""
- Workflow Type: {component_context.get("type", "linear_workflow")}
- Number of Steps: {len(steps)}
- Step Names: {", ".join(step_names) if step_names else "Not specified"}
- Timeout: {component_context.get("timeout_seconds", "Not specified")} seconds
- Parallel Execution: {component_context.get("parallel_execution", False)}

Focus on:
1. End-to-End Execution: Did the workflow complete successfully from start to finish?
2. Agent Coordination: Do the results show proper coordination between workflow steps?
3. Data Flow Integrity: Is the data properly transformed and passed between steps?
4. Step Validation: Are individual steps executing correctly?"""

    context_prompt += f"""

Your job is to review the {component_type}'s output and determine if it meets the specified expectations.

Format your output as JSON. IMPORTANT: Do not include any other text before or after, and do NOT format it as a code block (```). Here is the template:
{{
"analysis": "<your detailed analysis here>",
"expectations_broken": ["<broken expectation 1>", "<broken expectation 2>", "etc"]
}}"""

    return context_prompt
