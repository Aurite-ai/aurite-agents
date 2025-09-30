"""
Unified QA Engine for the Aurite Testing Framework.

This module provides the complete orchestration and execution of Quality Assurance
testing for all component types. It handles evaluation request processing, component
execution, result caching, and LLM-based expectation analysis.
"""

import asyncio
import inspect
import json
import logging
import random
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.config.config_manager import ConfigManager
from aurite.lib.models.config.components import EvaluationCase, EvaluationConfig, LLMConfig

from ..runners.agent_runner import AgentRunner
from .qa_models import CaseEvaluationResult, ExpectationAnalysisResult, QAEvaluationResult
from .qa_session_manager import QASessionManager
from .qa_utils import clean_llm_output, format_agent_conversation_history, validate_schema

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)


class QAEngine:
    """
    Unified QA Engine for Quality Assurance testing.

    This class manages the complete QA testing workflow:
    - Processing evaluation requests
    - Executing components (agents, workflows, MCP servers)
    - Caching results for performance
    - Analyzing outputs with LLM-as-judge
    - Managing parallel execution and rate limiting
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        session_manager: Optional[QASessionManager] = None,
    ):
        """
        Initialize the QA Engine.

        Args:
            config_manager: Optional ConfigManager for accessing configurations
            session_manager: Optional QASessionManager for caching and persistence
        """
        self.config_manager = config_manager
        self.qa_session_manager = session_manager
        self.logger = logging.getLogger(__name__)

        # Track failed MCP servers to prevent parallel retry attempts
        self._failed_mcp_servers: List[str] = []
        # Cache for MCP server test agents to reuse across test cases
        self._mcp_test_agents: Dict[str, str] = {}

        # Rate limiting configuration
        self._max_concurrent_tests = 3  # Default value
        self._rate_limit_retry_count = 3  # Default value
        self._rate_limit_base_delay = 1.0  # Default value
        self._semaphore: Optional[asyncio.Semaphore] = None

    # ============================================================================
    # Public Interface Methods
    # ============================================================================

    async def evaluate_component(
        self, request: EvaluationConfig, executor: Optional["AuriteEngine"] = None
    ) -> Dict[str, QAEvaluationResult]:
        """
        Main entry point for component evaluation.

        This method handles both single and multiple component evaluations.
        For multiple components, it runs evaluations in parallel and returns
        a dictionary with component names as keys.

        Args:
            request: The evaluation request containing test cases
            executor: Optional AuriteEngine for component execution

        Returns:
            Dictionary mapping component names to QAEvaluationResult objects
        """
        self.logger.info(f"QAEngine: Starting QA evaluation for component type: {request.component_type}")
        self.logger.info(f"QAEngine: Component refs: {request.component_refs}")
        self.logger.info(f"QAEngine: Test cases count: {len(request.test_cases)}")
        self.logger.info(f"QAEngine: Review LLM: {request.review_llm}")

        # Resolve evaluation mode if not explicitly set
        mode = request.resolve_mode()
        self.logger.info(f"QAEngine: Resolved evaluation mode: {mode}")

        # Determine component type
        component_type = request.component_type or "agent"  # Default to agent if not specified
        self.logger.info(f"QAEngine: Resolved component type: {component_type}")

        # Handle multiple components if specified
        if request.component_refs and len(request.component_refs) > 1:
            return await self._evaluate_multiple_components(request, executor)

        # Handle single component based on evaluation mode
        component_name = None

        if mode == "manual":
            # Manual output evaluation - no component loading needed
            component_name = request.component_refs[0] if request.component_refs else "manual_evaluation"
            self.logger.info(f"QAEngine: Manual mode - using component name: {component_name}")
        elif mode == "function":
            # Function-based evaluation - no component loading needed
            component_name = request.component_refs[0] if request.component_refs else "function_evaluation"
            self.logger.info(f"QAEngine: Function mode - using component name: {component_name}")
        else:
            # Aurite mode - load component configuration
            if request.component_refs and len(request.component_refs) >= 1:
                component_name = request.component_refs[0]

            # Get component config - prefer provided config over loading from ConfigManager
            if request.component_config:
                # Use the provided component configuration
                component_name = request.component_config.get("name", component_name or "unknown")
                self.logger.info(f"QAEngine: Using provided component config for {component_name}")
            elif self.config_manager and component_name:
                # Try to load from ConfigManager
                try:
                    self.logger.info(f"QAEngine: Loading component config for {component_type}.{component_name}")
                    config = self.config_manager.get_config(component_type=component_type, component_id=component_name)
                    if config:
                        request.component_config = config
                        self.logger.info("QAEngine: Successfully loaded component config")
                    else:
                        self.logger.warning(f"QAEngine: No config found for {component_type}.{component_name}")
                except Exception as e:
                    self.logger.warning(f"QAEngine: Could not load component config: {e}")

        self.logger.info("QAEngine: Starting test execution")
        # Execute the evaluation
        result = await self._test_component(request, executor)

        self.logger.info(f"QAEngine: Test completed with status: {result.status}")
        self.logger.info(f"QAEngine: Overall score: {result.overall_score:.2f}%")
        self.logger.info(
            f"QAEngine: Passed/Failed/Total: {result.passed_cases}/{result.failed_cases}/{result.total_cases}"
        )

        # Save result to storage if we have a session manager
        if self.qa_session_manager:
            config_id = component_name or "unknown"
            self.qa_session_manager.save_test_result(result.model_dump(), config_id)

        # Return single result in dictionary format for consistency
        return {component_name or "component": result}

    async def evaluate_by_config_id(
        self,
        evaluation_config_id: str,
        executor: Optional["AuriteEngine"] = None,
        test_cases_filter: Optional[str] = None,
    ) -> Dict[str, QAEvaluationResult]:
        """
        Evaluate components using a saved evaluation configuration.

        This method loads an evaluation configuration from the ConfigManager
        and executes the evaluation based on the saved test cases and settings.
        Supports both single and multiple component evaluations.

        Args:
            evaluation_config_id: ID of the evaluation configuration to load
            executor: Optional AuriteEngine for component execution
            test_cases_filter: Optional filter string for test cases (names, indices, or patterns)

        Returns:
            Dictionary mapping component names to QAEvaluationResult objects
        """
        if not self.config_manager:
            raise ValueError("ConfigManager is required to load evaluation configurations")

        # Load the evaluation configuration
        eval_config = self.config_manager.get_config("evaluation", evaluation_config_id)
        if not eval_config:
            raise ValueError(f"Evaluation configuration '{evaluation_config_id}' not found")

        shared_fields = set(EvaluationConfig.model_fields.keys())
        request_data = {field: eval_config[field] for field in shared_fields if field in eval_config}

        # Apply test case filtering if specified
        if test_cases_filter and "test_cases" in request_data:
            filtered_cases = self._filter_test_cases(request_data["test_cases"], test_cases_filter)
            if not filtered_cases:
                raise ValueError(f"No test cases matched filter: {test_cases_filter}")
            self.logger.info(
                f"QAEngine: Filtered from {len(request_data['test_cases'])} to {len(filtered_cases)} test cases"
            )
            request_data["test_cases"] = filtered_cases

        request = EvaluationConfig(**request_data)

        # Execute the evaluation
        return await self.evaluate_component(request, executor)

    # ============================================================================
    # Core Evaluation Methods
    # ============================================================================

    async def _test_component(
        self, request: EvaluationConfig, executor: Optional["AuriteEngine"] = None
    ) -> QAEvaluationResult:
        """
        Execute QA tests for any component type.

        Args:
            request: The QA test request containing test cases and configuration
            executor: Optional AuriteEngine instance for executing the component

        Returns:
            QAEvaluationResult containing the test results
        """
        evaluation_id = f"qa_{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow()

        self.logger.info(f"Starting QA testing {evaluation_id}")

        # Check for cached evaluation result first
        if request.use_cache and not request.force_refresh and request.evaluation_config_id and self.qa_session_manager:
            evaluation_cache_key = self.qa_session_manager.generate_evaluation_cache_key(
                evaluation_config_id=request.evaluation_config_id,
                test_cases=request.test_cases,
                review_llm=request.review_llm,
            )

            cached_evaluation = await self.qa_session_manager.get_cached_evaluation_result(
                cache_key=evaluation_cache_key,
                cache_ttl=request.cache_ttl,
            )

            if cached_evaluation:
                self.logger.info(f"Using cached evaluation result for {evaluation_id}")
                # Update timing to reflect cache hit
                cached_evaluation.started_at = started_at
                cached_evaluation.completed_at = datetime.utcnow()
                cached_evaluation.duration_seconds = (cached_evaluation.completed_at - started_at).total_seconds()
                return cached_evaluation

        self.logger.debug("No cached evaluation found, executing component tests")

        # Pre-register MCP servers if needed
        await self._pre_register_mcp_servers(request, executor)

        # Get LLM client for evaluation
        llm_client = await self._get_llm_client(request, executor)

        # Initialize semaphore for rate limiting
        if self._semaphore is None:
            max_concurrent = getattr(request, "max_concurrent_tests", self._max_concurrent_tests)
            self._semaphore = asyncio.Semaphore(max_concurrent)
            self.logger.info(f"Initialized rate limiting with max {max_concurrent} concurrent test cases")

        # Create tasks with semaphore-controlled execution
        tasks = [
            self._evaluate_single_case_with_semaphore(
                case=case, llm_client=llm_client, request=request, executor=executor
            )
            for case in request.test_cases
        ]
        case_results = await asyncio.gather(*tasks, return_exceptions=True)

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
        overall_score = self.aggregate_scores(list(processed_results.values()))

        # Determine overall status
        passed_count = len(processed_results) - failed_count
        if failed_count == 0:
            status = "success"
        elif failed_count == len(processed_results):
            status = "failed"
        else:
            status = "partial"

        completed_at = datetime.utcnow()

        evaluation_result = QAEvaluationResult(
            evaluation_id=evaluation_id,
            status=status,
            component_type=request.component_type,
            component_name=request.component_config.get("name", "unknown") if request.component_config else None,
            overall_score=overall_score,
            total_cases=len(processed_results),
            passed_cases=passed_count,
            failed_cases=failed_count,
            case_results=processed_results,
            metadata={
                "component_config": request.component_config,
                "component_type": request.component_type,
            },
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=(completed_at - started_at).total_seconds(),
        )

        # Store evaluation result in cache
        if request.use_cache and request.evaluation_config_id and self.qa_session_manager:
            evaluation_cache_key = self.qa_session_manager.generate_evaluation_cache_key(
                evaluation_config_id=request.evaluation_config_id,
                test_cases=request.test_cases,
                review_llm=request.review_llm,
            )

            await self.qa_session_manager.store_cached_evaluation_result(
                cache_key=evaluation_cache_key,
                result=evaluation_result,
            )

        return evaluation_result

    async def _evaluate_single_case_with_semaphore(
        self,
        case: EvaluationCase,
        llm_client: LiteLLMClient,
        request: EvaluationConfig,
        executor: Optional["AuriteEngine"] = None,
    ) -> CaseEvaluationResult:
        """
        Wrapper that uses semaphore to control concurrent execution.

        Args:
            case: The test case to evaluate
            llm_client: LLM client for expectation analysis
            request: The overall test request
            executor: Optional AuriteEngine for component execution

        Returns:
            CaseEvaluationResult for this test case
        """
        # Ensure semaphore exists
        if self._semaphore is None:
            max_concurrent = getattr(request, "max_concurrent_tests", self._max_concurrent_tests)
            self._semaphore = asyncio.Semaphore(max_concurrent)

        async with self._semaphore:
            # Add retry logic for rate limit errors
            last_exception = None
            retry_count = getattr(request, "rate_limit_retry_count", self._rate_limit_retry_count)
            base_delay = getattr(request, "rate_limit_base_delay", self._rate_limit_base_delay)

            for retry_attempt in range(retry_count):
                try:
                    result = await self._evaluate_single_case(case, llm_client, request, executor)
                    return result
                except Exception as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    # Check if this is a rate limit error
                    if any(
                        rate_indicator in error_msg
                        for rate_indicator in ["rate limit", "too many requests", "429", "rate_limit"]
                    ):
                        if retry_attempt < retry_count - 1:
                            # Calculate exponential backoff with jitter
                            delay = base_delay * (2**retry_attempt)
                            jitter = random.uniform(0, delay * 0.3)  # Add up to 30% jitter
                            total_delay = delay + jitter

                            self.logger.warning(
                                f"Rate limit hit for test case {case.id}, "
                                f"retrying in {total_delay:.2f} seconds "
                                f"(attempt {retry_attempt + 1}/{retry_count})"
                            )
                            await asyncio.sleep(total_delay)
                            continue
                        else:
                            self.logger.error(f"Max retries exceeded for test case {case.id} due to rate limiting")
                    # Re-raise the exception if not a rate limit or max retries exceeded
                    raise

            # If we get here, all retries failed - raise the last exception
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"Failed to evaluate test case {case.id} after {retry_count} attempts")

    async def _evaluate_single_case(
        self,
        case: EvaluationCase,
        llm_client: LiteLLMClient,
        request: EvaluationConfig,
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
            # Check for cached result first
            cached_result = None
            if request.use_cache and not request.force_refresh and self.qa_session_manager:
                cache_key = self.qa_session_manager.generate_case_cache_key(
                    case_input=str(case.input),
                    component_config=request.component_config,
                    evaluation_config_id=request.evaluation_config_id,
                    review_llm=request.review_llm,
                    expectations=case.expectations,
                )

                cached_result = await self.qa_session_manager.get_cached_case_result(
                    cache_key=cache_key,
                    cache_ttl=request.cache_ttl,
                )

                if cached_result:
                    self.logger.info(f"Using cached result for case {case.id}")
                    # Update execution time to reflect cache hit
                    cached_result.execution_time = (datetime.utcnow() - start_time).total_seconds()
                    return cached_result

            self.logger.debug(f"No cached result found for case {case.id}, executing component")

            # Execute the component
            output = await self._execute_component(case, request, executor)

            # Validate schema if provided
            schema_result = None
            if request.expected_schema:
                schema_result = validate_schema(output, request.expected_schema)
                if not schema_result.is_valid:
                    result = CaseEvaluationResult(
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
                    return result

            # Analyze expectations using LLM
            if case.expectations:
                component_context = request.component_config or {}
                expectation_result = await self._analyze_expectations(case, output, llm_client, component_context)

                grade = "PASS" if not expectation_result.expectations_broken else "FAIL"

                result = CaseEvaluationResult(
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
                result = CaseEvaluationResult(
                    case_id=str(case.id),
                    input=case.input,
                    output=output,
                    grade="PASS" if (not schema_result or schema_result.is_valid) else "FAIL",
                    analysis=f"No expectations defined, {request.component_type} output generated successfully",
                    expectations_broken=[],
                    schema_valid=schema_result.is_valid if schema_result else True,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                )

            # Store result in cache if successful
            if request.use_cache and result.grade == "PASS" and self.qa_session_manager:
                cache_key = self.qa_session_manager.generate_case_cache_key(
                    case_input=str(case.input),
                    component_config=request.component_config,
                    evaluation_config_id=request.evaluation_config_id,
                    review_llm=request.review_llm,
                    expectations=case.expectations,
                )

                await self.qa_session_manager.store_cached_case_result(
                    cache_key=cache_key,
                    result=result,
                )

            return result

        except Exception as e:
            self.logger.error(f"Error evaluating {request.component_type} case {case.id}: {e}")
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

    async def _evaluate_multiple_components(
        self, request: EvaluationConfig, executor: Optional["AuriteEngine"] = None
    ) -> Dict[str, QAEvaluationResult]:
        """
        Evaluate multiple components in parallel.

        Args:
            request: The evaluation request containing test cases and component references
            executor: Optional AuriteEngine for component execution

        Returns:
            Dictionary mapping component names to QAEvaluationResult objects
        """
        if not request.component_refs:
            raise ValueError("No component references provided for multi-component evaluation")

        self.logger.info(f"QAEngine: Starting parallel evaluation of {len(request.component_refs)} components")

        # Create individual evaluation tasks for each component
        tasks = []
        component_type = request.component_type or "agent"

        for component_name in request.component_refs:
            # Create a single-component request for each component
            single_request = request.model_copy(deep=True)
            single_request.component_refs = [component_name]
            if not single_request.component_config and self.config_manager:
                # Load component config if not already provided
                single_request.component_config = self.config_manager.get_config(
                    component_type=component_type, component_id=component_name
                )
            if not single_request.component_config:
                self.logger.info(f"Component {component_name} not found for evaluation, skipping")
                continue

            # Create task for this component
            task = self._test_component(single_request, executor)
            tasks.append((component_name, task))

        # Execute all tasks in parallel
        self.logger.info(f"QAEngine: Executing {len(tasks)} component evaluations in parallel")
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        # Process results and handle exceptions
        final_results = {}
        for (component_name, _), result in zip(tasks, results, strict=False):
            if isinstance(result, Exception):
                self.logger.error(f"QAEngine: Component {component_name} evaluation failed: {result}")
                # Create a failed result for this component
                failed_result = QAEvaluationResult(
                    evaluation_id=f"failed_{uuid.uuid4().hex[:8]}",
                    status="failed",
                    component_type=component_type,
                    component_name=component_name,
                    overall_score=0.0,
                    total_cases=len(request.test_cases),
                    passed_cases=0,
                    failed_cases=len(request.test_cases),
                    case_results={},
                    recommendations=[f"Component evaluation failed: {str(result)}"],
                    metadata={"error": str(result)},
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    duration_seconds=0.0,
                )
                final_results[component_name] = failed_result
            else:
                final_results[component_name] = result

        self.logger.info(f"QAEngine: Completed parallel evaluation of {len(final_results)} components")
        return final_results

    # ============================================================================
    # Business Logic Methods
    # ============================================================================

    async def _execute_component(
        self,
        case: EvaluationCase,
        request: EvaluationConfig,
        executor: Optional["AuriteEngine"] = None,
    ) -> Any:
        """
        Execute a component and get its output.

        Supports multiple execution patterns:
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
            self.logger.debug(f"Using pre-recorded output for case {case.id}")
            return case.output

        # Check for custom execution function (legacy run_agent support)
        run_agent = getattr(request, "run_agent", None)
        if run_agent:
            self.logger.debug(f"Using custom execution function for case {case.id}")
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

        if request.component_config:
            component_name = request.component_config.get("name")

        if not component_name and hasattr(request, "component_refs") and request.component_refs:
            component_name = request.component_refs[0]

        if not component_name:
            raise ValueError(f"Case {case.id}: No component name specified for execution")

        component_type = request.component_type
        self.logger.debug(f"Executing {component_type} '{component_name}' for case {case.id}")

        # Execute based on component type
        if component_type == "agent":
            result = await executor.run_agent(
                agent_name=component_name,
                user_message=case.input,
            )
            return format_agent_conversation_history(result)

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

        elif component_type == "graph_workflow":
            return await executor.run_graph_workflow(
                workflow_name=component_name,
                initial_input=case.input,
            )

        elif component_type == "mcp_server":
            # Check if we already have a test agent for this MCP server
            if self._mcp_test_agents and component_name in self._mcp_test_agents:
                agent_name = self._mcp_test_agents[component_name]
                self.logger.debug(f"Reusing existing test agent '{agent_name}' for MCP server '{component_name}'")
            else:
                # Create a new test agent for this MCP server
                agent_name = f"qa_test_agent_{component_name}_{uuid.uuid4().hex[:8]}"
                agent_config = {
                    "name": agent_name,
                    "type": "agent",
                    "mcp_servers": [component_name],
                    "llm_config_id": request.review_llm,
                    "system_prompt": f"""You are an expert test engineer who has been tasked with testing an MCP server named {component_name}. You have access to the tools defined by that server.
The user will give you a message which should inform which tool to call. If arguments for the tool are given, use those, and if not generate appropriate arguments yourself.
Finally, respond with the information returned by the tool.""",
                }
                executor._config_manager.create_component(component_type="agent", component_config=agent_config)
                self.logger.info(f"Created test agent '{agent_name}' for MCP server '{component_name}'")

                # Store in cache
                self._mcp_test_agents[component_name] = agent_name

            result = await executor.run_agent(
                agent_name=agent_name,
                user_message=case.input,
            )

            return format_agent_conversation_history(result)

        else:
            raise ValueError(f"Unsupported component type for execution: {component_type}")

    async def _analyze_expectations(
        self,
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
        system_prompt = self._build_analysis_system_prompt(component_context)

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
            self.logger.error(f"Error parsing LLM analysis output: {e}")
            # Return a failed analysis
            return ExpectationAnalysisResult(
                analysis=f"Failed to parse LLM output: {str(e)}",
                expectations_broken=case.expectations,  # Assume all failed if we can't parse
            )

    # ============================================================================
    # Helper Methods
    # ============================================================================

    async def _get_llm_client(
        self, request: EvaluationConfig, executor: Optional["AuriteEngine"] = None
    ) -> LiteLLMClient:
        """
        Get or create an LLM client for evaluation.

        Args:
            request: The test request
            executor: Optional AuriteEngine with config manager

        Returns:
            LiteLLMClient for evaluation
        """
        config_manager = executor._config_manager if executor and hasattr(executor, "_config_manager") else None

        if request.review_llm and config_manager:
            # Use the specified LLM configuration
            llm_config = config_manager.get_config(component_type="llm", component_id=request.review_llm)

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

    async def _pre_register_mcp_servers(self, request: EvaluationConfig, executor: Optional["AuriteEngine"] = None):
        """
        Pre-register MCP servers for agent evaluations to avoid race conditions.

        This method extracts MCP server configurations from the agent config
        and registers them once before parallel test execution begins.

        Args:
            request: The evaluation request containing component configuration
            executor: Optional AuriteEngine with MCP host for server registration
        """
        # Only proceed if we have an executor with MCP host
        if not executor or not hasattr(executor, "_host"):
            return

        # Proceed for agent evaluations with MCP servers OR MCP server evaluations
        if request.component_type == "agent":
            if not request.component_config:
                return

            # Extract MCP server names from agent configuration
            mcp_servers = request.component_config.get("mcp_servers", [])
        elif request.component_type == "mcp_server":
            # For MCP server evaluations, register the MCP server being tested
            if request.component_config:
                server_name = request.component_config.get("name")
                mcp_servers = [server_name] if server_name else []
            else:
                # Fall back to component_refs
                mcp_servers = request.component_refs if request.component_refs else []
        else:
            return

        if not mcp_servers:
            return

        self.logger.info(f"Pre-registering {len(mcp_servers)} MCP servers for evaluation")

        # Get the config manager to load MCP server configs
        config_manager = executor._config_manager if hasattr(executor, "_config_manager") else None
        if not config_manager:
            self.logger.warning("No config manager available to load MCP server configurations")
            return

        # Track servers that failed registration
        failed_servers = []

        # Register each MCP server
        for server_name in mcp_servers:
            try:
                # Check if already registered
                if server_name in executor._host.registered_server_names:
                    self.logger.debug(f"MCP server '{server_name}' already registered")
                    continue

                # Load server configuration
                server_config = config_manager.get_config("mcp_server", server_name)
                if not server_config:
                    self.logger.warning(f"MCP server configuration not found for '{server_name}'")
                    failed_servers.append(server_name)
                    continue

                # Import ClientConfig for creating the config object
                from aurite.lib.models.config.components import ClientConfig

                # Create ClientConfig from the loaded configuration
                client_config = ClientConfig(**server_config)

                # Register the server
                self.logger.info(f"Pre-registering MCP server: {server_name}")
                await executor._host.register_client(client_config)
                self.logger.info(f"Successfully pre-registered MCP server: {server_name}")

            except Exception as e:
                self.logger.error(f"Failed to pre-register MCP server '{server_name}': {e}")
                failed_servers.append(server_name)
                continue

        # Store failed servers
        if failed_servers:
            self._failed_mcp_servers.extend(failed_servers)
            self.logger.warning(f"Failed to register {len(failed_servers)} MCP servers: {failed_servers}")

    def _filter_test_cases(self, test_cases: list, filter_str: str) -> list:
        """
        Filter test cases based on the provided filter string.

        Supports:
        - Comma-separated names: "test1,test2"
        - Index ranges: "0-2" (indices 0, 1, 2)
        - Single indices: "0,2,4"
        - Mixed: "test1,0-2,test5"
        - Regex patterns: "/pattern/" or "regex:pattern"

        Args:
            test_cases: List of test case dictionaries
            filter_str: Filter string

        Returns:
            Filtered list of test cases
        """
        import re

        filtered = []
        filters = [f.strip() for f in filter_str.split(",")]

        for filter_item in filters:
            # Check for regex pattern
            if filter_item.startswith("/") and filter_item.endswith("/"):
                # Regex pattern
                pattern = filter_item[1:-1]
                try:
                    regex = re.compile(pattern, re.IGNORECASE)
                    for case in test_cases:
                        name = case.get("name", "")
                        if regex.search(name) and case not in filtered:
                            filtered.append(case)
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern '{pattern}': {e}")

            elif filter_item.startswith("regex:"):
                # Alternative regex syntax
                pattern = filter_item[6:]
                try:
                    regex = re.compile(pattern, re.IGNORECASE)
                    for case in test_cases:
                        name = case.get("name", "")
                        if regex.search(name) and case not in filtered:
                            filtered.append(case)
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern '{pattern}': {e}")

            elif "-" in filter_item and filter_item.replace("-", "").isdigit():
                # Index range (e.g., "0-2")
                parts = filter_item.split("-")
                if len(parts) == 2:
                    try:
                        start = int(parts[0])
                        end = int(parts[1])
                        for i in range(start, min(end + 1, len(test_cases))):
                            if test_cases[i] not in filtered:
                                filtered.append(test_cases[i])
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Invalid index range '{filter_item}': {e}")

            elif filter_item.isdigit():
                # Single index
                try:
                    idx = int(filter_item)
                    if 0 <= idx < len(test_cases) and test_cases[idx] not in filtered:
                        filtered.append(test_cases[idx])
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Invalid index '{filter_item}': {e}")

            else:
                # Test case name
                for case in test_cases:
                    if case.get("name", "") == filter_item and case not in filtered:
                        filtered.append(case)

        # Preserve original order
        return [case for case in test_cases if case in filtered]

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

    def _build_analysis_system_prompt(self, component_context: Optional[Dict[str, Any]] = None) -> str:
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
