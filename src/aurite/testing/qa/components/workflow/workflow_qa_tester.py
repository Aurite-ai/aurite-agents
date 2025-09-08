"""
Workflow QA Tester for the Aurite Testing Framework.

This module provides quality assurance testing specifically for workflow components,
evaluating end-to-end execution, agent coordination, data flow integrity, and step validation.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.models.config.components import LLMConfig

from ...base_qa_tester import BaseQATester
from ...qa_models import (
    CaseEvaluationResult,
    ComponentQAConfig,
    ExpectationAnalysisResult,
    QAEvaluationResult,
    QATestCategory,
    QATestRequest,
    SchemaValidationResult,
)

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)

__all__ = ["WorkflowQATester"]


class WorkflowQATester(BaseQATester):
    """
    Component-specific QA tester for workflows (Level 3).

    This tester evaluates workflow performance across multiple dimensions:
    - End-to-End Execution: Complete workflow execution from start to finish
    - Agent Coordination: How well agents work together and pass data
    - Data Flow Integrity: Proper data transformation and passing between steps
    - Step Validation: Individual step execution and error handling
    """

    def __init__(self, config: Optional[ComponentQAConfig] = None):
        """
        Initialize the Workflow QA tester.

        Args:
            config: Optional configuration for workflow-specific testing
        """
        if config is None:
            config = ComponentQAConfig(
                component_type="workflow",  # Base type for workflows
                test_categories=self._get_default_test_categories(),
                default_timeout=120.0,  # Workflows may take longer due to multiple steps
                parallel_execution=False,  # Workflows are inherently sequential
                max_retries=1,
            )

        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_default_test_categories(self) -> List[QATestCategory]:
        """Get default test categories for workflow testing."""
        return [
            QATestCategory(
                name="end_to_end_execution",
                description="Complete workflow execution from start to finish",
                weight=0.4,  # Most important for workflows
                required=True,
            ),
            QATestCategory(
                name="agent_coordination",
                description="How well agents work together and coordinate tasks",
                weight=0.3,
                required=True,
            ),
            QATestCategory(
                name="data_flow_integrity",
                description="Proper data transformation and passing between steps",
                weight=0.2,
                required=True,
            ),
            QATestCategory(
                name="step_validation",
                description="Individual step execution and error handling",
                weight=0.1,
                required=False,
            ),
        ]

    async def test_component(
        self, request: QATestRequest, executor: Optional["AuriteEngine"] = None
    ) -> QAEvaluationResult:
        """
        Execute QA tests for a workflow component.

        Args:
            request: The QA test request containing test cases and configuration
            executor: Optional AuriteEngine instance for executing the workflow

        Returns:
            QAEvaluationResult containing the test results
        """
        evaluation_id = f"workflow_qa_{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow()

        self.logger.info(
            f"Starting workflow QA testing {evaluation_id} for component: {request.component_config.get('name', 'unknown')}"
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

            # Execute all test cases (workflows are typically run sequentially)
            if self.config.parallel_execution:
                tasks = [
                    self._evaluate_single_case(case=case, llm_client=llm_client, request=request, executor=executor)
                    for case in request.test_cases
                ]
                case_results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Sequential execution for workflows
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
                        analysis=f"Workflow test execution failed: {str(result)}",
                        expectations_broken=case.expectations,
                        error=str(result),
                    )
                    failed_count += 1
                elif isinstance(result, CaseEvaluationResult):
                    processed_results[case_id_str] = result
                    if result.grade == "FAIL":
                        failed_count += 1

            # Calculate overall score using workflow-specific scoring
            overall_score = self.aggregate_scores(list(processed_results.values()))

            # Generate workflow-specific recommendations
            recommendations = self._generate_workflow_recommendations(list(processed_results.values()), request)

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
                component_type="workflow",
                component_name=request.component_config.get("name", "unknown"),
                overall_score=overall_score,
                total_cases=len(processed_results),
                passed_cases=passed_count,
                failed_cases=failed_count,
                case_results=processed_results,
                recommendations=recommendations,
                metadata={
                    "workflow_config": request.component_config,
                    "test_categories": [cat.name for cat in self.get_test_categories()],
                    "workflow_type": request.component_config.get("type", "linear_workflow"),
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
        llm_client: LiteLLMClient,
        request: QATestRequest,
        executor: Optional["AuriteEngine"] = None,
    ) -> CaseEvaluationResult:
        """
        Evaluate a single test case for a workflow.

        Args:
            case: The test case to evaluate
            llm_client: LLM client for expectation analysis
            request: The overall test request
            executor: Optional AuriteEngine for workflow execution

        Returns:
            CaseEvaluationResult for this test case
        """
        start_time = datetime.utcnow()

        try:
            # Get the output (either provided or by running the workflow)
            output = await self._get_workflow_output(case, request, executor)

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
                expectation_result = await self._analyze_workflow_expectations(case, output, llm_client, request)

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
                    analysis="No expectations defined, workflow output generated successfully",
                    expectations_broken=[],
                    schema_valid=schema_result.is_valid if schema_result else True,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                )

        except Exception as e:
            self.logger.error(f"Error evaluating workflow case {case.id}: {e}")
            return CaseEvaluationResult(
                case_id=str(case.id),
                input=case.input,
                output=None,
                grade="FAIL",
                analysis=f"Workflow evaluation failed: {str(e)}",
                expectations_broken=case.expectations,
                error=str(e),
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )

    async def _get_workflow_output(self, case, request: QATestRequest, executor: Optional["AuriteEngine"] = None):
        """
        Get the output for a test case by running the workflow.

        Args:
            case: The test case
            request: The test request
            executor: Optional AuriteEngine for workflow execution

        Returns:
            The output from the workflow
        """
        # If output is already provided, use it
        if case.output is not None:
            return case.output

        # Otherwise, we need to run the workflow
        if not executor:
            raise ValueError(f"Case {case.id}: No output provided and no executor available to run workflow")

        workflow_name = request.eval_name or request.component_config.get("name")
        if not workflow_name:
            raise ValueError(f"Case {case.id}: No workflow name specified for execution")

        # Determine workflow type from config
        workflow_type = request.component_config.get("type", "linear_workflow")

        # Run the workflow using the executor
        if workflow_type == "linear_workflow":
            result = await executor.run_linear_workflow(
                workflow_name=workflow_name,
                initial_input=case.input,
            )
        elif workflow_type == "custom_workflow":
            result = await executor.run_custom_workflow(
                workflow_name=workflow_name,
                initial_input=case.input,
            )
        else:
            raise ValueError(f"Unsupported workflow type: {workflow_type}")

        return result

    def _validate_schema(self, output, expected_schema: Dict) -> SchemaValidationResult:
        """
        Validate workflow output against an expected JSON schema.

        Args:
            output: The workflow output to validate
            expected_schema: The JSON schema to validate against

        Returns:
            SchemaValidationResult with validation details
        """
        try:
            import jsonschema

            # Convert output to JSON if it's a string
            if isinstance(output, str):
                try:
                    data_to_validate = json.loads(output)
                except json.JSONDecodeError:
                    return SchemaValidationResult(
                        is_valid=False,
                        error_message="Workflow output is not valid JSON",
                        validation_errors=["Failed to parse workflow output as JSON"],
                    )
            elif isinstance(output, dict):
                data_to_validate = output
            else:
                return SchemaValidationResult(
                    is_valid=False,
                    error_message="Workflow output is not a string or dictionary",
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

    async def _analyze_workflow_expectations(
        self, case, output, llm_client: LiteLLMClient, request: QATestRequest
    ) -> ExpectationAnalysisResult:
        """
        Use an LLM to analyze whether the workflow output meets the expectations.

        Args:
            case: The test case with expectations
            output: The workflow output to analyze
            llm_client: The LLM client to use for analysis
            request: The test request for context

        Returns:
            ExpectationAnalysisResult with the analysis
        """
        expectations_str = "\n".join(case.expectations)
        workflow_config = request.component_config

        # Create workflow-specific analysis prompt
        steps = workflow_config.get("steps", [])
        step_names = []
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict):
                    step_names.append(step.get("name", "unnamed"))
                elif isinstance(step, str):
                    step_names.append(step)

        system_prompt = f"""You are an expert Quality Assurance Engineer specializing in AI workflow evaluation.

You are evaluating a workflow with the following configuration:
- Workflow Name: {workflow_config.get("name", "Unknown")}
- Workflow Type: {workflow_config.get("type", "linear_workflow")}
- Number of Steps: {len(steps)}
- Step Names: {", ".join(step_names) if step_names else "Not specified"}
- Timeout: {workflow_config.get("timeout_seconds", "Not specified")} seconds
- Parallel Execution: {workflow_config.get("parallel_execution", False)}

Your job is to review the workflow's output and determine if it meets the specified expectations.

Focus on:
1. End-to-End Execution: Did the workflow complete successfully from start to finish?
2. Agent Coordination: Do the results show proper coordination between workflow steps?
3. Data Flow Integrity: Is the data properly transformed and passed between steps?
4. Step Validation: Are individual steps executing correctly?

Format your output as JSON. IMPORTANT: Do not include any other text before or after, and do NOT format it as a code block (```). Here is the template:
{{
"analysis": "<your detailed analysis here>",
"expectations_broken": ["<broken expectation 1>", "<broken expectation 2>", "etc"]
}}"""

        analysis_output = await llm_client.create_message(
            messages=[
                {
                    "role": "user",
                    "content": f"Expectations:\n{expectations_str}\n\nWorkflow Input: {case.input}\n\nWorkflow Output: {output}",
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

    async def _get_llm_client(self, request: QATestRequest, executor: Optional["AuriteEngine"] = None) -> LiteLLMClient:
        """
        Get or create an LLM client for evaluation.

        Args:
            request: The test request
            executor: Optional AuriteEngine with config manager

        Returns:
            LiteLLMClient for evaluation
        """
        if request.review_llm and executor and executor._config_manager:
            # Use the specified LLM configuration
            llm_config = executor._config_manager.get_config(component_type="llm", component_id=request.review_llm)

            if not llm_config:
                raise ValueError(f"No config found for LLM: {request.review_llm}")

            return LiteLLMClient(LLMConfig(**llm_config))
        else:
            # Use default Anthropic configuration
            default_config = LLMConfig(
                name="Default Workflow QA Evaluator",
                type="llm",
                model="claude-3-5-sonnet-20241022",
                provider="anthropic",
                temperature=0.1,
            )
            return LiteLLMClient(default_config)

    def _generate_workflow_recommendations(
        self, results: List[CaseEvaluationResult], request: QATestRequest
    ) -> List[str]:
        """
        Generate workflow-specific recommendations based on test results.

        Args:
            results: List of case evaluation results
            request: Original test request

        Returns:
            List of workflow-specific recommendation strings
        """
        recommendations = []
        workflow_config = request.component_config

        if not results:
            return recommendations

        failed_cases = [r for r in results if r.grade == "FAIL"]

        # Analyze workflow structure
        steps = workflow_config.get("steps", [])
        if not steps:
            recommendations.append("Workflow has no defined steps. Add workflow steps to enable execution.")
            return recommendations

        if len(steps) < 2:
            recommendations.append("Workflow has only one step. Consider if this should be a simple agent instead.")

        # Analyze step configuration issues
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                if not step.get("name"):
                    recommendations.append(
                        f"Step {i + 1} is missing a name. Add descriptive names for better debugging."
                    )

                if not step.get("agent"):
                    recommendations.append(
                        f"Step {i + 1} ({step.get('name', 'unnamed')}) is missing agent specification."
                    )

                # Check for data flow issues
                input_mapping = step.get("input_mapping", {})
                if not input_mapping and i > 0:
                    recommendations.append(
                        f"Step {i + 1} ({step.get('name', 'unnamed')}) has no input mapping. "
                        "Consider how data flows from previous steps."
                    )

        # Analyze timeout settings
        timeout = workflow_config.get("timeout_seconds", 60)
        if timeout < 30 and len(steps) > 2:
            recommendations.append(
                f"Timeout ({timeout}s) may be too short for a {len(steps)}-step workflow. "
                "Consider increasing to allow adequate time for all steps."
            )

        # Analyze error handling
        error_handling = workflow_config.get("error_handling", {})
        if not error_handling:
            recommendations.append(
                "No error handling configuration found. Add error handling strategy for better reliability."
            )
        else:
            retry_attempts = error_handling.get("retry_attempts", 0)
            if retry_attempts == 0 and len(failed_cases) > 0:
                recommendations.append(
                    "No retry attempts configured but failures detected. Consider adding retry logic."
                )

        # Analyze parallel execution settings
        parallel_execution = workflow_config.get("parallel_execution", False)
        if parallel_execution and workflow_config.get("type") == "linear_workflow":
            recommendations.append(
                "Parallel execution enabled for linear workflow. This may cause unexpected behavior."
            )

        # Analyze execution time patterns
        slow_cases = [r for r in results if r.execution_time and r.execution_time > 60]
        if slow_cases and len(slow_cases) > len(results) / 2:
            recommendations.append(
                f"{len(slow_cases)} test cases took >60 seconds. Consider optimizing workflow steps or increasing timeout."
            )

        # Analyze failure patterns for coordination issues
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

        Performs any necessary initialization for workflow testing.
        """
        self.logger.debug("Setting up workflow QA tester")
        # Add any workflow-specific setup here
        pass

    async def teardown(self) -> None:
        """
        Teardown method called after running tests.

        Performs cleanup after workflow testing.
        """
        self.logger.debug("Tearing down workflow QA tester")
        # Add any workflow-specific cleanup here
        pass

    def validate_request(self, request: QATestRequest) -> List[str]:
        """
        Validate the test request for workflow-specific requirements.

        Args:
            request: The test request to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        # Custom validation that bypasses base class component type check
        errors = []

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

        # Workflow-specific validations
        if request.component_type not in ["workflow", "linear_workflow", "custom_workflow", "graph_workflow"]:
            errors.append(f"Component type must be workflow-related, got '{request.component_type}'")

        # Validate workflow configuration has required fields
        workflow_config = request.component_config
        if not workflow_config.get("name"):
            errors.append("Workflow configuration missing required 'name' field")

        workflow_type = workflow_config.get("type", "linear_workflow")
        if workflow_type not in ["linear_workflow", "custom_workflow", "graph_workflow"]:
            errors.append(f"Invalid workflow type: {workflow_type}")

        # Validate workflow has steps (for linear workflows)
        if workflow_type == "linear_workflow":
            steps = workflow_config.get("steps", [])
            if not steps:
                errors.append("Linear workflow missing required 'steps' field")
            elif len(steps) == 0:
                errors.append("Linear workflow has empty steps list")

        # Validate custom workflow has required fields
        elif workflow_type == "custom_workflow":
            if not workflow_config.get("module_path"):
                errors.append("Custom workflow missing required 'module_path' field")
            if not workflow_config.get("class_name"):
                errors.append("Custom workflow missing required 'class_name' field")

        # Validate test cases have appropriate expectations for workflows
        for case in request.test_cases:
            if not case.expectations:
                continue

            # Check for workflow-relevant expectations
            workflow_keywords = ["workflow", "step", "coordination", "data flow", "end-to-end", "complete"]
            has_workflow_expectation = any(
                keyword in " ".join(case.expectations).lower() for keyword in workflow_keywords
            )

            if not has_workflow_expectation:
                errors.append(
                    f"Test case {case.id}: Expectations may not be suitable for workflow testing. "
                    "Consider including expectations about workflow execution or step coordination."
                )

        return errors
