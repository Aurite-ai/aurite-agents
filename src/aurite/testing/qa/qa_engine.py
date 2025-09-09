"""
QA Engine for the Aurite Testing Framework.

This module provides the Level 2 orchestrator for Quality Assurance testing.
It manages QA testing across all component types, delegating to the unified
ComponentQATester for actual test execution.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Dict, Optional

from aurite.lib.config.config_manager import ConfigManager
from aurite.lib.models.api.requests import EvaluationRequest

from .component_qa_tester import ComponentQATester
from .qa_models import QAEvaluationResult

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)


class QAEngine:
    """
    Level 2 Orchestrator for Quality Assurance testing.

    This class manages QA testing across all component types, delegating
    to the unified ComponentQATester for actual test execution.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the QA Engine.

        Args:
            config_manager: Optional ConfigManager for accessing configurations
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        # Use a single unified tester for all component types
        self._component_tester = ComponentQATester()

    async def evaluate_component(
        self, request: EvaluationRequest, executor: Optional["AuriteEngine"] = None
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

        # Determine component type
        component_type = request.component_type or "agent"  # Default to agent if not specified
        self.logger.info(f"QAEngine: Resolved component type: {component_type}")

        # Check if this is a manual output evaluation (all test cases have outputs)
        has_manual_outputs = all(case.output is not None for case in request.test_cases)
        self.logger.info(f"QAEngine: Manual outputs detected: {has_manual_outputs}")

        # Check if this is a function-based evaluation (run_agent is provided)
        has_run_function = request.run_agent is not None
        self.logger.info(f"QAEngine: Run function detected: {has_run_function}")

        # Handle multiple components if specified
        if request.component_refs and len(request.component_refs) > 1:
            return await self._evaluate_multiple_components(request, executor)

        # Handle single component (either from component_refs[0] or component_config)
        component_name = None
        component_config = {}

        if has_manual_outputs and not request.component_refs:
            # Manual output evaluation - no component needed
            component_name = "manual_output_evaluation"
            component_config = {"name": component_name, "type": component_type}
            self.logger.info("QAEngine: Using manual output evaluation mode - no component loading needed")
        elif has_run_function and not request.component_refs:
            # Function-based evaluation - no component needed
            component_name = "function_evaluation"
            component_config = {"name": component_name, "type": component_type}
            self.logger.info("QAEngine: Using function evaluation mode - no component loading needed")
        else:
            # Regular component evaluation
            if request.component_refs and len(request.component_refs) >= 1:
                component_name = request.component_refs[0]

            # Get component config - prefer provided config over loading from ConfigManager
            if hasattr(request, "component_config") and request.component_config:
                # Use the provided component configuration
                component_config = request.component_config
                component_name = component_config.get("name", component_name or "unknown")
                self.logger.info(f"QAEngine: Using provided component config for {component_name}")
            elif self.config_manager and component_name:
                # Try to load from ConfigManager as fallback
                try:
                    self.logger.info(f"QAEngine: Loading component config for {component_type}.{component_name}")
                    config = self.config_manager.get_config(component_type=component_type, component_id=component_name)
                    if config:
                        component_config = config
                        self.logger.info("QAEngine: Successfully loaded component config")
                    else:
                        self.logger.warning(f"QAEngine: No config found for {component_type}.{component_name}")
                except Exception as e:
                    self.logger.warning(f"QAEngine: Could not load component config: {e}")

        self.logger.info("QAEngine: Delegating to unified ComponentQATester")
        # Delegate to the unified component tester
        result = await self._component_tester.test_component(request, executor)

        self.logger.info(f"QAEngine: Component tester completed with status: {result.status}")
        self.logger.info(f"QAEngine: Overall score: {result.overall_score:.2f}%")
        self.logger.info(
            f"QAEngine: Passed/Failed/Total: {result.passed_cases}/{result.failed_cases}/{result.total_cases}"
        )

        # Save result to storage if we have a session manager
        if executor and hasattr(executor, "_session_manager") and executor._session_manager:
            try:
                # For single component results, save the result
                # Use component_name as evaluation_config_id if available, otherwise "unknown"
                config_id = component_name or "unknown"
                result_id = executor._session_manager.save_qa_test_result(result.model_dump(), config_id)
                if result_id:
                    self.logger.info(f"QAEngine: Saved test result with ID: {result_id}")
                else:
                    self.logger.warning("QAEngine: Failed to save test result")
            except Exception as e:
                self.logger.error(f"QAEngine: Error saving test result: {e}")

        # Return single result in dictionary format for consistency
        return {component_name or "component": result}

    async def _evaluate_multiple_components(
        self, request: EvaluationRequest, executor: Optional["AuriteEngine"] = None
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
            single_request.component_config = self.config_manager.get_config(
                component_type=component_type, component_id=component_name
            )
            if not single_request.component_config:
                self.logger.info(f"Component {component_name} not found for evaluation, skipping")
                continue

            # Create task for this component
            task = self._component_tester.test_component(single_request, executor)
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
                import uuid
                from datetime import datetime

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

    async def evaluate_by_config_id(
        self, evaluation_config_id: str, executor: Optional["AuriteEngine"] = None
    ) -> Dict[str, QAEvaluationResult]:
        """
        Evaluate components using a saved evaluation configuration.

        This method loads an evaluation configuration from the ConfigManager
        and executes the evaluation based on the saved test cases and settings.
        Supports both single and multiple component evaluations.

        Args:
            evaluation_config_id: ID of the evaluation configuration to load
            executor: Optional AuriteEngine for component execution

        Returns:
            Dictionary mapping component names to QAEvaluationResult objects
        """
        if not self.config_manager:
            raise ValueError("ConfigManager is required to load evaluation configurations")

        # Load the evaluation configuration
        eval_config = self.config_manager.get_config("evaluation", evaluation_config_id)
        if not eval_config:
            raise ValueError(f"Evaluation configuration '{evaluation_config_id}' not found")

        shared_fields = set(EvaluationRequest.model_fields.keys())
        request_data = {field: eval_config[field] for field in shared_fields if field in eval_config}
        request = EvaluationRequest(**request_data)

        # Execute the evaluation
        return await self.evaluate_component(request, executor)
