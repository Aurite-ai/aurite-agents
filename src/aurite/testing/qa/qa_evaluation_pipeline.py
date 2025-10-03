"""
Evaluation pipeline for QA testing.

This module manages the evaluation flow for individual test cases:
1. Check cache for existing results
2. Execute the component (via mode handlers)
3. Validate schema if provided
4. Analyze expectations using LLM
5. Store successful results in cache
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.models.config.components import EvaluationCase, EvaluationConfig

from .qa_mode_handlers import BaseModeHandler
from .qa_models import CaseEvaluationResult
from .qa_session_manager import QASessionManager
from .qa_utils import validate_schema

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)


class EvaluationPipeline:
    """
    Manages the evaluation flow for individual test cases.

    This class orchestrates the evaluation process:
    - Cache checking and storage
    - Component execution via mode handlers
    - Schema validation
    - LLM-based expectation analysis
    """

    def __init__(
        self,
        session_manager: Optional[QASessionManager] = None,
    ):
        """
        Initialize the evaluation pipeline.

        Args:
            session_manager: Optional QASessionManager for caching
        """
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)

    async def evaluate_case(
        self,
        case: EvaluationCase,
        request: EvaluationConfig,
        mode_handler: BaseModeHandler,
        llm_client: LiteLLMClient,
        executor: Optional["AuriteEngine"] = None,
    ) -> CaseEvaluationResult:
        """
        Evaluate a single test case through the complete pipeline.

        Args:
            case: The test case to evaluate
            request: The evaluation configuration
            mode_handler: Mode handler for component execution
            llm_client: LLM client for expectation analysis
            executor: Optional AuriteEngine for component execution

        Returns:
            CaseEvaluationResult for this test case
        """
        start_time = datetime.utcnow()

        try:
            # Step 1: Check cache
            cached_result = await self._check_cache(case, request)
            if cached_result:
                self.logger.info(f"Using cached result for case {case.id}")
                cached_result.execution_time = (datetime.utcnow() - start_time).total_seconds()
                return cached_result

            self.logger.debug(f"No cached result found for case {case.id}, executing component")

            # Step 2: Execute component
            output = await mode_handler.get_output(case, request, executor)

            # Step 3: Validate schema
            schema_result = await self._validate_schema(output, request)
            if schema_result and not schema_result.is_valid:
                return self._create_schema_failure_result(case, output, schema_result, start_time)

            # Step 4: Analyze expectations
            if case.expectations:
                result = await self._analyze_and_grade(case, output, llm_client, request, schema_result, start_time)
            else:
                result = self._create_no_expectation_result(case, output, request, schema_result, start_time)

            # Step 5: Store in cache if successful
            if request.use_cache and result.grade == "PASS" and self.session_manager:
                await self._store_in_cache(case, request, result)

            return result

        except Exception as e:
            self.logger.error(f"Error evaluating {request.component_type} case {case.id}: {e}")
            return self._create_error_result(case, request, e, start_time)

    async def _check_cache(self, case: EvaluationCase, request: EvaluationConfig) -> Optional[CaseEvaluationResult]:
        """
        Check for cached result.

        Args:
            case: The test case
            request: The evaluation configuration

        Returns:
            Cached result if found, None otherwise
        """
        if not request.use_cache or request.force_refresh or not self.session_manager:
            return None

        cache_key = self.session_manager.generate_case_cache_key(
            case_input=str(case.input),
            component_config=request.component_config,
            evaluation_config_id=request.evaluation_config_id,
            review_llm=request.review_llm,
            expectations=case.expectations,
        )

        return await self.session_manager.get_cached_case_result(
            cache_key=cache_key,
            cache_ttl=request.cache_ttl,
        )

    async def _validate_schema(self, output: Any, request: EvaluationConfig) -> Optional[Any]:
        """
        Validate output against schema if provided.

        Args:
            output: The output to validate
            request: The evaluation configuration

        Returns:
            Schema validation result if schema provided, None otherwise
        """
        if not request.expected_schema:
            return None

        return validate_schema(output, request.expected_schema)

    async def _analyze_and_grade(
        self,
        case: EvaluationCase,
        output: Any,
        llm_client: LiteLLMClient,
        request: EvaluationConfig,
        schema_result: Optional[Any],
        start_time: datetime,
    ) -> CaseEvaluationResult:
        """
        Analyze expectations using LLM and create graded result.

        Args:
            case: The test case
            output: The component output
            llm_client: LLM client for analysis
            request: The evaluation configuration
            schema_result: Schema validation result
            start_time: Start time of evaluation

        Returns:
            CaseEvaluationResult with analysis and grade
        """
        from .qa_expectation_analyzer import analyze_expectations

        component_context = request.component_config or {}
        expectation_result = await analyze_expectations(
            case=case,
            output=output,
            llm_client=llm_client,
            component_context=component_context,
        )

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

    def _create_schema_failure_result(
        self,
        case: EvaluationCase,
        output: Any,
        schema_result: Any,
        start_time: datetime,
    ) -> CaseEvaluationResult:
        """
        Create a result for schema validation failure.

        Args:
            case: The test case
            output: The component output
            schema_result: Schema validation result
            start_time: Start time of evaluation

        Returns:
            CaseEvaluationResult for schema failure
        """
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

    def _create_no_expectation_result(
        self,
        case: EvaluationCase,
        output: Any,
        request: EvaluationConfig,
        schema_result: Optional[Any],
        start_time: datetime,
    ) -> CaseEvaluationResult:
        """
        Create a result when no expectations are defined.

        Args:
            case: The test case
            output: The component output
            request: The evaluation configuration
            schema_result: Schema validation result
            start_time: Start time of evaluation

        Returns:
            CaseEvaluationResult for no expectations case
        """
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

    def _create_error_result(
        self,
        case: EvaluationCase,
        request: EvaluationConfig,
        error: Exception,
        start_time: datetime,
    ) -> CaseEvaluationResult:
        """
        Create a result for evaluation errors.

        Args:
            case: The test case
            request: The evaluation configuration
            error: The exception that occurred
            start_time: Start time of evaluation

        Returns:
            CaseEvaluationResult for error case
        """
        return CaseEvaluationResult(
            case_id=str(case.id),
            input=case.input,
            output=None,
            grade="FAIL",
            analysis=f"Evaluation failed: {str(error)}",
            expectations_broken=case.expectations,
            error=str(error),
            execution_time=(datetime.utcnow() - start_time).total_seconds(),
        )

    async def _store_in_cache(
        self,
        case: EvaluationCase,
        request: EvaluationConfig,
        result: CaseEvaluationResult,
    ) -> None:
        """
        Store successful result in cache.

        Args:
            case: The test case
            request: The evaluation configuration
            result: The result to cache
        """
        if not self.session_manager:
            return

        cache_key = self.session_manager.generate_case_cache_key(
            case_input=str(case.input),
            component_config=request.component_config,
            evaluation_config_id=request.evaluation_config_id,
            review_llm=request.review_llm,
            expectations=case.expectations,
        )

        await self.session_manager.store_cached_case_result(
            cache_key=cache_key,
            result=result,
        )
