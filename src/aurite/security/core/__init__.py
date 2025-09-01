"""
Aurite Security Framework - Core Module

This module contains the core components of the security framework:
- SecurityEngine: Main orchestration engine
- BaseSecurityTester: Abstract base class for component testers
- SecurityConfig: Configuration management
- Common data models and enums

These components provide the foundation for all security operations
"""

from .security_engine import SecurityEngine, SecurityThreat, SecurityAssessmentResult, SecurityLevel, SecurityStatus
from .base_tester import (
    BaseSecurityTester, SecurityTest, SecurityTestResult, ComponentSecurityAssessment,
    ThreatCategory, SecurityTestType
)
from .security_config import (
    SecurityConfig, ComponentSecurityConfig, SecurityToolConfig,
    MonitoringConfig, StorageConfig, APIConfig,
    SecurityMode, LogLevel,
    create_default_security_config, create_production_security_config,
    load_security_config_from_dict,
    create_default_llm_config, create_default_mcp_config,
    create_default_agent_config, create_default_workflow_config
)

__all__ = [
    # Main engine
    "SecurityEngine",
    
    # Data models
    "SecurityThreat",
    "SecurityAssessmentResult", 
    "SecurityLevel",
    "SecurityStatus",
    
    # Base tester
    "BaseSecurityTester",
    "SecurityTest",
    "SecurityTestResult",
    "ComponentSecurityAssessment",
    "ThreatCategory",
    "SecurityTestType",
    
    # Configuration
    "SecurityConfig",
    "ComponentSecurityConfig", 
    "SecurityToolConfig",
    "MonitoringConfig",
    "StorageConfig",
    "APIConfig",
    "SecurityMode",
    "LogLevel",
    
    # Configuration factories
    "create_default_security_config",
    "create_production_security_config",
    "load_security_config_from_dict",
    "create_default_llm_config",
    "create_default_mcp_config",
    "create_default_agent_config",
    "create_default_workflow_config",
]
