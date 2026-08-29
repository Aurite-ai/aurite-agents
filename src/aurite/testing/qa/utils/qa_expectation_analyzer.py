"""
Expectation analysis for QA testing.

This module provides LLM-based expectation analysis functionality.
"""

import json
import logging
from typing import Any, Dict, Optional

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.models.config.components import EvaluationCase

from ..qa_models import ExpectationAnalysisResult
from .qa_utils import clean_llm_output

logger = logging.getLogger(__name__)


async def analyze_expectations(
    case: EvaluationCase,
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
    system_prompt = build_analysis_system_prompt(component_context)

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


def build_analysis_system_prompt(component_context: Optional[Dict[str, Any]] = None) -> str:
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
- Tools Available: {", ".join(component_context.get("mcp_servers", [])) or "None"}
- Temperature: {component_context.get("temperature", "Not specified")}

Focus on:
1. Goal Achievement: Did the agent accomplish what was asked?
2. Response Quality: Is the response coherent, relevant, and complete?
3. Tool Usage: If tools were available, were they used appropriately?
4. System Prompt Adherence: Does the response follow the agent's behavioral guidelines?"""

    elif component_type in ["workflow", "linear_workflow"]:
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
