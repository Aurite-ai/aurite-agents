"""
Aurite Security Framework - LLM Security Component

This module provides security testing and validation for Large Language Model (LLM)
components within the Aurite framework. It integrates with various open-source
security tools to provide comprehensive LLM security assessment.

Key Features:
- LLM Guard integration for input/output scanning
- Prompt injection detection
- Content filtering and validation
- Bias and toxicity detection
- Custom LLM security policies

Architecture:
- Modular security tool integration
- Extensible test framework
- Real-time monitoring capabilities
"""

from .llm_security_tester import LLMSecurityTester
from .llm_guard_basic import LLMGuardBasic

__all__ = [
    "LLMSecurityTester",
    "LLMGuardBasic"
]
