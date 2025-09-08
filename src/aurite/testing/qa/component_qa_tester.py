"""
Unified Component QA Tester for the Aurite Testing Framework.

This module provides a single, unified QA tester that handles all component types
(agents, workflows, etc.) using component-aware context and recommendations.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from .qa_models import (
    CaseEvaluationResult,
    ComponentQAConfig,
    QAEvaluationResult,
    QATestCategory,
    QATestRequest,
)
from .qa_utils import (
    analyze_expectations,
    execute_component,
    get_llm_client,
    validate_schema,
)

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)


class ComponentQATester:
    """
    Unified QA tester for all component types (Level 3).

    This tester handles quality assurance testing for any component type by:
    - Using component-aware context for expectation analysis
    - Generating component-specific recommendations
    - Supporting custom execution patterns
    - Leveraging shared utilities for common operations
    """

    def __init__(self, config: Optional[ComponentQAConfig] = None):
        """
        Initialize the Component QA tester.

        Args:
            config: Optional configuration for component-specific testing
        """
        self.config = config or ComponentQAConfig(
            component_type="unified",  # This tester handles all types
            test_categories=self._get_default_test_categories(),
            default_timeout=90.0,  # Reasonable default for most components
            parallel_execution=True,  # Most components can run in parallel
            max_retries=1,
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_default_test_categories(self) -> List[QATestCategory]:
        """Get default test categories for component testing."""
        return [
            QATestCategory(
                name="functionality",
                description="Core functionality and goal achievement",
                weight=0.4,
                required=True,
            ),
            QATestCategory(
                name="output_quality",
                description="Quality, coherence, and completeness of outputs",
                weight=0.3,
                required=True,
            ),
            QATestCategory(
                name="integration",
                description="Integration with other components and data flow",
                weight=0.2,
                required=False,
            ),
            QATestCategory(
                name="reliability",
                description="Error handling and consistent behavior",
                weight=0.1,
                required=False,
            ),
        ]

    async def test_component(
        self, request: QATestRequest, executor: Optional["AuriteEngine"] = None
    ) -> QAEvaluationResult:
        """
        Execute QA tests for any component type.

        Args:
            request: The QA test request containing test cases and configuration
            executor: Optional AuriteEngine instance for executing the component

        Returns:
            QAEvaluationResult containing the test results
        """
        evaluation_id = f"{request.component_type}_qa_{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow()

        self.logger.info(
            f"Starting {request.component_type} QA testing {evaluation_id} for component: {request.component_config.get('name', 'unknown')}"
        )

        # Validate the request
        validation_errors = self.validate_request(request)
        if validation_errors:
            raise ValueError(f"Invalid request: {'; '.join(validation_errors)}")

        # Set up testing
        await self.setup()

        try:
            # Get LLM client for evaluation
            llm_client = await self._get_llm_client(request, executor)

            # Determine execution strategy based on component type
            parallel_execution = self._should_use_parallel_execution(request.component_type)

            # Execute test cases
            if parallel_execution:
                tasks = [
                    self._evaluate_single_case(case=case, llm_client=llm_client, request=request, executor=executor)
                    for case in request.test_cases
                ]
                case_results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Sequential execution for components that require it
                case_results = []
                for case in request.test_cases:
                    try:
                        result = await self._evaluate_single_case(
                            case=case, llm_client=llm_client, request=request, executor=executor
                        )
                        case_results.append(result)
                    except Exception as e:
                        case_results.append(e)

            # Process results and handle any exceptions
            processed_results: Dict[str, CaseEvaluationResult] = {}
            failed_count = 0

            for case, result in zip(request.test_cases, case_results, strict=False):
                case_id_str = str(case.id)
                if isinstance(result, Exception):
                    # Create a failed result for exceptions
                    processed_results[case_id_str] = CaseEvaluationResult(
                        case_id=case_id_str,
                        input=case.input,
                        output=None,
                        grade="FAIL",
                        analysis=f"{request.component_type.title()} test execution failed: {str(result)}",
                        expectations_broken=case.expectations,
                        error=str(result),
                    )
                    failed_count += 1
                elif isinstance(result, CaseEvaluationResult):
                    processed_results[case_id_str] = result
                    if result.grade == "FAIL":
                        failed_count += 1

            # Calculate overall score
            overall_score = self.aggregate_scores(list(processed_results.values()))

            # Generate component-specific recommendations
            recommendations = self._generate_component_recommendations(list(processed_results.values()), request)

            # Determine overall status
            passed_count = len(processed_results) - failed_count
            if failed_count == 0:
                status = "success"
            elif failed_count == len(processed_results):
                status = "failed"
            else:
                status = "partial"

            completed_at = datetime.utcnow()

            return QAEvaluationResult(
                evaluation_id=evaluation_id,
                status=status,
                component_type=request.component_type,
                component_name=request.component_config.get("name", "unknown"),
                overall_score=overall_score,
                total_cases=len(processed_results),
                passed_cases=passed_count,
                failed_cases=failed_count,
                case_results=processed_results,
                recommendations=recommendations,
                metadata={
                    "component_config": request.component_config,
                    "test_categories": [cat.name for cat in self.get_test_categories()],
                    "component_type": request.component_type,
                    "framework": request.framework,
                },
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
            )

        finally:
            await self.teardown()

    async def _evaluate_single_case(
        self,
        case,
        llm_client,
        request: QATestRequest,
        executor: Optional["AuriteEngine"] = None,
    ) -> CaseEvaluationResult:
        """
        Evaluate a single test case for any component type.

        Args:
            case: The test case to evaluate
            llm_client: LLM client for expectation analysis
            request: The overall test request
            executor: Optional AuriteEngine for component execution

        Returns:
            CaseEvaluationResult for this test case
        """
        start_time = datetime.utcnow()

        try:
            # Get the output using the utility function (supports custom execution)
            output = await execute_component(case, request, executor)

            # Validate schema if provided using utility function
            schema_result = None
            if request.expected_schema:
                schema_result = validate_schema(output, request.expected_schema)
                if not schema_result.is_valid:
                    # Schema validation failed
                    return CaseEvaluationResult(
                        case_id=str(case.id),
                        input=case.input,
                        output=output,
                        grade="FAIL",
                        analysis=f"Schema Validation Failed: {schema_result.error_message}",
                        expectations_broken=[],
                        schema_valid=False,
                        schema_errors=schema_result.validation_errors,
                        execution_time=(datetime.utcnow() - start_time).total_seconds(),
                    )

            # Analyze expectations using utility function with component context
            if case.expectations:
                component_context = self._build_component_context(request)
                expectation_result = await analyze_expectations(case, output, llm_client, component_context)

                grade = "PASS" if not expectation_result.expectations_broken else "FAIL"

                return CaseEvaluationResult(
                    case_id=str(case.id),
                    input=case.input,
                    output=output,
                    grade=grade,
                    analysis=expectation_result.analysis,
                    expectations_broken=expectation_result.expectations_broken,
                    schema_valid=schema_result.is_valid if schema_result else True,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                )
            else:
                # No expectations to check, just schema validation
                return CaseEvaluationResult(
                    case_id=str(case.id),
                    input=case.input,
                    output=output,
                    grade="PASS" if (not schema_result or schema_result.is_valid) else "FAIL",
                    analysis=f"No expectations defined, {request.component_type} output generated successfully",
                    expectations_broken=[],
                    schema_valid=schema_result.is_valid if schema_result else True,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                )

        except Exception as e:
            self.logger.error(f"Error evaluating {request.component_type} case {case.id}: {e}")
            return CaseEvaluationResult(
                case_id=str(case.id),
                input=case.input,
                output=None,
                grade="FAIL",
                analysis=f"{request.component_type.title()} evaluation failed: {str(e)}",
                expectations_broken=case.expectations,
                error=str(e),
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )

    def _build_component_context(self, request: QATestRequest) -> Dict:
        """
        Build component-specific context for expectation analysis.

        Args:
            request: The test request containing component configuration

        Returns:
            Dictionary with component context for the LLM
        """
        component_config = request.component_config
        component_type = request.component_type

        base_context = {
            "type": component_type,
            "name": component_config.get("name", "Unknown"),
        }

        # Add component-specific context
        if component_type == "agent":
            base_context.update(
                {
                    "system_prompt": component_config.get("system_prompt", ""),
                    "tools": component_config.get("tools", []),
                    "temperature": component_config.get("temperature", 0.7),
                    "max_tokens": component_config.get("max_tokens"),
                    "conversation_memory": component_config.get("conversation_memory", True),
                }
            )

        elif component_type in ["workflow", "linear_workflow", "custom_workflow"]:
            steps = component_config.get("steps", [])
            base_context.update(
                {
                    "steps": steps,
                    "timeout_seconds": component_config.get("timeout_seconds", 60),
                    "parallel_execution": component_config.get("parallel_execution", False),
                    "error_handling": component_config.get("error_handling", {}),
                }
            )

            # Add workflow type specific context
            if component_type == "custom_workflow":
                base_context.update(
                    {
                        "module_path": component_config.get("module_path"),
                        "class_name": component_config.get("class_name"),
                    }
                )

        elif component_type == "llm":
            base_context.update(
                {
                    "model": component_config.get("model", "Unknown"),
                    "provider": component_config.get("provider", "Unknown"),
                    "temperature": component_config.get("temperature", 0.7),
                    "max_tokens": component_config.get("max_tokens"),
                }
            )

        elif component_type == "mcp_server":
            base_context.update(
                {
                    "command": component_config.get("command", []),
                    "tools": component_config.get("tools", []),
                    "resources": component_config.get("resources", []),
                }
            )

        return base_context

    def _should_use_parallel_execution(self, component_type: str) -> bool:
        """
        Determine if parallel execution should be used for a component type.

        Args:
            component_type: The type of component being tested

        Returns:
            True if parallel execution is appropriate, False otherwise
        """
        # Workflows are typically sequential by nature
        if component_type in ["workflow", "linear_workflow", "custom_workflow"]:
            return False

        # Most other components can be tested in parallel
        return True

    async def _get_llm_client(self, request: QATestRequest, executor: Optional["AuriteEngine"] = None):
        """
        Get or create an LLM client for evaluation using utility function.

        Args:
            request: The test request
            executor: Optional AuriteEngine with config manager

        Returns:
            LiteLLMClient for evaluation
        """
        config_manager = executor._config_manager if executor else None
        return await get_llm_client(request.review_llm, config_manager)

    def _generate_component_recommendations(
        self, results: List[CaseEvaluationResult], request: QATestRequest
    ) -> List[str]:
        """
        Generate component-specific recommendations based on test results.

        Args:
            results: List of case evaluation results
            request: Original test request

        Returns:
            List of component-specific recommendation strings
        """
        recommendations = []
        component_config = request.component_config
        component_type = request.component_type

        if not results:
            return recommendations

        failed_cases = [r for r in results if r.grade == "FAIL"]

        # Generate component-specific recommendations
        if component_type == "agent":
            recommendations.extend(self._generate_agent_recommendations(failed_cases, component_config, results))
        elif component_type in ["workflow", "linear_workflow", "custom_workflow"]:
            recommendations.extend(self._generate_workflow_recommendations(failed_cases, component_config, results))
        elif component_type == "llm":
            recommendations.extend(self._generate_llm_recommendations(failed_cases, component_config, results))
        elif component_type == "mcp_server":
            recommendations.extend(self._generate_mcp_server_recommendations(failed_cases, component_config, results))

        # Add general recommendations
        if not failed_cases:
            recommendations.append("All test cases passed successfully.")
        else:
            failure_rate = len(failed_cases) / len(results)
            if failure_rate > 0.5:
                recommendations.append(
                    f"High failure rate ({failure_rate:.1%}). Consider reviewing the {component_type}'s core functionality."
                )

        return recommendations

    def _generate_agent_recommendations(
        self, failed_cases: List[CaseEvaluationResult], config: Dict, all_results: List[CaseEvaluationResult]
    ) -> List[str]:
        """Generate agent-specific recommendations."""
        recommendations = []

        # Analyze system prompt issues
        system_prompt = config.get("system_prompt", "")
        if system_prompt and len(system_prompt) < 50:
            recommendations.append(
                "System prompt is very short. Consider providing more detailed instructions and behavioral guidelines."
            )

        # Analyze tool usage patterns
        tools = config.get("tools", [])
        if not tools and any("tool" in r.analysis.lower() for r in failed_cases):
            recommendations.append(
                "Agent lacks tools but test cases suggest tool usage is needed. Consider adding relevant tools."
            )

        # Analyze temperature settings
        temperature = config.get("temperature", 0.7)
        if temperature > 0.9 and len(failed_cases) > len(all_results) / 2:
            recommendations.append(
                f"High temperature setting ({temperature}) may be causing inconsistent responses. Consider lowering to 0.3-0.7."
            )

        # Analyze response length issues
        max_tokens = config.get("max_tokens")
        if max_tokens and max_tokens < 500:
            short_responses = [
                r for r in failed_cases if "too short" in r.analysis.lower() or "incomplete" in r.analysis.lower()
            ]
            if short_responses:
                recommendations.append(
                    f"Max tokens setting ({max_tokens}) may be too low, causing truncated responses. Consider increasing."
                )

        return recommendations

    def _generate_workflow_recommendations(
        self, failed_cases: List[CaseEvaluationResult], config: Dict, all_results: List[CaseEvaluationResult]
    ) -> List[str]:
        """Generate workflow-specific recommendations."""
        recommendations = []

        # Analyze workflow structure
        steps = config.get("steps", [])
        if not steps:
            recommendations.append("Workflow has no defined steps. Add workflow steps to enable execution.")
            return recommendations

        if len(steps) < 2:
            recommendations.append("Workflow has only one step. Consider if this should be a simple agent instead.")

        # Analyze timeout settings
        timeout = config.get("timeout_seconds", 60)
        if timeout < 30 and len(steps) > 2:
            recommendations.append(
                f"Timeout ({timeout}s) may be too short for a {len(steps)}-step workflow. "
                "Consider increasing to allow adequate time for all steps."
            )

        # Analyze coordination failures
        coordination_failures = [
            r
            for r in failed_cases
            if any(keyword in r.analysis.lower() for keyword in ["coordination", "data flow", "step", "mapping"])
        ]
        if coordination_failures:
            recommendations.append(
                f"{len(coordination_failures)} failures appear related to agent coordination or data flow. "
                "Review step input/output mappings and agent compatibility."
            )

        return recommendations

    def _generate_llm_recommendations(
        self, failed_cases: List[CaseEvaluationResult], config: Dict, all_results: List[CaseEvaluationResult]
    ) -> List[str]:
        """Generate LLM-specific recommendations."""
        recommendations = []

        model = config.get("model", "")
        provider = config.get("provider", "")

        if not model:
            recommendations.append("No model specified in LLM configuration.")

        if not provider:
            recommendations.append("No provider specified in LLM configuration.")

        # Analyze temperature for consistency issues
        temperature = config.get("temperature", 0.7)
        if temperature > 0.8 and len(failed_cases) > len(all_results) / 3:
            recommendations.append(
                f"High temperature ({temperature}) may be causing inconsistent outputs. Consider lowering for more deterministic results."
            )

        return recommendations

    def _generate_mcp_server_recommendations(
        self, failed_cases: List[CaseEvaluationResult], config: Dict, all_results: List[CaseEvaluationResult]
    ) -> List[str]:
        """Generate MCP server-specific recommendations."""
        recommendations = []

        command = config.get("command", [])
        if not command:
            recommendations.append("No command specified for MCP server.")

        tools = config.get("tools", [])
        resources = config.get("resources", [])

        if not tools and not resources:
            recommendations.append("MCP server has no tools or resources defined. Consider adding functionality.")

        return recommendations

    def aggregate_scores(self, results: List[CaseEvaluationResult]) -> float:
        """
        Calculate aggregate score using weighted average (QA approach).

        This method uses a weighted average approach suitable for QA testing,
        where the overall score represents the percentage of passed tests.

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

        return (passed / total) * 100.0

    def get_test_categories(self) -> List[QATestCategory]:
        """
        Return the categories of tests this tester can perform.

        Returns:
            List of test categories supported by this tester
        """
        return self.config.test_categories if self.config else self._get_default_test_categories()

    async def setup(self) -> None:
        """
        Setup method called before running tests.

        Performs any necessary initialization for component testing.
        """
        self.logger.debug("Setting up component QA tester")
        # Add any component-specific setup here
        pass

    async def teardown(self) -> None:
        """
        Teardown method called after running tests.

        Performs cleanup after component testing.
        """
        self.logger.debug("Tearing down component QA tester")
        # Add any component-specific cleanup here
        pass

    def validate_request(self, request: QATestRequest) -> List[str]:
        """
        Validate the test request for component-specific requirements.

        Args:
            request: The test request to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Basic validations
        if not request.test_cases:
            errors.append("No test cases provided")

        if not request.component_type:
            errors.append("Component type not specified")

        # Validate test cases have required fields
        for i, case in enumerate(request.test_cases):
            if not case.id:
                errors.append(f"Test case {i} missing ID")
            if not case.expectations and not request.expected_schema:
                errors.append(f"Test case {case.id}: No expectations or schema defined")

        # Check if this is a manual output evaluation (all test cases have outputs)
        has_manual_outputs = all(case.output is not None for case in request.test_cases)

        # Check if this is a function-based evaluation (run_agent is provided)
        has_run_function = getattr(request, "run_agent", None) is not None

        # Skip component-specific validations for manual output or function-based evaluations
        if has_manual_outputs:
            self.logger.info("Skipping component-specific validations for manual output evaluation")
            return errors
        elif has_run_function:
            self.logger.info("Skipping component-specific validations for function-based evaluation")
            return errors

        # Component-specific validations (only for live component evaluations)
        component_config = request.component_config
        component_type = request.component_type

        if not component_config.get("name"):
            errors.append(f"{component_type.title()} configuration missing required 'name' field")

        # Type-specific validations
        if component_type == "agent":
            if not component_config.get("llm") and not component_config.get("llm_config_id"):
                errors.append("Agent configuration missing LLM specification ('llm' or 'llm_config_id')")

        elif component_type in ["workflow", "linear_workflow", "custom_workflow"]:
            workflow_type = component_config.get("type", "linear_workflow")

            if component_type == "linear_workflow" or workflow_type == "linear_workflow":
                steps = component_config.get("steps", [])
                if not steps:
                    errors.append("Linear workflow missing required 'steps' field")

            elif component_type == "custom_workflow" or workflow_type == "custom_workflow":
                if not component_config.get("module_path"):
                    errors.append("Custom workflow missing required 'module_path' field")
                if not component_config.get("class_name"):
                    errors.append("Custom workflow missing required 'class_name' field")

        elif component_type == "llm":
            if not component_config.get("model"):
                errors.append("LLM configuration missing required 'model' field")
            if not component_config.get("provider"):
                errors.append("LLM configuration missing required 'provider' field")

        return errors
