"""
QA Testing Module for the Aurite Framework.

This module provides the Quality Assurance testing system with:
- QAEngine: Main orchestration and execution class
- QASessionManager: Cache and session management
- Result models for evaluation tracking
- Utility functions for schema validation and formatting
"""

from .qa_engine import QAEngine
from .qa_models import (
    CaseEvaluationResult,
    ExpectationAnalysisResult,
    QAEvaluationResult,
    SchemaValidationResult,
)
from .qa_session_manager import QASessionManager
from .qa_utils import clean_llm_output, format_agent_conversation_history, validate_schema

__all__ = [
    # Core classes
    "QAEngine",
    "QASessionManager",
    # Result models
    "SchemaValidationResult",
    "ExpectationAnalysisResult",
    "CaseEvaluationResult",
    "QAEvaluationResult",
    # Utility functions
    "validate_schema",
    "clean_llm_output",
    "format_agent_conversation_history",
]
