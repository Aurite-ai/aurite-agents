"""
Aurite Security Framework

A comprehensive security framework for AI agent systems, providing:
- Component-based security testing (LLM, MCP, Agent, Workflow)
- Integration with open-source security tools
- Real-time monitoring and threat detection

Key Components:
- SecurityEngine: Main orchestration engine
- Component Testers: Specialized security testing for each component type
- Security Configuration: Centralized configuration management
- API Layer: REST API for external integration

Usage:
    from aurite.security import SecurityEngine, create_default_security_config

    config = create_default_security_config()
    engine = SecurityEngine(config)

    # Assess LLM security
    result = await engine.assess_component_security(
        component_type="llm",
        component_id="my_llm",
        component_config={"provider": "openai", "model": "gpt-4"}
    )
"""

# Component testers
from .components.llm_security import LLMGuardBasic, LLMSecurityTester
from .core.base_tester import BaseSecurityTester, SecurityTest, SecurityTestResult
from .core.security_config import (
    SecurityConfig,
    create_default_security_config,
    create_production_security_config,
    load_security_config_from_dict,
)
from .core.security_engine import SecurityAssessmentResult, SecurityEngine, SecurityThreat

__version__ = "1.0.0-mvp"

__all__ = [
    # Core components
    "SecurityEngine",
    "SecurityThreat",
    "SecurityAssessmentResult",
    # Configuration
    "SecurityConfig",
    "create_default_security_config",
    "create_production_security_config",
    "load_security_config_from_dict",
    # Base classes
    "BaseSecurityTester",
    "SecurityTest",
    "SecurityTestResult",
    # Component testers
    "LLMSecurityTester",
    "LLMGuardBasic",
]
