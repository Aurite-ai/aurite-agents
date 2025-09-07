"""
Base QA Tester for the Aurite Testing Framework.

This module provides the abstract base class for component-specific QA testers.
Each component type (LLM, MCP, Agent, Workflow) should implement its own tester
by extending this base class.
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional

from .qa_models import (
    CaseEvaluationResult,
    ComponentQAConfig,
    QAEvaluationResult,
    QATestCategory,
    QATestRequest,
)

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine


__all__ = ["BaseQATester"]


class BaseQATester(ABC):
    """
    Abstract base class for component-specific QA testers (Level 3).

    Each component type (LLM, MCP, Agent, Workflow) should have its own tester
    that extends this base class and implements the abstract methods.

    This class provides common functionality for:
    - Score aggregation (weighted average for QA)
    - Recommendation generation based on failure patterns
    - Test category management
    """

    def __init__(self, config: Optional[ComponentQAConfig] = None):
        """
        Initialize the QA tester.

        Args:
            config: Optional configuration for component-specific testing
        """
        self.config = config or ComponentQAConfig(
            component_type="unknown", test_categories=[], default_timeout=30.0, parallel_execution=True, max_retries=0
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def test_component(
        self, request: QATestRequest, executor: Optional["AuriteEngine"] = None
    ) -> QAEvaluationResult:
        """
        Execute QA tests for the specific component type.

        This method must be implemented by each component-specific tester
        to handle the unique testing requirements of that component.

        Args:
            request: The QA test request containing test cases and configuration
            executor: Optional AuriteEngine instance for executing components

        Returns:
            QAEvaluationResult containing the test results
        """
        pass

    @abstractmethod
    def get_test_categories(self) -> List[QATestCategory]:
        """
        Return the categories of tests this tester can perform.

        Each component tester should define its own test categories,
        such as:
        - For LLMs: ["accuracy", "coherence", "safety"]
        - For Agents: ["goal_achievement", "tool_usage", "conversation_flow"]
        - For MCPs: ["api_compliance", "performance", "error_handling"]
        - For Workflows: ["end_to_end", "step_validation", "data_flow"]

        Returns:
            List of test categories supported by this tester
        """
        pass

    def aggregate_scores(self, results: List[CaseEvaluationResult]) -> float:
        """
        Calculate aggregate score using weighted average (QA approach).

        This method uses a weighted average approach suitable for QA testing,
        where the overall score represents the percentage of passed tests.
        Can be overridden by specific testers if different scoring is needed.

        Args:
            results: List of individual test case results

        Returns:
            Overall score as a percentage (0-100)
        """
        if not results:
            return 0.0

        # For QA, we use a simple pass/fail ratio
        passed = sum(1 for r in results if r.grade == "PASS")
        total = len(results)

        # If we have test categories with weights, apply them
        if self.config and self.config.test_categories:
            # Group results by category if available
            # This would require category information in the results
            # For now, use simple average
            pass

        return (passed / total) * 100.0

    def generate_recommendations(self, results: List[CaseEvaluationResult]) -> List[str]:
        """
        Generate recommendations based on test results.

        Analyzes failure patterns and generates actionable recommendations
        for improving the component. Can be overridden by specific testers
        for more targeted recommendations.

        Args:
            results: List of test case results to analyze

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if not results:
            return recommendations

        # Analyze failure patterns
        failed_cases = [r for r in results if r.grade == "FAIL"]

        if not failed_cases:
            recommendations.append("All test cases passed. Consider adding more challenging test cases.")
            return recommendations

        # Calculate failure rate
        failure_rate = len(failed_cases) / len(results)

        if failure_rate > 0.5:
            recommendations.append(
                f"High failure rate ({failure_rate:.1%}). Consider reviewing the component's core functionality."
            )

        # Group failures by broken expectations
        failure_patterns: Dict[str, int] = {}
        schema_failures = 0

        for case in failed_cases:
            # Track schema validation failures
            if not case.schema_valid:
                schema_failures += 1

            # Track expectation failures
            for expectation in case.expectations_broken:
                failure_patterns[expectation] = failure_patterns.get(expectation, 0) + 1

        # Generate recommendations based on patterns
        if schema_failures > 0:
            recommendations.append(
                f"Schema validation failed in {schema_failures} cases. "
                "Ensure the component outputs data in the expected format."
            )

        # Find the most common failure patterns
        if failure_patterns:
            sorted_patterns = sorted(failure_patterns.items(), key=lambda x: x[1], reverse=True)

            # Report top 3 most common issues
            for pattern, count in sorted_patterns[:3]:
                percentage = (count / len(results)) * 100
                if percentage > 20:  # Only report if it affects >20% of cases
                    recommendations.append(
                        f"Recurring issue: '{pattern}' (failed in {count}/{len(results)} cases). "
                        "This should be prioritized for fixing."
                    )

        # Check for consistent errors
        error_messages = [r.error for r in failed_cases if r.error]
        if error_messages:
            unique_errors = set(error_messages)
            if len(unique_errors) == 1:
                recommendations.append(
                    f"Consistent error across failures: {list(unique_errors)[0]}. This indicates a systematic issue."
                )
            else:
                recommendations.append(
                    f"Multiple error types encountered ({len(unique_errors)} unique errors). "
                    "Review error handling and edge cases."
                )

        # Performance considerations
        if any(r.execution_time and r.execution_time > 10 for r in results):
            slow_cases = sum(1 for r in results if r.execution_time and r.execution_time > 10)
            recommendations.append(f"{slow_cases} test cases took >10 seconds. Consider optimizing performance.")

        return recommendations

    def validate_request(self, request: QATestRequest) -> List[str]:
        """
        Validate the test request before execution.

        Checks that the request contains valid data and all required
        fields for the specific component type.

        Args:
            request: The test request to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not request.test_cases:
            errors.append("No test cases provided")

        if not request.component_type:
            errors.append("Component type not specified")

        # Validate component type matches this tester
        if self.config and request.component_type != self.config.component_type:
            errors.append(
                f"Component type mismatch: expected {self.config.component_type}, got {request.component_type}"
            )

        # Validate test cases have required fields
        for i, case in enumerate(request.test_cases):
            if not case.id:
                errors.append(f"Test case {i} missing ID")
            if not case.expectations and not request.expected_schema:
                errors.append(f"Test case {case.id}: No expectations or schema defined")

        return errors

    @abstractmethod
    async def setup(self) -> None:
        """
        Optional setup method called before running tests.

        Can be overridden by specific testers to perform initialization
        tasks like loading resources or establishing connections.
        """
        pass

    @abstractmethod
    async def teardown(self) -> None:
        """
        Optional teardown method called after running tests.

        Can be overridden by specific testers to perform cleanup
        tasks like closing connections or releasing resources.
        """
        pass
