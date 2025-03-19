"""
Evaluation workflow for assessing agent outputs.

This module implements a workflow for evaluating AI agent outputs
based on configurable rubrics, with support for multi-run evaluations
and statistical aggregation.
"""

import logging
import statistics
import json
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union

# Import needed for ClientConfig
from ...host.config import ClientConfig

# Import required framework components
from ..base_workflow import BaseWorkflow, WorkflowStep
from ..base_models import AgentContext, StepStatus
from .models import (
    create_standard_rubric,
    create_qa_rubric,
    create_planning_rubric,
    create_analysis_rubric,
    create_creative_rubric,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class EvaluateAgentStep(WorkflowStep):
    """
    Step to evaluate an agent's output against a rubric.
    """

    def __init__(self):
        super().__init__(
            name="evaluate_agent",
            description="Evaluate agent output against specified criteria",
            required_inputs={"agent_output", "rubric"},
            provided_outputs={"evaluation_result"},
            required_tools={"evaluate_agent"},
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the evaluation step."""
        # Extract required inputs
        agent_output = context.get("agent_output", "")
        rubric = context.get("rubric", {})
        expected_output = context.get("expected_output", "")
        detailed_feedback = context.get("detailed_feedback", True)

        logger.info(
            f"Evaluating agent output with {len(rubric.get('criteria', {}))} criteria"
        )

        # Build arguments for the tool
        tool_args = {
            "agent_output": agent_output,
            "criteria": rubric,
            "expected_output": expected_output,
            "detailed_feedback": detailed_feedback,
        }

        # Execute the evaluation tool
        result = await context.host.tools.execute_tool("evaluate_agent", tool_args)

        # Parse the result - assuming it's returned as JSON text
        try:
            if isinstance(result, list) and len(result) > 0:
                if hasattr(result[0], "text"):
                    evaluation_result = json.loads(result[0].text)
                else:
                    evaluation_result = result[0]
            else:
                # Fallback to string parsing
                evaluation_result = json.loads(str(result))

            # Add metadata
            evaluation_result["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

            logger.info(
                f"Evaluation complete with score: {evaluation_result.get('score', 'unknown')}"
            )

            return {
                "evaluation_result": evaluation_result,
                "raw_tool_result": result,
            }
        except Exception as e:
            logger.error(f"Error parsing evaluation result: {e}")
            return {
                "evaluation_result": {"error": str(e)},
                "raw_tool_result": result,
            }


@dataclass
class AggregateEvaluationsStep(WorkflowStep):
    """
    Step to aggregate multiple evaluation results.
    """

    def __init__(self):
        super().__init__(
            name="aggregate_evaluations",
            description="Aggregate multiple evaluation results",
            required_inputs={"evaluation_results"},
            provided_outputs={"aggregated_result"},
            required_tools={"aggregate_evaluations"},
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the aggregation step."""
        # Extract required inputs
        evaluation_results = context.get("evaluation_results", [])
        evaluation_ids = context.get("evaluation_ids", [])
        agent_id = context.get("agent_id", None)
        rubric_id = context.get("rubric_id", None)

        # If we have evaluation_ids, use those directly
        if evaluation_ids:
            logger.info(f"Aggregating {len(evaluation_ids)} evaluations by ID")

            # Build arguments for the tool
            tool_args = {
                "evaluation_ids": evaluation_ids,
                "agent_id": agent_id,
                "rubric_id": rubric_id,
            }

            # Execute the aggregation tool
            result = await context.host.tools.execute_tool(
                "aggregate_evaluations", tool_args
            )

        # Otherwise, perform aggregation in-memory using the provided results
        else:
            logger.info(
                f"Aggregating {len(evaluation_results)} evaluation results in-memory"
            )

            # Compute aggregated statistics
            aggregated_result = self._compute_aggregated_stats(evaluation_results)

            # Return as if from the tool
            result = [{"type": "text", "text": json.dumps(aggregated_result)}]

        # Parse the result
        try:
            if isinstance(result, list) and len(result) > 0:
                if hasattr(result[0], "text"):
                    aggregated_result = json.loads(result[0].text)
                else:
                    aggregated_result = result[0]
            else:
                # Fallback to string parsing
                aggregated_result = json.loads(str(result))

            logger.info(
                f"Aggregation complete for {aggregated_result.get('num_runs', 0)} evaluations"
            )

            return {
                "aggregated_result": aggregated_result,
                "raw_tool_result": result,
            }
        except Exception as e:
            logger.error(f"Error parsing aggregation result: {e}")
            return {
                "aggregated_result": {"error": str(e)},
                "raw_tool_result": result,
            }

    def _compute_aggregated_stats(
        self, evaluation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compute aggregated statistics from a list of evaluation results."""
        # Extract overall scores
        scores = [
            result.get("score", 0) for result in evaluation_results if "score" in result
        ]
        if not scores:
            return {"error": "No valid scores found in evaluation results"}

        # Extract criterion scores
        criterion_scores = {}
        for result in evaluation_results:
            if "criterion_scores" in result:
                for criterion, data in result["criterion_scores"].items():
                    if criterion not in criterion_scores:
                        criterion_scores[criterion] = []

                    # Handle different formats
                    if isinstance(data, dict) and "score" in data:
                        criterion_scores[criterion].append(data["score"])
                    elif isinstance(data, (int, float)):
                        criterion_scores[criterion].append(data)

        # Compute statistics
        mean_score = statistics.mean(scores) if scores else 0
        median_score = statistics.median(scores) if scores else 0
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0

        # Compute criterion statistics
        criterion_means = {}
        criterion_std_devs = {}

        for criterion, c_scores in criterion_scores.items():
            if c_scores:
                criterion_means[criterion] = statistics.mean(c_scores)
                if len(c_scores) > 1:
                    criterion_std_devs[criterion] = statistics.stdev(c_scores)
                else:
                    criterion_std_devs[criterion] = 0

        # Determine pass rate
        if "passed" in evaluation_results[0]:
            passing = sum(1 for r in evaluation_results if r.get("passed", False))
            pass_rate = passing / len(evaluation_results)
        else:
            pass_rate = None

        # Collect common strengths and areas for improvement
        all_strengths = []
        all_areas = []

        for result in evaluation_results:
            if "strengths" in result:
                all_strengths.extend(result["strengths"])
            if "areas_for_improvement" in result:
                all_areas.extend(result["areas_for_improvement"])

        # Count occurrences
        strength_counts = {}
        area_counts = {}

        for s in all_strengths:
            strength_counts[s] = strength_counts.get(s, 0) + 1

        for a in all_areas:
            area_counts[a] = area_counts.get(a, 0) + 1

        # Get the most common ones (appearing in at least 1/3 of evaluations)
        threshold = len(evaluation_results) / 3
        common_strengths = [
            s for s, count in strength_counts.items() if count >= threshold
        ]
        common_areas = [a for a, count in area_counts.items() if count >= threshold]

        # Create summary
        if mean_score >= 4.5:
            quality = "excellent"
        elif mean_score >= 4.0:
            quality = "very good"
        elif mean_score >= 3.5:
            quality = "good"
        elif mean_score >= 3.0:
            quality = "satisfactory"
        else:
            quality = "needs improvement"

        consistency = "highly consistent" if std_dev < 0.3 else "somewhat variable"

        summary = (
            f"Across {len(evaluation_results)} evaluations, the agent demonstrates {quality} "
            f"performance that is {consistency} (σ={std_dev:.2f}). "
        )

        if common_strengths:
            summary += f"Key strengths include {', '.join(common_strengths[:3])}. "

        if common_areas:
            summary += f"Areas for improvement include {', '.join(common_areas[:3])}."

        # Return the aggregated result
        return {
            "mean_score": mean_score,
            "median_score": median_score,
            "min_score": min(scores),
            "max_score": max(scores),
            "std_deviation": std_dev,
            "pass_rate": pass_rate,
            "criterion_mean_scores": criterion_means,
            "criterion_std_deviations": criterion_std_devs,
            "common_strengths": common_strengths,
            "common_areas_for_improvement": common_areas,
            "summary": summary,
            "num_runs": len(evaluation_results),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }


class EvaluationWorkflow(BaseWorkflow):
    """
    Workflow for evaluating agent outputs using rubric-based assessment.

    This workflow supports both single-run and multi-run evaluations,
    with statistical aggregation for the latter.
    """

    def __init__(
        self,
        host,
        name: str = "evaluation_workflow",
        client_config: Optional[ClientConfig] = None,
        workflow_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the evaluation workflow."""
        super().__init__(
            host=host,
            name=name,
            client_config=client_config,
            workflow_config=workflow_config,
        )

        # Set description
        self.description = "Workflow for evaluating agent outputs using rubrics"

        # Add the evaluation step
        self.add_step(EvaluateAgentStep())

        # Add the aggregation step
        self.add_step(AggregateEvaluationsStep())

    async def evaluate_agent(
        self,
        agent_output: str,
        rubric: Union[Dict[str, Any], str] = "standard",
        expected_output: str = "",
        detailed_feedback: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluate an agent's output using the specified rubric.

        Args:
            agent_output: The output from the agent to evaluate
            rubric: Either a rubric dict or a string name of a standard rubric
            expected_output: Optional expected output for comparison
            detailed_feedback: Whether to include detailed feedback

        Returns:
            Evaluation results
        """
        # If rubric is a string, load the appropriate standard rubric
        if isinstance(rubric, str):
            rubric_name = rubric.lower()
            if rubric_name == "qa" or rubric_name == "question_answering":
                rubric = create_qa_rubric().model_dump()
            elif rubric_name == "planning":
                rubric = create_planning_rubric().model_dump()
            elif rubric_name == "analysis":
                rubric = create_analysis_rubric().model_dump()
            elif rubric_name == "creative":
                rubric = create_creative_rubric().model_dump()
            else:  # Default to standard
                rubric = create_standard_rubric().model_dump()

        # Create input data
        input_data = {
            "agent_output": agent_output,
            "rubric": rubric,
            "expected_output": expected_output,
            "detailed_feedback": detailed_feedback,
            "multi_run": False,
        }

        # Execute the workflow
        result_context = await self.execute(input_data)

        # Return the summarized results
        return result_context.summarize_results()

    async def evaluate_multi_run(
        self,
        agent_output: str,
        rubric: Union[Dict[str, Any], str] = "standard",
        expected_output: str = "",
        num_runs: int = 3,
        detailed_feedback: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluate an agent's output multiple times and aggregate the results.

        Args:
            agent_output: The output from the agent to evaluate
            rubric: Either a rubric dict or a string name of a standard rubric
            expected_output: Optional expected output for comparison
            num_runs: Number of evaluation runs to perform
            detailed_feedback: Whether to include detailed feedback

        Returns:
            Aggregated evaluation results
        """
        # If rubric is a string, load the appropriate standard rubric
        if isinstance(rubric, str):
            rubric_name = rubric.lower()
            if rubric_name == "qa" or rubric_name == "question_answering":
                rubric = create_qa_rubric().model_dump()
            elif rubric_name == "planning":
                rubric = create_planning_rubric().model_dump()
            elif rubric_name == "analysis":
                rubric = create_analysis_rubric().model_dump()
            elif rubric_name == "creative":
                rubric = create_creative_rubric().model_dump()
            else:  # Default to standard
                rubric = create_standard_rubric().model_dump()

        # Run multiple evaluations
        evaluation_results = []
        for i in range(num_runs):
            logger.info(f"Starting evaluation run {i+1}/{num_runs}")

            # Create input data
            input_data = {
                "agent_output": agent_output,
                "rubric": rubric,
                "expected_output": expected_output,
                "detailed_feedback": detailed_feedback,
                "run_id": i + 1,
                "multi_run": True,
            }

            # Execute the workflow for just the evaluation step
            result_context = await self.execute(input_data)

            # Check if evaluation was successful
            step_result = result_context.step_results.get("evaluate_agent")
            if step_result and step_result.status == StepStatus.COMPLETED:
                # Get the evaluation result
                evaluation_result = result_context.get("evaluation_result")
                if evaluation_result:
                    evaluation_results.append(evaluation_result)

        # If we have results, aggregate them
        if evaluation_results:
            logger.info(f"Aggregating {len(evaluation_results)} evaluation results")

            # Create input data for aggregation
            input_data = {
                "evaluation_results": evaluation_results,
                "agent_id": "agent",  # Could be parameterized
                "multi_run": True,
            }

            # Execute the workflow for the aggregation step
            result_context = await self.execute(input_data)

            # Return the summarized results
            return result_context.summarize_results()
        else:
            return {"success": False, "error": "No evaluation results were generated"}


# Helper functions for accessing standard rubrics


def get_standard_rubric() -> Dict[str, Any]:
    """Get the standard evaluation rubric."""
    return create_standard_rubric().model_dump()


def get_qa_rubric() -> Dict[str, Any]:
    """Get the Q&A evaluation rubric."""
    return create_qa_rubric().model_dump()


def get_planning_rubric() -> Dict[str, Any]:
    """Get the planning evaluation rubric."""
    return create_planning_rubric().model_dump()


def get_analysis_rubric() -> Dict[str, Any]:
    """Get the analysis evaluation rubric."""
    return create_analysis_rubric().model_dump()


def get_creative_rubric() -> Dict[str, Any]:
    """Get the creative writing evaluation rubric."""
    return create_creative_rubric().model_dump()
