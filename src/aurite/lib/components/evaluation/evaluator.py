"""
Backward compatibility wrapper for the evaluation system.

This module provides compatibility with the old evaluation API while
the system migrates to the new testing framework architecture.
All functionality has been moved to aurite.testing.qa.qa_engine.
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

from aurite.lib.models.api.requests import EvaluationRequest
from aurite.testing.qa.qa_engine import QAEngine

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)

# Create a module-level QAEngine instance for backward compatibility
_qa_engine: Optional[QAEngine] = None


def _get_qa_engine(executor: Optional["AuriteEngine"] = None) -> QAEngine:
    """
    Get or create the QA engine instance.

    Args:
        executor: Optional AuriteEngine with config manager

    Returns:
        QAEngine instance
    """
    global _qa_engine

    if _qa_engine is None or (executor and executor._config_manager):
        # Create new instance if we don't have one or if we have a new config manager
        config_manager = executor._config_manager if executor else None
        _qa_engine = QAEngine(config_manager=config_manager)

    return _qa_engine


async def evaluate(
    request: EvaluationRequest,
    executor: Optional["AuriteEngine"] = None,
) -> Any:
    """
    Evaluates one or more evaluation test cases.

    This is a backward compatibility wrapper that maintains the original
    function interface while using the new QAEngine implementation.

    Args:
        request: The EvaluationRequest object
        executor: The AuriteEngine instance to run agents

    Returns:
        A dictionary containing the result or an error.
    """
    logger.info("Using backward compatibility wrapper for evaluate function")

    # Get or create QA engine
    qa_engine = _get_qa_engine(executor)

    # Run the evaluation using the new engine
    result = await qa_engine.evaluate_component(request, executor)

    # Convert to legacy format
    return result.to_legacy_format()


# For backward compatibility, also export the evaluate function directly
__all__ = ["evaluate"]
