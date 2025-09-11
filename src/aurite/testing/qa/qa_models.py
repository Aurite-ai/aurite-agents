"""
QA Testing Models for the Aurite Testing Framework.

This module defines the data models used for Quality Assurance testing,
including requests, results, and validation structures.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SchemaValidationResult(BaseModel):
    """Result of schema validation."""

    is_valid: bool = Field(description="Whether the output is valid according to schema")
    error_message: Optional[str] = Field(default=None, description="Main error message if validation failed")
    validation_errors: List[str] = Field(default_factory=list, description="List of specific validation errors")


class ExpectationAnalysisResult(BaseModel):
    """Result of expectation analysis by LLM."""

    analysis: str = Field(description="LLM's analysis of how well the output meets expectations")
    expectations_broken: List[str] = Field(default_factory=list, description="List of expectations that were not met")
    confidence_score: Optional[float] = Field(default=None, description="Confidence score of the analysis (0-1)")


class CaseEvaluationResult(BaseModel):
    """Result for a single test case evaluation."""

    case_id: str = Field(description="Unique identifier for the test case")
    input: Any = Field(description="Input provided to the component")
    output: Any = Field(description="Output produced by the component")
    grade: Literal["PASS", "FAIL"] = Field(description="Overall grade for this test case")
    analysis: str = Field(description="Detailed analysis of the test case result")
    expectations_broken: List[str] = Field(default_factory=list, description="List of expectations that were not met")
    schema_valid: bool = Field(default=True, description="Whether the output passed schema validation")
    schema_errors: List[str] = Field(default_factory=list, description="Schema validation errors if any")
    execution_time: Optional[float] = Field(default=None, description="Time taken to execute this test case in seconds")
    error: Optional[str] = Field(default=None, description="Error message if test case execution failed")


class QAEvaluationResult(BaseModel):
    """Overall QA evaluation result."""

    evaluation_id: str = Field(description="Unique identifier for this evaluation run")
    status: Literal["success", "failed", "partial"] = Field(description="Overall status of the evaluation")
    component_type: Optional[str] = Field(default=None, description="Type of component that was tested")
    component_name: Optional[str] = Field(default=None, description="Name of the component that was tested")
    overall_score: float = Field(description="Overall QA score as a percentage (0-100)")
    total_cases: int = Field(description="Total number of test cases executed")
    passed_cases: int = Field(description="Number of test cases that passed")
    failed_cases: int = Field(description="Number of test cases that failed")
    case_results: Dict[str, CaseEvaluationResult] = Field(
        description="Detailed results for each test case, keyed by case ID"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for improving the component based on test results"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the evaluation")
    started_at: datetime = Field(description="Timestamp when the evaluation started")
    completed_at: Optional[datetime] = Field(default=None, description="Timestamp when the evaluation completed")
    duration_seconds: Optional[float] = Field(default=None, description="Total duration of the evaluation in seconds")


class ComponentQAConfig(BaseModel):
    """Configuration for component-specific QA testing."""

    component_type: str = Field(description="Type of component this config applies to")
    default_timeout: float = Field(default=30.0, description="Default timeout for test execution in seconds")
    parallel_execution: bool = Field(default=True, description="Whether test cases can be executed in parallel")
    max_retries: int = Field(default=0, description="Maximum number of retries for failed test cases")
