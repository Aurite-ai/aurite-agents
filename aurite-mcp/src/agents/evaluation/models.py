"""
Data models for agent evaluation.

This module defines data models for agent evaluation, including rubrics,
evaluation criteria, and result structures.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union, Set
from pydantic import BaseModel, Field, model_validator


class ScoringScale(BaseModel):
    """Defines a scoring scale for evaluation criteria."""

    min: float = Field(..., description="Minimum score value")
    max: float = Field(..., description="Maximum score value")
    increment: float = Field(
        1.0, description="Score increment (e.g. 0.5 for half-point scoring)"
    )

    @model_validator(mode="after")
    def validate_scale(self):
        """Validate that the scale makes sense."""
        if self.min >= self.max:
            raise ValueError("Minimum score must be less than maximum score")
        if self.increment <= 0:
            raise ValueError("Increment must be positive")
        if (self.max - self.min) < self.increment:
            raise ValueError("Range must be at least as large as increment")
        return self


class CriterionScoring(BaseModel):
    """Defines scoring guidelines for a criterion."""

    # Maps score values to descriptions
    # Example: {"1": "Poor", "2": "Fair", "3": "Good", "4": "Very Good", "5": "Excellent"}
    scoring: Dict[str, str] = Field(
        ..., description="Mapping of score values to descriptions"
    )


class EvaluationCriterion(BaseModel):
    """Defines a single evaluation criterion."""

    description: str = Field(
        ..., description="Description of what this criterion evaluates"
    )
    weight: float = Field(
        1.0,
        description="Weight of this criterion in overall score (default = 1.0)",
        ge=0.0,
        le=1.0,
    )
    scoring: Dict[str, str] = Field(
        ..., description="Scoring guidelines for this criterion"
    )

    # Optional fields
    examples: Optional[Dict[str, str]] = Field(
        None, description="Optional examples for different score levels"
    )
    instructions: Optional[str] = Field(
        None, description="Specific instructions for evaluating this criterion"
    )


class EvaluationRubric(BaseModel):
    """Complete evaluation rubric with criteria and scoring scale."""

    criteria: Dict[str, EvaluationCriterion] = Field(
        ..., description="Map of criterion names to criterion definitions"
    )
    scale: ScoringScale = Field(..., description="Scoring scale for the rubric")
    passing_threshold: Optional[float] = Field(
        None, description="Score threshold for passing (if applicable)"
    )

    # Optional fields
    name: Optional[str] = Field(None, description="Name of the rubric")
    description: Optional[str] = Field(None, description="Description of the rubric")
    instructions: Optional[str] = Field(
        None, description="General instructions for applying the rubric"
    )
    tags: Optional[List[str]] = Field(
        None, description="Tags for categorizing the rubric"
    )

    @model_validator(mode="after")
    def validate_weights(self):
        """Validate that weights sum to approximately 1.0."""
        total_weight = sum(criterion.weight for criterion in self.criteria.values())
        if not 0.99 <= total_weight <= 1.01:  # Allow for small floating point errors
            raise ValueError(f"Criterion weights must sum to 1.0, got {total_weight}")
        return self


class CriterionScore(BaseModel):
    """Score for a single criterion."""

    name: str = Field(..., description="Name of the criterion")
    score: float = Field(..., description="Numeric score")
    justification: str = Field(..., description="Justification for the score")

    # Optional breakdown for complex criteria
    sub_scores: Optional[Dict[str, float]] = Field(
        None, description="Optional sub-scores for complex criteria"
    )


class EvaluationResult(BaseModel):
    """Result of an agent evaluation."""

    # Core fields
    overall_score: float = Field(..., description="Overall weighted score")
    passed: Optional[bool] = Field(None, description="Whether the evaluation passed")
    criterion_scores: Dict[str, CriterionScore] = Field(
        ..., description="Scores for individual criteria"
    )

    # Metadata
    agent_id: Optional[str] = Field(None, description="ID of the evaluated agent")
    evaluator_id: Optional[str] = Field(None, description="ID of the evaluator")
    rubric_id: Optional[str] = Field(None, description="ID of the used rubric")
    timestamp: Optional[str] = Field(None, description="Timestamp of the evaluation")

    # Detailed feedback
    summary_feedback: str = Field(..., description="Summary feedback")
    strengths: List[str] = Field(
        default_factory=list, description="Identified strengths"
    )
    areas_for_improvement: List[str] = Field(
        default_factory=list, description="Areas for improvement"
    )

    # Input data
    agent_output: Optional[str] = Field(
        None, description="Agent output that was evaluated"
    )
    expected_output: Optional[str] = Field(
        None, description="Expected output (if applicable)"
    )

    # Additional metadata
    tags: Set[str] = Field(default_factory=set, description="Tags for this evaluation")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    # For multi-run evaluations
    run_id: Optional[int] = Field(None, description="Run ID for multi-run evaluations")


class AggregatedEvaluationResult(BaseModel):
    """Aggregated results from multiple evaluation runs."""

    # Core aggregated metrics
    mean_score: float = Field(..., description="Mean overall score")
    median_score: float = Field(..., description="Median overall score")
    min_score: float = Field(..., description="Minimum overall score")
    max_score: float = Field(..., description="Maximum overall score")
    std_deviation: float = Field(..., description="Standard deviation of scores")
    pass_rate: float = Field(..., description="Proportion of passing evaluations")

    # Criterion-level aggregation
    criterion_mean_scores: Dict[str, float] = Field(
        ..., description="Mean scores by criterion"
    )
    criterion_std_deviations: Dict[str, float] = Field(
        ..., description="Standard deviations by criterion"
    )

    # Individual results
    results: List[EvaluationResult] = Field(
        ..., description="Individual evaluation results"
    )

    # Metadata
    num_runs: int = Field(..., description="Number of evaluation runs")
    agent_id: Optional[str] = Field(None, description="ID of the evaluated agent")
    rubric_id: Optional[str] = Field(None, description="ID of the used rubric")
    timestamp: Optional[str] = Field(None, description="Timestamp of the aggregation")

    # Aggregated feedback
    common_strengths: List[str] = Field(
        default_factory=list, description="Common strengths across evaluations"
    )
    common_areas_for_improvement: List[str] = Field(
        default_factory=list,
        description="Common areas for improvement across evaluations",
    )
    summary: str = Field(..., description="Summary of aggregated results")

    # Additional metadata
    tags: Set[str] = Field(default_factory=set, description="Tags for this evaluation")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


# Standard Rubric Templates


def create_standard_rubric(
    name: str = "standard", description: str = None
) -> EvaluationRubric:
    """Create a standard five-point rubric with balanced criteria."""
    return EvaluationRubric(
        name=name,
        description=description or "Standard five-point evaluation rubric",
        criteria={
            "accuracy": EvaluationCriterion(
                description="Correctness of information in the response",
                weight=0.3,
                scoring={
                    "1": "Contains significant factual errors",
                    "2": "Contains minor factual errors",
                    "3": "Mostly accurate with some imprecisions",
                    "4": "Highly accurate with minimal issues",
                    "5": "Perfectly accurate information",
                },
            ),
            "relevance": EvaluationCriterion(
                description="How well the response addresses the query",
                weight=0.3,
                scoring={
                    "1": "Does not address the query at all",
                    "2": "Partially addresses the query with major gaps",
                    "3": "Addresses the main points of the query",
                    "4": "Thoroughly addresses the query",
                    "5": "Comprehensively addresses all aspects of the query",
                },
            ),
            "coherence": EvaluationCriterion(
                description="Logical structure and flow of the response",
                weight=0.2,
                scoring={
                    "1": "Incoherent and disorganized",
                    "2": "Poorly structured with logical gaps",
                    "3": "Adequately structured with minor issues",
                    "4": "Well structured and easy to follow",
                    "5": "Exceptionally well structured and engaging",
                },
            ),
            "completeness": EvaluationCriterion(
                description="Thoroughness of the response",
                weight=0.2,
                scoring={
                    "1": "Critically incomplete",
                    "2": "Missing important elements",
                    "3": "Covers basic requirements",
                    "4": "Comprehensive coverage",
                    "5": "Exceptionally thorough coverage",
                },
            ),
        },
        scale=ScoringScale(min=1, max=5, increment=1),
        passing_threshold=3.0,
    )


def create_qa_rubric() -> EvaluationRubric:
    """Create a rubric specifically for evaluating Q&A agents."""
    return EvaluationRubric(
        name="qa_rubric",
        description="Rubric for evaluating question-answering performance",
        criteria={
            "accuracy": EvaluationCriterion(
                description="Factual correctness of the answer",
                weight=0.4,
                scoring={
                    "1": "Contains significant factual errors",
                    "2": "Contains minor factual errors",
                    "3": "Mostly accurate with some imprecisions",
                    "4": "Highly accurate with minimal issues",
                    "5": "Perfectly accurate information",
                },
            ),
            "comprehensiveness": EvaluationCriterion(
                description="How thoroughly the question is answered",
                weight=0.3,
                scoring={
                    "1": "Misses most key points",
                    "2": "Addresses only some key points",
                    "3": "Addresses most key points",
                    "4": "Thoroughly addresses key points with some details",
                    "5": "Comprehensively addresses all aspects with appropriate detail",
                },
            ),
            "clarity": EvaluationCriterion(
                description="Clarity and understandability of the answer",
                weight=0.2,
                scoring={
                    "1": "Confusing and difficult to understand",
                    "2": "Somewhat unclear, requires significant effort to understand",
                    "3": "Adequately clear with some room for improvement",
                    "4": "Very clear and easy to understand",
                    "5": "Exceptionally clear, concise, and accessible",
                },
            ),
            "directness": EvaluationCriterion(
                description="How directly the answer addresses the question",
                weight=0.1,
                scoring={
                    "1": "Does not directly address the question",
                    "2": "Indirectly addresses the question",
                    "3": "Mostly addresses the question directly",
                    "4": "Directly addresses the question with minor tangents",
                    "5": "Perfectly addresses the question with no irrelevant information",
                },
            ),
        },
        scale=ScoringScale(min=1, max=5, increment=1),
        passing_threshold=3.0,
    )


def create_planning_rubric() -> EvaluationRubric:
    """Create a rubric specifically for evaluating planning agents."""
    return EvaluationRubric(
        name="planning_rubric",
        description="Rubric for evaluating plan quality and feasibility",
        criteria={
            "completeness": EvaluationCriterion(
                description="How thoroughly the plan covers all necessary elements",
                weight=0.25,
                scoring={
                    "1": "Missing critical elements",
                    "2": "Missing several important elements",
                    "3": "Covers most essential elements",
                    "4": "Comprehensive coverage of necessary elements",
                    "5": "Exceptional coverage including contingencies",
                },
            ),
            "feasibility": EvaluationCriterion(
                description="How realistic and feasible the plan is",
                weight=0.25,
                scoring={
                    "1": "Completely unfeasible",
                    "2": "Questionable feasibility with major issues",
                    "3": "Generally feasible with some concerns",
                    "4": "Highly feasible with minor issues",
                    "5": "Perfectly feasible and well-considered",
                },
            ),
            "structure": EvaluationCriterion(
                description="Organization, sequencing, and dependencies",
                weight=0.2,
                scoring={
                    "1": "Poorly structured with illogical sequencing",
                    "2": "Basic structure with sequencing issues",
                    "3": "Adequate structure with reasonable sequencing",
                    "4": "Well-structured with clear dependencies",
                    "5": "Exceptionally well-structured with optimized sequencing",
                },
            ),
            "specificity": EvaluationCriterion(
                description="Level of detail and actionability",
                weight=0.15,
                scoring={
                    "1": "Extremely vague and unactionable",
                    "2": "General with few specific details",
                    "3": "Moderately specific and mostly actionable",
                    "4": "Highly specific and actionable",
                    "5": "Precisely detailed and immediately actionable",
                },
            ),
            "adaptability": EvaluationCriterion(
                description="Flexibility and consideration of alternatives",
                weight=0.15,
                scoring={
                    "1": "No consideration of alternatives or contingencies",
                    "2": "Limited consideration of alternatives",
                    "3": "Some consideration of key alternatives",
                    "4": "Good consideration of alternatives and contingencies",
                    "5": "Comprehensive alternatives and contingency planning",
                },
            ),
        },
        scale=ScoringScale(min=1, max=5, increment=1),
        passing_threshold=3.0,
    )


def create_analysis_rubric() -> EvaluationRubric:
    """Create a rubric specifically for evaluating analysis agents."""
    return EvaluationRubric(
        name="analysis_rubric",
        description="Rubric for evaluating data analysis quality",
        criteria={
            "accuracy": EvaluationCriterion(
                description="Correctness of analysis results and calculations",
                weight=0.3,
                scoring={
                    "1": "Significant calculation errors or misinterpretations",
                    "2": "Some calculation errors or misinterpretations",
                    "3": "Generally accurate with minor issues",
                    "4": "Highly accurate analysis",
                    "5": "Perfectly accurate analysis with verification",
                },
            ),
            "depth": EvaluationCriterion(
                description="Depth and sophistication of analysis",
                weight=0.25,
                scoring={
                    "1": "Superficial analysis only",
                    "2": "Basic analysis with limited insight",
                    "3": "Moderate depth with some insights",
                    "4": "Deep analysis with valuable insights",
                    "5": "Exceptionally deep analysis with novel insights",
                },
            ),
            "methodology": EvaluationCriterion(
                description="Appropriateness and quality of analytical approach",
                weight=0.25,
                scoring={
                    "1": "Inappropriate methodology",
                    "2": "Flawed but somewhat relevant methodology",
                    "3": "Adequate methodology",
                    "4": "Strong methodology with justification",
                    "5": "Optimal methodology with robust justification",
                },
            ),
            "communication": EvaluationCriterion(
                description="Clarity in presenting analysis and findings",
                weight=0.2,
                scoring={
                    "1": "Confusing presentation of findings",
                    "2": "Unclear presentation with organization issues",
                    "3": "Clear presentation with adequate organization",
                    "4": "Very clear presentation with good organization",
                    "5": "Exceptionally clear and effectively organized",
                },
            ),
        },
        scale=ScoringScale(min=1, max=5, increment=1),
        passing_threshold=3.0,
    )


def create_creative_rubric() -> EvaluationRubric:
    """Create a rubric specifically for evaluating creative writing agents."""
    return EvaluationRubric(
        name="creative_rubric",
        description="Rubric for evaluating creative writing quality",
        criteria={
            "originality": EvaluationCriterion(
                description="Uniqueness and creativity of ideas",
                weight=0.3,
                scoring={
                    "1": "Highly derivative and unoriginal",
                    "2": "Mostly conventional with few original elements",
                    "3": "Balance of conventional and original elements",
                    "4": "Predominantly original and creative",
                    "5": "Exceptionally original and innovative",
                },
            ),
            "coherence": EvaluationCriterion(
                description="Internal logic and consistency",
                weight=0.25,
                scoring={
                    "1": "Incoherent with major contradictions",
                    "2": "Partially coherent with notable inconsistencies",
                    "3": "Mostly coherent with minor inconsistencies",
                    "4": "Highly coherent and consistent",
                    "5": "Perfectly coherent with elegant integration",
                },
            ),
            "engagement": EvaluationCriterion(
                description="Ability to engage and hold interest",
                weight=0.25,
                scoring={
                    "1": "Unengaging and difficult to continue",
                    "2": "Minimally engaging with significant lulls",
                    "3": "Moderately engaging with occasional lulls",
                    "4": "Highly engaging throughout",
                    "5": "Exceptionally engaging and captivating",
                },
            ),
            "technical_quality": EvaluationCriterion(
                description="Technical writing quality (language, structure, etc.)",
                weight=0.2,
                scoring={
                    "1": "Poor technical quality with numerous issues",
                    "2": "Below average quality with notable issues",
                    "3": "Average quality with few distracting issues",
                    "4": "High quality with minimal issues",
                    "5": "Exceptional quality with masterful execution",
                },
            ),
        },
        scale=ScoringScale(min=1, max=5, increment=1),
        passing_threshold=3.0,
    )
