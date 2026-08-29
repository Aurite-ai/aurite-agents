"""
QA Session Manager for the Aurite Testing Framework.

This module provides session and cache management for Quality Assurance testing,
handling result storage, cache operations, and cache key generation.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .qa_models import CaseEvaluationResult, QAEvaluationResult

logger = logging.getLogger(__name__)


class QASessionManager:
    """
    Manages session state and caching for QA evaluation results.

    This class handles:
    - Cache key generation for cases and evaluations
    - Storing and retrieving cached results
    - Persisting evaluation results to storage
    """

    def __init__(self, session_manager=None):
        """
        Initialize the QA Session Manager.

        Args:
            session_manager: Optional SessionManager instance for storage operations
        """
        self.session_manager = session_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    # Cache Key Generation

    def generate_case_cache_key(
        self,
        case_input: str,
        component_config: Optional[Dict[str, Any]],
        evaluation_config_id: Optional[str] = None,
        review_llm: Optional[str] = None,
        expectations: Optional[List[str]] = None,
    ) -> str:
        """
        Generate a unique cache key for a test case evaluation.

        Args:
            case_input: The input string for the test case
            component_config: Configuration of the component being tested
            evaluation_config_id: Optional evaluation configuration ID
            review_llm: Optional review LLM configuration ID
            expectations: Optional list of expectations for the test case

        Returns:
            Unique cache key string
        """
        if not component_config:
            component_config = {}

        # Extract key configuration elements that affect the output
        key_data = {
            "input": case_input,
            "component_name": component_config.get("name"),
            "component_type": component_config.get("type"),
            "eval_config_id": evaluation_config_id,
            "review_llm": review_llm,
            "expectations": sorted(expectations) if expectations else None,
            # Include key config settings that affect output
            "temperature": component_config.get("temperature"),
            "model": component_config.get("model"),
            "provider": component_config.get("provider"),
            "system_prompt": component_config.get("system_prompt"),
            "tools": sorted(component_config.get("tools", [])),
            "max_tokens": component_config.get("max_tokens"),
            # For workflows
            "steps": component_config.get("steps"),
            "timeout_seconds": component_config.get("timeout_seconds"),
            "parallel_execution": component_config.get("parallel_execution"),
        }

        # Create hash of the key data
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        cache_key = f"qa_case_{hashlib.md5(key_str.encode()).hexdigest()}"

        self.logger.debug(f"Generated cache key: {cache_key} for input: {case_input[:50]}...")
        return cache_key

    def generate_evaluation_cache_key(
        self,
        evaluation_config_id: str,
        test_cases: List,
        review_llm: Optional[str] = None,
    ) -> str:
        """
        Generate a unique cache key for a complete evaluation.

        Args:
            evaluation_config_id: ID of the evaluation configuration
            test_cases: List of test cases (for generating consistent hash)
            review_llm: Optional review LLM configuration ID

        Returns:
            Unique cache key string for the evaluation
        """
        # Create a deterministic representation of test cases
        test_case_data = []
        for case in test_cases:
            case_data = {
                "input": str(case.input),
                "expectations": (
                    sorted(case.expectations) if hasattr(case, "expectations") and case.expectations else None
                ),
            }
            test_case_data.append(case_data)

        # Sort test cases by input to ensure consistent ordering
        test_case_data.sort(key=lambda x: x["input"])

        key_data = {
            "evaluation_config_id": evaluation_config_id,
            "review_llm": review_llm,
            "test_cases": test_case_data,
        }

        # Create hash of the key data
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        cache_key = f"qa_eval_{hashlib.md5(key_str.encode()).hexdigest()}"

        self.logger.debug(f"Generated evaluation cache key: {cache_key} for config: {evaluation_config_id}")
        return cache_key

    # Case-Level Cache Operations

    async def get_cached_case_result(
        self,
        cache_key: str,
        cache_ttl: int = 3600,
    ) -> Optional["CaseEvaluationResult"]:
        """
        Retrieve a cached case evaluation result if it exists and is not expired.

        Args:
            cache_key: The cache key to look up
            cache_ttl: Time-to-live in seconds for cached results

        Returns:
            CaseEvaluationResult if found and valid, None otherwise
        """
        if not self.session_manager:
            return None

        try:
            # Try to get cached result
            cached_data = self.session_manager.get_qa_case_result(cache_key)
            if not cached_data:
                return None

            # Check if cache is expired
            cached_at = datetime.fromisoformat(cached_data.get("cached_at", ""))
            if datetime.utcnow() - cached_at > timedelta(seconds=cache_ttl):
                self.logger.debug(f"Cache expired for key: {cache_key}")
                return None

            # Import here to avoid circular imports
            from .qa_models import CaseEvaluationResult

            # Return the cached result
            result_data = cached_data.get("result")
            if result_data:
                self.logger.debug(f"Cache hit for key: {cache_key}")
                return CaseEvaluationResult(**result_data)

        except Exception as e:
            self.logger.warning(f"Error retrieving cached result for key {cache_key}: {e}")

        return None

    async def store_cached_case_result(
        self,
        cache_key: str,
        result: "CaseEvaluationResult",
    ) -> bool:
        """
        Store a case evaluation result in the cache.

        Args:
            cache_key: The cache key to store under
            result: The CaseEvaluationResult to cache

        Returns:
            True if stored successfully, False otherwise
        """
        if not self.session_manager:
            return False

        try:
            cache_data = {
                "result": result.model_dump(),
                "cached_at": datetime.utcnow().isoformat(),
            }

            success = self.session_manager.save_qa_case_result(cache_key, cache_data)
            if success:
                self.logger.debug(f"Cached result for key: {cache_key}")
            return success

        except Exception as e:
            self.logger.warning(f"Error storing cached result for key {cache_key}: {e}")
            return False

    # Evaluation-Level Cache Operations

    async def get_cached_evaluation_result(
        self,
        cache_key: str,
        cache_ttl: int = 3600,
    ) -> Optional["QAEvaluationResult"]:
        """
        Retrieve a cached evaluation result if it exists and is not expired.

        Args:
            cache_key: The cache key to look up
            cache_ttl: Time-to-live in seconds for cached results

        Returns:
            QAEvaluationResult if found and valid, None otherwise
        """
        if not self.session_manager:
            return None

        try:
            # Try to get cached result
            cached_data = self.session_manager.get_qa_evaluation_result(cache_key)
            if not cached_data:
                return None

            # Check if cache is expired
            cached_at = datetime.fromisoformat(cached_data.get("cached_at", ""))
            if datetime.utcnow() - cached_at > timedelta(seconds=cache_ttl):
                self.logger.debug(f"Evaluation cache expired for key: {cache_key}")
                return None

            # Import here to avoid circular imports
            from .qa_models import QAEvaluationResult

            # Return the cached result
            result_data = cached_data.get("result")
            if result_data:
                self.logger.debug(f"Evaluation cache hit for key: {cache_key}")
                return QAEvaluationResult(**result_data)

        except Exception as e:
            self.logger.warning(f"Error retrieving cached evaluation result for key {cache_key}: {e}")

        return None

    async def store_cached_evaluation_result(
        self,
        cache_key: str,
        result: "QAEvaluationResult",
    ) -> bool:
        """
        Store a complete evaluation result in the cache.

        Args:
            cache_key: The cache key to store under
            result: The QAEvaluationResult to cache

        Returns:
            True if stored successfully, False otherwise
        """
        if not self.session_manager:
            return False

        try:
            cache_data = {
                "result": result.model_dump(),
                "cached_at": datetime.utcnow().isoformat(),
            }

            success = self.session_manager.save_qa_evaluation_result(cache_key, cache_data)
            if success:
                self.logger.debug(f"Cached evaluation result for key: {cache_key}")
            return success

        except Exception as e:
            self.logger.warning(f"Error storing cached evaluation result for key {cache_key}: {e}")
            return False

    # Result Persistence

    def save_test_result(self, result_data: Dict[str, Any], config_id: str) -> Optional[str]:
        """
        Save a test result to persistent storage.

        Args:
            result_data: Dictionary representation of the test result
            config_id: Configuration ID for the evaluation

        Returns:
            Result ID if saved successfully, None otherwise
        """
        if not self.session_manager:
            self.logger.warning("No session manager available to save test result")
            return None

        try:
            result_id = self.session_manager.save_qa_test_result(result_data, config_id)
            if result_id:
                self.logger.info(f"Saved test result with ID: {result_id}")
            else:
                self.logger.warning("Failed to save test result")
            return result_id
        except Exception as e:
            self.logger.error(f"Error saving test result: {e}")
            return None
