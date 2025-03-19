"""
Evaluation server for Aurite agents.

This module implements an MCP server with tools for evaluating agent outputs
based on configurable rubrics.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List

from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize the FastMCP server
mcp = FastMCP("evaluation-server")

# Define constants
EVALUATIONS_DIR = Path("evaluations")
os.makedirs(EVALUATIONS_DIR, exist_ok=True)


@mcp.tool("evaluate_agent")
def evaluate_agent(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluate agent output against specified criteria or a rubric.

    Args:
        agent_output: The output from the agent to evaluate
        criteria: Evaluation criteria as a structured object or rubric name
        expected_output: Optional expected output for comparison
        detailed_feedback: Whether to provide detailed feedback (default: True)

    Returns:
        Evaluation results with scores and feedback
    """
    # Extract arguments
    agent_output = arguments.get("agent_output", "")
    criteria = arguments.get("criteria", {})
    expected_output = arguments.get("expected_output", "")
    detailed_feedback = arguments.get("detailed_feedback", True)

    # Log evaluation request
    logger.info(f"Evaluating agent output against {len(criteria)} criteria")

    # Perform evaluation
    # In a real implementation, this would analyze the content against criteria
    # Here we'll return a simplified mock response

    result = {
        "score": 4.2,
        "passed": True,
        "criterion_scores": {
            "accuracy": {
                "score": 4.0,
                "justification": "The agent provided mostly accurate information with only minor imprecisions.",
            },
            "relevance": {
                "score": 4.5,
                "justification": "The output thoroughly addressed the query with comprehensive coverage.",
            },
            "coherence": {
                "score": 4.0,
                "justification": "The response was well-structured and easy to follow.",
            },
            "completeness": {
                "score": 4.3,
                "justification": "The output provided comprehensive coverage of the topic.",
            },
        },
        "summary_feedback": "Overall, the agent performed well, providing a comprehensive and accurate response that was well-structured.",
        "strengths": [
            "Thorough coverage of the topic",
            "Well-organized presentation",
            "Accurate information",
        ],
        "areas_for_improvement": [
            "Could provide more specific examples",
            "Minor inaccuracies in some details",
        ],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Save evaluation result
    save_evaluation_result(result, agent_output, expected_output)

    return [{"type": "text", "text": json.dumps(result)}]


@mcp.tool("score_agent")
def score_agent(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Score agent output using a specified rubric, returning a numeric score.

    Args:
        agent_output: The output from the agent to score
        rubric: The rubric to use for scoring (name or full rubric object)

    Returns:
        Numeric scores with minimal feedback
    """
    # Extract arguments
    agent_output = arguments.get("agent_output", "")
    rubric_spec = arguments.get("rubric", {})

    # Log scoring request
    logger.info("Scoring agent output with rubric")

    # Perform scoring
    # In a real implementation, this would score based on the rubric
    # Here we'll return a simplified mock response

    result = {
        "overall_score": 4.2,
        "criterion_scores": {
            "accuracy": 4.0,
            "relevance": 4.5,
            "coherence": 4.0,
            "completeness": 4.3,
        },
        "passed": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    return [{"type": "text", "text": json.dumps(result)}]


@mcp.tool("analyze_agent_performance")
def analyze_agent_performance(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyze agent performance in detail, providing comprehensive feedback.

    Args:
        agent_output: The output from the agent to analyze
        expected_output: Expected output for comparison
        analysis_type: Type of analysis to perform (standard, detailed, focused)
        focus_areas: Specific areas to focus on (if analysis_type is focused)

    Returns:
        Detailed analysis with qualitative feedback
    """
    # Extract arguments
    agent_output = arguments.get("agent_output", "")
    expected_output = arguments.get("expected_output", "")
    analysis_type = arguments.get("analysis_type", "standard")
    focus_areas = arguments.get("focus_areas", [])

    # Log analysis request
    logger.info(f"Analyzing agent performance with {analysis_type} analysis")

    # Perform analysis
    # In a real implementation, this would perform a detailed analysis
    # Here we'll return a simplified mock response

    result = {
        "analysis_type": analysis_type,
        "strengths": [
            {"area": "Content", "description": "Comprehensive coverage of the topic"},
            {"area": "Structure", "description": "Well-organized with logical flow"},
            {"area": "Accuracy", "description": "Mostly accurate information"},
        ],
        "areas_for_improvement": [
            {"area": "Detail", "description": "Could provide more specific examples"},
            {"area": "Precision", "description": "Some minor inaccuracies in details"},
        ],
        "comparison_with_expected": {
            "similarity_score": 0.85,
            "key_differences": [
                "Expected output included more specific data points",
                "Agent provided better organization than expected output",
            ],
        },
        "recommendations": [
            "Improve fact-checking for higher accuracy",
            "Include more specific examples to support points",
            "Consider adding quantitative data where appropriate",
        ],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    return [{"type": "text", "text": json.dumps(result)}]


@mcp.tool("aggregate_evaluations")
def aggregate_evaluations(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Aggregate multiple evaluation results to produce statistics.

    Args:
        evaluation_ids: List of evaluation IDs to aggregate
        agent_id: Optional agent ID to filter evaluations
        rubric_id: Optional rubric ID to filter evaluations

    Returns:
        Aggregated statistics and meta-analysis
    """
    # Extract arguments
    evaluation_ids = arguments.get("evaluation_ids", [])
    agent_id = arguments.get("agent_id", None)
    rubric_id = arguments.get("rubric_id", None)

    # Log aggregation request
    eval_count = len(evaluation_ids)
    logger.info(f"Aggregating {eval_count} evaluation results")

    # In a real implementation, this would load and aggregate evaluations
    # Here we'll return a simplified mock response

    result = {
        "mean_score": 4.15,
        "median_score": 4.2,
        "min_score": 3.8,
        "max_score": 4.5,
        "std_deviation": 0.25,
        "pass_rate": 1.0,
        "criterion_mean_scores": {
            "accuracy": 4.1,
            "relevance": 4.3,
            "coherence": 4.0,
            "completeness": 4.2,
        },
        "criterion_std_deviations": {
            "accuracy": 0.3,
            "relevance": 0.2,
            "coherence": 0.3,
            "completeness": 0.25,
        },
        "common_strengths": [
            "Strong organization and structure",
            "Comprehensive topic coverage",
        ],
        "common_areas_for_improvement": [
            "Increase specificity with examples",
            "Improve factual accuracy in details",
        ],
        "summary": "Across all evaluations, the agent demonstrates consistently strong performance with particular strengths in organization and comprehensive coverage. The main areas for improvement are increasing specificity and fact-checking for greater accuracy.",
        "num_runs": eval_count,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    return [{"type": "text", "text": json.dumps(result)}]


@mcp.tool("list_evaluations")
def list_evaluations(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    List available evaluation results with optional filtering.

    Args:
        agent_id: Optional agent ID to filter evaluations
        rubric_id: Optional rubric ID to filter evaluations
        min_score: Optional minimum score threshold
        max_results: Maximum number of results to return (default: 10)

    Returns:
        List of matching evaluation results
    """
    # Extract arguments
    agent_id = arguments.get("agent_id", None)
    rubric_id = arguments.get("rubric_id", None)
    min_score = arguments.get("min_score", None)
    max_results = arguments.get("max_results", 10)

    # In a real implementation, this would search stored evaluations
    # Here we'll return a simplified mock response

    # Get evaluations from the directory
    evaluations = []
    try:
        for eval_file in EVALUATIONS_DIR.glob("*.json"):
            try:
                with open(eval_file, "r") as f:
                    evaluation = json.load(f)

                    # Apply filters if provided
                    if agent_id and evaluation.get("agent_id") != agent_id:
                        continue
                    if rubric_id and evaluation.get("rubric_id") != rubric_id:
                        continue
                    if min_score and evaluation.get("overall_score", 0) < min_score:
                        continue

                    evaluations.append(
                        {
                            "id": eval_file.stem,
                            "timestamp": evaluation.get("timestamp", ""),
                            "overall_score": evaluation.get("overall_score", 0),
                            "agent_id": evaluation.get("agent_id", "unknown"),
                            "rubric_id": evaluation.get("rubric_id", "unknown"),
                        }
                    )

                    if len(evaluations) >= max_results:
                        break
            except Exception as e:
                logger.error(f"Error loading evaluation {eval_file}: {e}")
    except Exception as e:
        logger.error(f"Error listing evaluations: {e}")

    # If no real evaluations were found or there was an error, return mock data
    if not evaluations:
        evaluations = [
            {
                "id": "eval_001",
                "timestamp": "2025-03-18 15:30:45",
                "overall_score": 4.2,
                "agent_id": "planning_agent",
                "rubric_id": "standard_rubric",
            },
            {
                "id": "eval_002",
                "timestamp": "2025-03-18 16:15:22",
                "overall_score": 3.8,
                "agent_id": "qa_agent",
                "rubric_id": "qa_rubric",
            },
        ]

    result = {
        "evaluations": evaluations,
        "count": len(evaluations),
        "filters_applied": {
            "agent_id": agent_id,
            "rubric_id": rubric_id,
            "min_score": min_score,
        },
    }

    return [{"type": "text", "text": json.dumps(result)}]


@mcp.prompt()
def evaluation_prompt() -> str:
    """
    System prompt for agent evaluation.

    This prompt guides the model in evaluating agent outputs using
    rubric-based assessment, ensuring thorough and consistent evaluation.
    """
    return """# Agent Evaluator

You are an expert evaluator of AI agent outputs. Your job is to assess the quality, accuracy, and effectiveness of outputs produced by AI agents based on specified criteria.

## Evaluation Process

1. Carefully review the agent's output
2. Evaluate each criterion based on the provided rubric
3. Provide a detailed justification for each score
4. Identify specific strengths and areas for improvement
5. Synthesize an overall assessment

## Evaluation Principles

- Be objective and consistent in your assessments
- Consider the specific task and context of the agent's work
- Provide specific examples from the agent's output to support your evaluation
- Be constructive in your feedback
- Follow the rubric strictly while providing nuanced assessment

## Using the evaluate_agent Tool

Use the `evaluate_agent` tool to conduct formal evaluations. This tool accepts:
- The agent's output
- A rubric or criteria specification
- Optional expected output for comparison
- Whether to provide detailed feedback

The tool will store your evaluation for record-keeping and analysis.

Example usage:
```
{
  "agent_output": "The complete text output from the agent",
  "criteria": {
    "accuracy": {
      "description": "Correctness of information",
      "weight": 0.3,
      "scoring": {
        "1": "Contains significant errors",
        "5": "Perfectly accurate"
      }
    },
    ...more criteria...
  },
  "expected_output": "Optional reference output for comparison",
  "detailed_feedback": true
}
```

## Additional Tools

- `score_agent` - Provides numeric scoring with minimal feedback
- `analyze_agent_performance` - Provides in-depth analysis of specific aspects
- `aggregate_evaluations` - Combines multiple evaluation results for statistical analysis
- `list_evaluations` - Lists existing evaluations with filtering options

Focus on providing fair, thorough, and constructive evaluations that can help improve agent performance."""


@mcp.prompt()
def rubric_prompt() -> str:
    """
    System prompt for using evaluation rubrics.

    This prompt guides the model in applying rubrics consistently
    for evaluating agent outputs.
    """
    return """# Rubric-Based Evaluation Guide

You are applying a standardized rubric to evaluate AI agent outputs. Follow these guidelines to ensure consistent and fair evaluations.

## Understanding Rubrics

A rubric consists of:
- Criteria: Specific aspects of performance to evaluate
- Weights: The importance of each criterion
- Scoring scales: Defined levels of performance for each criterion
- Descriptions: What each score means for each criterion

## How to Apply the Rubric

For each criterion:
1. Review the criterion description and scoring scale
2. Examine the agent output specifically for this aspect
3. Compare the output to each level in the scoring scale
4. Select the score that best matches the output
5. Provide specific examples from the output to justify your score

## Important Considerations

- Use the full range of the scoring scale appropriately
- Be consistent in how you apply the same criterion across evaluations
- Evaluate each criterion independently before considering the overall score
- Consider only the evidence present in the agent output
- Be specific in your justifications, citing concrete examples

## Calculating Overall Scores

The overall score is calculated as a weighted average:
- Multiply each criterion score by its weight
- Sum these weighted scores
- Ensure the result is on the same scale as the individual criteria

## Example Criterion Evaluation

Criterion: Accuracy (Weight: 0.3)
Scoring Scale:
- 1: Contains significant factual errors
- 2: Contains minor factual errors
- 3: Mostly accurate with some imprecisions
- 4: Highly accurate with minimal issues
- 5: Perfectly accurate information

Assessment: The agent output claims that "Python was created in 1991," which is correct, but incorrectly states that "Python 3.0 was released in 2007" (actually released in 2008). It provides accurate information about Python's features and use cases. These are minor factual errors.

Score: 2 - Contains minor factual errors

Justification: While most of the information is accurate, there are specific factual errors regarding the release date of Python 3.0. The output states it was released in 2007, but it was actually released in December 2008. This represents a minor factual error in an otherwise mostly accurate response."""


# Helper functions


def save_evaluation_result(
    result: Dict[str, Any], agent_output: str, expected_output: str
) -> None:
    """Save evaluation result to a file."""
    try:
        timestamp = time.strftime("%Y%m%d%H%M%S")
        evaluation_id = f"eval_{timestamp}"

        # Add agent output and expected output to result
        full_result = result.copy()
        full_result["agent_output"] = agent_output
        full_result["expected_output"] = expected_output

        # Save to file
        eval_path = EVALUATIONS_DIR / f"{evaluation_id}.json"
        with open(eval_path, "w") as f:
            json.dump(full_result, f, indent=2)

        logger.info(f"Saved evaluation to {eval_path}")
    except Exception as e:
        logger.error(f"Error saving evaluation: {e}")


# Run the server if executed directly
if __name__ == "__main__":
    mcp.run(transport="stdio")
