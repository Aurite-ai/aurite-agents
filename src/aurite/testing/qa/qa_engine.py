"""
QA Engine for the Aurite Testing Framework.

This module provides the Level 2 orchestrator for Quality Assurance testing.
It manages QA testing across all component types, handling test case distribution,
result aggregation, and integration with the broader testing framework.
"""

import asyncio
import inspect
import json
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import jsonschema

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.config.config_manager import ConfigManager
from aurite.lib.models.api.requests import EvaluationCase, EvaluationRequest
from aurite.lib.models.config.components import LLMConfig

from ..runners.agent_runner import AgentRunner
from .base_qa_tester import BaseQATester
from .qa_models import (
    CaseEvaluationResult,
    ExpectationAnalysisResult,
    QAEvaluationResult,
    SchemaValidationResult,
)

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)


__all__ = ["QAEngine", "evaluate"]


class QAEngine:
    """
    Level 2 Orchestrator for Quality Assurance testing.

    This class manages QA testing across all component types, coordinating
    test execution, result aggregation, and reporting. It serves as the
    main entry point for all QA operations in the testing framework.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the QA Engine.

        Args:
            config_manager: Optional ConfigManager for accessing configurations
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self._component_testers: Dict[str, BaseQATester] = {}
        self._initialize_component_testers()

    def _initialize_component_testers(self) -> None:
        """Initialize component-specific testers (Level 3)."""
        # TODO: Initialize specific testers when they are implemented
        # For now, we'll add them as they're created
        pass

    async def evaluate_component(
        self, request: EvaluationRequest, executor: Optional["AuriteEngine"] = None
    ) -> QAEvaluationResult:
        """
        Main entry point for component evaluation.

        This method replaces the old `evaluate` function and provides
        the same functionality with improved structure and error handling.

        Args:
            request: The evaluation request containing test cases
            executor: Optional AuriteEngine for component execution

        Returns:
            QAEvaluationResult containing the evaluation results
        """
        evaluation_id = f"qa_{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow()

        self.logger.info(f"Starting QA evaluation {evaluation_id}")

        try:
            # Get or create LLM client for evaluation
            llm_client = await self._get_llm_client(request, executor)

            # Execute all test cases in parallel
            tasks = [
                self._evaluate_single_case(case=case, llm_client=llm_client, request=request, executor=executor)
                for case in request.test_cases
            ]

            case_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle any exceptions
            processed_results: Dict[str, CaseEvaluationResult] = {}
            failed_count = 0

            for _i, (case, result) in enumerate(zip(request.test_cases, case_results, strict=False)):
                case_id_str = str(case.id)  # Convert UUID to string
                if isinstance(result, Exception):
                    # Create a failed result for exceptions
                    processed_results[case_id_str] = CaseEvaluationResult(
                        case_id=case_id_str,
                        input=case.input,
                        output=None,
                        grade="FAIL",
                        analysis=f"Test execution failed: {str(result)}",
                        expectations_broken=case.expectations,
                        error=str(result),
                    )
                    failed_count += 1
                elif isinstance(result, CaseEvaluationResult):
                    processed_results[case_id_str] = result
                    if result.grade == "FAIL":
                        failed_count += 1

            # Calculate overall score
            passed_count = len(processed_results) - failed_count
            overall_score = (passed_count / len(processed_results)) * 100 if processed_results else 0

            # Generate recommendations
            recommendations = self._generate_recommendations(list(processed_results.values()))

            # Determine overall status
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
                component_type=request.eval_type,
                component_name=request.eval_name,
                overall_score=overall_score,
                total_cases=len(processed_results),
                passed_cases=passed_count,
                failed_cases=failed_count,
                case_results=processed_results,
                recommendations=recommendations,
                metadata={
                    "original_request": request.model_dump() if hasattr(request, "model_dump") else None,
                    "review_llm": request.review_llm,
                    "framework": getattr(request, "framework", "aurite"),
                },
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
            )

        except Exception as e:
            self.logger.error(f"QA evaluation {evaluation_id} failed: {e}")
            completed_at = datetime.utcnow()

            return QAEvaluationResult(
                evaluation_id=evaluation_id,
                status="failed",
                component_type=request.eval_type,
                component_name=request.eval_name,
                overall_score=0,
                total_cases=len(request.test_cases),
                passed_cases=0,
                failed_cases=len(request.test_cases),
                case_results={},
                recommendations=[f"Evaluation failed: {str(e)}"],
                metadata={"error": str(e)},
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
            )

    async def _evaluate_single_case(
        self,
        case: EvaluationCase,
        llm_client: LiteLLMClient,
        request: EvaluationRequest,
        executor: Optional["AuriteEngine"] = None,
    ) -> CaseEvaluationResult:
        """
        Evaluate a single test case.

        Args:
            case: The test case to evaluate
            llm_client: LLM client for expectation analysis
            request: The overall evaluation request
            executor: Optional AuriteEngine for component execution

        Returns:
            CaseEvaluationResult for this test case
        """
        start_time = datetime.utcnow()

        try:
            # Get the output (either provided or by running the component)
            output = await self._get_case_output(case, request, executor)

            # Validate schema if provided
            schema_result = None
            if request.expected_schema:
                schema_result = self._validate_schema(output, request.expected_schema)
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

            # Analyze expectations using LLM
            if case.expectations:
                expectation_result = await self._analyze_expectations(case, output, llm_client)

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
                    analysis="No expectations defined, output generated successfully",
                    expectations_broken=[],
                    schema_valid=schema_result.is_valid if schema_result else True,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                )

        except Exception as e:
            self.logger.error(f"Error evaluating case {case.id}: {e}")
            return CaseEvaluationResult(
                case_id=str(case.id),
                input=case.input,
                output=None,
                grade="FAIL",
                analysis=f"Evaluation failed: {str(e)}",
                expectations_broken=case.expectations,
                error=str(e),
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )

    async def _get_case_output(
        self, case: EvaluationCase, request: EvaluationRequest, executor: Optional["AuriteEngine"] = None
    ) -> Any:
        """
        Get the output for a test case, either from the case itself or by running the component.

        Args:
            case: The test case
            request: The evaluation request
            executor: Optional AuriteEngine for component execution

        Returns:
            The output for the test case
        """
        # If output is already provided, use it
        if case.output is not None:
            return case.output

        # Otherwise, we need to run the component
        if request.run_agent:
            if isinstance(request.run_agent, str):
                # It's an agent name
                runner = AgentRunner(request.run_agent)
                return await runner.execute(case.input, **request.run_agent_kwargs)
            elif inspect.iscoroutinefunction(request.run_agent):
                # It's an async function
                return await request.run_agent(case.input, **request.run_agent_kwargs)
            else:
                # It's a regular callable
                return request.run_agent(case.input, **request.run_agent_kwargs)

        elif request.eval_type and request.eval_name and executor:
            # Use the executor to run the component
            match request.eval_type:
                case "agent":
                    result = await executor.run_agent(
                        agent_name=request.eval_name,
                        user_message=case.input,
                    )
                    return result.primary_text
                case "linear_workflow":
                    return await executor.run_linear_workflow(
                        workflow_name=request.eval_name,
                        initial_input=case.input,
                    )
                case "custom_workflow":
                    return await executor.run_custom_workflow(
                        workflow_name=request.eval_name,
                        initial_input=case.input,
                    )
                case _:
                    raise ValueError(f"Unrecognized eval_type: {request.eval_type}")
        else:
            raise ValueError(
                f"Case {case.id}: No output provided and no way to generate it "
                "(run_agent and eval_name/eval_type not specified)"
            )

    def _validate_schema(self, output: Any, expected_schema: Dict[str, Any]) -> SchemaValidationResult:
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

    async def _analyze_expectations(
        self, case: EvaluationCase, output: Any, llm_client: LiteLLMClient
    ) -> ExpectationAnalysisResult:
        """
        Use an LLM to analyze whether the output meets the expectations.

        Args:
            case: The test case with expectations
            output: The output to analyze
            llm_client: The LLM client to use for analysis

        Returns:
            ExpectationAnalysisResult with the analysis
        """
        expectations_str = "\n".join(case.expectations)

        analysis_output = await llm_client.create_message(
            messages=[
                {
                    "role": "user",
                    "content": f"Expectations:\n{expectations_str}\n\nInput:{case.input}\n\nOutput:{output}",
                }
            ],
            tools=None,
            system_prompt_override="""You are an expert Quality Assurance Engineer. Your job is to review the output from an agent and make sure it meets a list of expectations.
Your output should be your analysis of its performance, and a list of which expectations were broken (if any). These strings should be identical to the original expectation strings.

Format your output as JSON. IMPORTANT: Do not include any other text before or after, and do NOT format it as a code block (```). Here is a template: {
"analysis": "<your analysis here>",
"expectations_broken": ["<broken expectation 1>", "<broken expectation 2>", "etc"]
}""",
        )

        analysis_text = analysis_output.content

        if analysis_text is None:
            raise ValueError("Evaluation LLM returned no content")

        try:
            # Clean the output and parse JSON
            cleaned_output = self._clean_llm_output(analysis_text)
            analysis_json = json.loads(cleaned_output)

            return ExpectationAnalysisResult(
                analysis=analysis_json.get("analysis", "No analysis provided"),
                expectations_broken=analysis_json.get("expectations_broken", []),
            )

        except Exception as e:
            self.logger.error(f"Error parsing LLM analysis output: {e}")
            # Return a failed analysis
            return ExpectationAnalysisResult(
                analysis=f"Failed to parse LLM output: {str(e)}",
                expectations_broken=case.expectations,  # Assume all failed if we can't parse
            )

    def _clean_llm_output(self, output: str) -> str:
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

    async def _get_llm_client(
        self, request: EvaluationRequest, executor: Optional["AuriteEngine"] = None
    ) -> LiteLLMClient:
        """
        Get or create an LLM client for evaluation.

        Args:
            request: The evaluation request
            executor: Optional AuriteEngine with config manager

        Returns:
            LiteLLMClient for evaluation
        """
        if request.review_llm and executor and self.config_manager:
            # Use the specified LLM configuration
            llm_config = self.config_manager.get_config(component_type="llm", component_id=request.review_llm)

            if not llm_config:
                raise ValueError(f"No config found for LLM: {request.review_llm}")

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

    def _generate_recommendations(self, results: List[CaseEvaluationResult]) -> List[str]:
        """
        Generate recommendations based on test results.

        Args:
            results: List of case evaluation results

        Returns:
            List of recommendations
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

    def register_component_tester(self, component_type: str, tester: BaseQATester) -> None:
        """
        Register a component-specific tester.

        Args:
            component_type: The type of component this tester handles
            tester: The tester instance
        """
        self._component_testers[component_type] = tester
        self.logger.info(f"Registered QA tester for component type: {component_type}")


# Backward compatibility function
async def evaluate(
    request: EvaluationRequest,
    executor: Optional["AuriteEngine"] = None,
) -> Any:
    """
    Backward compatibility wrapper for the old evaluate function.

    This function maintains the same interface as the original evaluator
    to ensure existing code continues to work during the migration.

    Args:
        request: The EvaluationRequest object
        executor: The AuriteEngine instance to run agents

    Returns:
        A dictionary containing the result in the legacy format
    """
    # Create a QAEngine instance
    config_manager = executor._config_manager if executor else None
    qa_engine = QAEngine(config_manager=config_manager)

    # Run the evaluation
    result = await qa_engine.evaluate_component(request, executor)

    # Convert to legacy format
    return result.to_legacy_format()
