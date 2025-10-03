"""
Unified QA Engine for the Aurite Testing Framework.

This module provides the complete orchestration and execution of Quality Assurance
testing for all component types. It handles evaluation request processing, component
execution, result caching, and LLM-based expectation analysis.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.config.config_manager import ConfigManager
from aurite.lib.models.config.components import EvaluationCase, EvaluationConfig, LLMConfig

from .qa_evaluation_pipeline import EvaluationPipeline
from .qa_mode_handlers import get_mode_handler
from .qa_models import CaseEvaluationResult, QAEvaluationResult
from .qa_rate_limiter import RateLimiter
from .qa_session_manager import QASessionManager
from .qa_utils import filter_test_cases

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

        # Initialize evaluation pipeline
        self.evaluation_pipeline = EvaluationPipeline(session_manager=session_manager)

        # Track failed MCP servers to prevent parallel retry attempts
        self._failed_mcp_servers: List[str] = []
        # Cache for MCP server test agents to reuse across test cases
        self._mcp_test_agents: Dict[str, str] = {}

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
            request: The evaluation request (see EvaluationConfig) containing test cases
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

        # default to agent testing if not specified
        if not request.component_type:
            request.component_type = "agent"
            self.logger.warning("QAEngine: No component type specified, defaulting to 'agent'")
        else:
            self.logger.info(f"QAEngine: Resolved component type: {request.component_type}")

        # Handle multiple components if specified
        if request.component_refs and len(request.component_refs) > 1:
            return await self._evaluate_multiple_components(request, executor)

        # Prepare configuration using mode handler
        mode_handler = get_mode_handler(
            mode=mode,
            config_manager=self.config_manager,
            mcp_test_agents=self._mcp_test_agents,
        )
        component_name = await mode_handler.prepare_config(request, executor)

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
            # For storage, use component_name for Aurite mode, evaluation_config_id for others
            config_id = component_name if component_name else (request.evaluation_config_id or f"{mode}_evaluation")
            self.qa_session_manager.save_test_result(result.model_dump(), config_id)

        # Return single result in dictionary format for consistency
        result_key = component_name if component_name else f"{mode}_evaluation"
        return {result_key: result}

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
            filtered_cases = filter_test_cases(request_data["test_cases"], test_cases_filter)
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

        # Initialize rate limiter with request configuration
        max_concurrent = getattr(request, "max_concurrent_tests", 3)
        retry_count = getattr(request, "rate_limit_retry_count", 3)
        base_delay = getattr(request, "rate_limit_base_delay", 1.0)

        rate_limiter = RateLimiter(
            max_concurrent=max_concurrent,
            retry_count=retry_count,
            base_delay=base_delay,
        )

        # Create tasks with rate-limited execution
        tasks = [
            self._evaluate_case_with_rate_limiting(
                case=case, llm_client=llm_client, request=request, executor=executor, rate_limiter=rate_limiter
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

    async def _evaluate_case_with_rate_limiting(
        self,
        case: EvaluationCase,
        llm_client: LiteLLMClient,
        request: EvaluationConfig,
        rate_limiter: RateLimiter,
        executor: Optional["AuriteEngine"] = None,
    ) -> CaseEvaluationResult:
        """
        Wrapper that executes case evaluation with rate limiting and retry logic.

        Args:
            case: The test case to evaluate
            llm_client: LLM client for expectation analysis
            request: The overall test request
            rate_limiter: RateLimiter instance for concurrency control
            executor: Optional AuriteEngine for component execution

        Returns:
            CaseEvaluationResult for this test case
        """

        async def evaluate_operation():
            return await self._evaluate_single_case(case, llm_client, request, executor)

        return await rate_limiter.execute_with_retry(
            operation=evaluate_operation,
            operation_id=f"test case {case.id}",
        )

    async def _evaluate_single_case(
        self,
        case: EvaluationCase,
        llm_client: LiteLLMClient,
        request: EvaluationConfig,
        executor: Optional["AuriteEngine"] = None,
    ) -> CaseEvaluationResult:
        """
        Evaluate a single test case for any component type.

        This method delegates to the evaluation pipeline which handles:
        - Cache checking and storage
        - Component execution via mode handlers
        - Schema validation
        - LLM-based expectation analysis

        Args:
            case: The test case to evaluate
            llm_client: LLM client for expectation analysis
            request: The overall test request
            executor: Optional AuriteEngine for component execution

        Returns:
            CaseEvaluationResult for this test case
        """
        # Get the appropriate mode handler
        mode = request.resolve_mode()
        mode_handler = get_mode_handler(
            mode=mode,
            config_manager=self.config_manager,
            mcp_test_agents=self._mcp_test_agents,
        )

        # Delegate to evaluation pipeline
        return await self.evaluation_pipeline.evaluate_case(
            case=case,
            request=request,
            mode_handler=mode_handler,
            llm_client=llm_client,
            executor=executor,
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
