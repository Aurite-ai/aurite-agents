"""
Unified Component QA Tester for the Aurite Testing Framework.

This module provides a single, unified QA tester that handles all component types
(agents, workflows, etc.) using component-aware context and recommendations.
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from aurite.lib.models.api.requests import EvaluationRequest

from .qa_models import (
    CaseEvaluationResult,
    ComponentQAConfig,
    QAEvaluationResult,
)
from .qa_utils import (
    analyze_expectations,
    execute_component,
    generate_cache_key,
    generate_evaluation_cache_key,
    get_cached_case_result,
    get_cached_evaluation_result,
    get_llm_client,
    store_cached_case_result,
    store_cached_evaluation_result,
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
            default_timeout=90.0,  # Reasonable default for most components
            parallel_execution=True,  # Most components can run in parallel
            max_retries=1,
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        # Track failed MCP servers to prevent parallel retry attempts
        self._failed_mcp_servers: List[str] = []
        # Cache for MCP server test agents to reuse across test cases
        self._mcp_test_agents: Dict[str, str] = {}

        # Rate limiting configuration
        self._max_concurrent_tests = getattr(config, "max_concurrent_tests", 3)  # Default to 3 concurrent tests
        self._rate_limit_retry_count = getattr(config, "rate_limit_retry_count", 3)  # Max retries for rate limits
        self._rate_limit_base_delay = getattr(config, "rate_limit_base_delay", 1.0)  # Base delay in seconds
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def test_component(
        self, request: EvaluationRequest, executor: Optional["AuriteEngine"] = None
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

        # Check for cached evaluation result first (if caching is enabled and not forced refresh)
        if request.use_cache and not request.force_refresh and request.evaluation_config_id:
            evaluation_cache_key = generate_evaluation_cache_key(
                evaluation_config_id=request.evaluation_config_id,
                test_cases=request.test_cases,
                review_llm=request.review_llm,
            )

            session_manager = None
            if executor and hasattr(executor, "_session_manager"):
                session_manager = executor._session_manager

            cached_evaluation = await get_cached_evaluation_result(
                cache_key=evaluation_cache_key,
                session_manager=session_manager,
                cache_ttl=request.cache_ttl,
            )

            if cached_evaluation:
                self.logger.info(f"Using cached evaluation result for {evaluation_id}")
                # Update timing to reflect cache hit
                cached_evaluation.started_at = started_at
                cached_evaluation.completed_at = datetime.utcnow()
                cached_evaluation.duration_seconds = (cached_evaluation.completed_at - started_at).total_seconds()
                return cached_evaluation

        # No cached evaluation found or caching disabled - proceed with execution
        self.logger.debug("No cached evaluation found, executing component tests")

        # Pre-register MCP servers if this is an agent or MCP server evaluation
        await self._pre_register_mcp_servers(request, executor)

        # Get LLM client for evaluation
        llm_client = await self._get_llm_client(request, executor)

        # Initialize semaphore for rate limiting (if not already initialized)
        if self._semaphore is None:
            # Check if request has max_concurrent_tests parameter
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

        # Store evaluation result in cache if caching is enabled
        if request.use_cache and request.evaluation_config_id:
            evaluation_cache_key = generate_evaluation_cache_key(
                evaluation_config_id=request.evaluation_config_id,
                test_cases=request.test_cases,
                review_llm=request.review_llm,
            )

            session_manager = None
            if executor and hasattr(executor, "_session_manager"):
                session_manager = executor._session_manager

            await store_cached_evaluation_result(
                cache_key=evaluation_cache_key,
                result=evaluation_result,
                session_manager=session_manager,
            )

        return evaluation_result

    async def _evaluate_single_case_with_semaphore(
        self,
        case,
        llm_client,
        request: EvaluationRequest,
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
        # Ensure semaphore exists (shouldn't happen but defensive programming)
        if self._semaphore is None:
            max_concurrent = getattr(request, "max_concurrent_tests", self._max_concurrent_tests)
            self._semaphore = asyncio.Semaphore(max_concurrent)

        async with self._semaphore:
            # Add retry logic for rate limit errors
            last_exception = None
            for retry_attempt in range(self._rate_limit_retry_count):
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
                        if retry_attempt < self._rate_limit_retry_count - 1:
                            # Calculate exponential backoff with jitter
                            delay = self._rate_limit_base_delay * (2**retry_attempt)
                            jitter = random.uniform(0, delay * 0.3)  # Add up to 30% jitter
                            total_delay = delay + jitter

                            self.logger.warning(
                                f"Rate limit hit for test case {case.id}, "
                                f"retrying in {total_delay:.2f} seconds "
                                f"(attempt {retry_attempt + 1}/{self._rate_limit_retry_count})"
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
                # This should never happen but provide a fallback
                raise RuntimeError(
                    f"Failed to evaluate test case {case.id} after {self._rate_limit_retry_count} attempts"
                )

    async def _evaluate_single_case(
        self,
        case,
        llm_client,
        request: EvaluationRequest,
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
            # Check for cached result first (if caching is enabled and not forced refresh)
            cached_result = None
            if request.use_cache and not request.force_refresh:
                # Generate cache key for this test case
                cache_key = generate_cache_key(
                    case_input=str(case.input),
                    component_config=request.component_config,
                    evaluation_config_id=request.evaluation_config_id,
                    review_llm=request.review_llm,
                    expectations=case.expectations,
                )

                # Try to get cached result
                session_manager = None
                if executor and hasattr(executor, "_session_manager"):
                    session_manager = executor._session_manager

                cached_result = await get_cached_case_result(
                    cache_key=cache_key,
                    session_manager=session_manager,
                    cache_ttl=request.cache_ttl,
                )

                if cached_result:
                    self.logger.info(f"Using cached result for case {case.id}")
                    # Update execution time to reflect cache hit (very fast)
                    cached_result.execution_time = (datetime.utcnow() - start_time).total_seconds()
                    return cached_result

            # No cached result found or caching disabled - proceed with execution
            self.logger.debug(f"No cached result found for case {case.id}, executing component")

            # Get the output using the utility function (supports custom execution)
            # Pass the MCP test agents cache for MCP server evaluations
            output = await execute_component(case, request, executor, self._mcp_test_agents)

            # Validate schema if provided using utility function
            schema_result = None
            if request.expected_schema:
                schema_result = validate_schema(output, request.expected_schema)
                if not schema_result.is_valid:
                    # Schema validation failed
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
                    # Don't cache failed schema validation results
                    return result

            # Analyze expectations using utility function with component context
            if case.expectations:
                component_context = request.component_config or {}
                expectation_result = await analyze_expectations(case, output, llm_client, component_context)

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

            # Store result in cache if caching is enabled and result is successful
            if request.use_cache and result.grade == "PASS":
                cache_key = generate_cache_key(
                    case_input=str(case.input),
                    component_config=request.component_config,
                    evaluation_config_id=request.evaluation_config_id,
                    review_llm=request.review_llm,
                    expectations=case.expectations,
                )

                session_manager = None
                if executor and hasattr(executor, "_session_manager"):
                    session_manager = executor._session_manager

                await store_cached_case_result(
                    cache_key=cache_key,
                    result=result,
                    session_manager=session_manager,
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

    async def _get_llm_client(self, request: EvaluationRequest, executor: Optional["AuriteEngine"] = None):
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

    async def _pre_register_mcp_servers(self, request: EvaluationRequest, executor: Optional["AuriteEngine"] = None):
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

        self.logger.info(f"Pre-registering {len(mcp_servers)} MCP servers for agent evaluation")

        # Get the config manager to load MCP server configs
        config_manager = executor._config_manager if hasattr(executor, "_config_manager") else None
        if not config_manager:
            self.logger.warning("No config manager available to load MCP server configurations")
            return

        # Track servers that failed registration to prevent retry attempts
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
                # Track this server as failed to prevent parallel registration attempts
                failed_servers.append(server_name)
                continue

        # Store failed servers to prevent retry attempts during parallel execution
        if failed_servers:
            self._failed_mcp_servers.extend(failed_servers)
            self.logger.warning(f"Failed to register {len(failed_servers)} MCP servers: {failed_servers}")
            self.logger.warning("These servers will be skipped during test execution to prevent race conditions")

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
