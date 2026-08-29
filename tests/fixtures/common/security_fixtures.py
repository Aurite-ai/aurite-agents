"""
Shared fixtures for Security testing.

This module provides reusable test data, mock functions, and fixtures
for testing the Security Engine and related components.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest

from aurite.testing.security.security_models import (
    ComponentSecurityConfig,
    SecurityAssessmentResult,
    SecurityConfig,
    SecurityLevel,
    SecurityStatus,
    SecurityTest,
    SecurityTestResult,
    SecurityTestType,
    SecurityThreat,
    ThreatCategory,
    create_default_llm_config,
    create_default_security_config,
)

# --- Test Data Factories ---


def create_security_threats() -> List[SecurityThreat]:
    """Create sample security threats for testing."""
    return [
        SecurityThreat(
            threat_id="threat_001",
            threat_type="prompt_injection",
            severity=SecurityLevel.HIGH,
            component_type="llm",
            component_id="test_llm_1",
            description="Potential prompt injection detected",
            details={"pattern": "ignore previous instructions", "confidence": 0.85},
            mitigation_suggestions=["Implement input validation", "Use prompt guards"],
            confidence_score=0.85,
            false_positive_likelihood=0.15,
        ),
        SecurityThreat(
            threat_id="threat_002",
            threat_type="data_leakage",
            severity=SecurityLevel.MEDIUM,
            component_type="llm",
            component_id="test_llm_1",
            description="Possible sensitive data exposure",
            details={"data_type": "PII", "fields": ["email", "phone"]},
            mitigation_suggestions=["Implement data masking", "Add output filtering"],
            confidence_score=0.70,
            false_positive_likelihood=0.30,
        ),
        SecurityThreat(
            threat_id="threat_003",
            threat_type="configuration_error",
            severity=SecurityLevel.LOW,
            component_type="llm",
            component_id="test_llm_1",
            description="Insecure configuration detected",
            details={"setting": "temperature", "value": 1.5, "recommended": 0.7},
            mitigation_suggestions=["Adjust temperature setting"],
            confidence_score=0.95,
            false_positive_likelihood=0.05,
        ),
    ]


def create_critical_threats() -> List[SecurityThreat]:
    """Create critical security threats for testing."""
    return [
        SecurityThreat(
            threat_id="threat_critical_001",
            threat_type="malicious_code_execution",
            severity=SecurityLevel.CRITICAL,
            component_type="agent",
            component_id="test_agent_1",
            description="Attempted code execution detected",
            details={"code": "os.system('rm -rf /')", "blocked": True},
            mitigation_suggestions=["Enable sandboxing", "Restrict system access"],
            confidence_score=0.99,
            false_positive_likelihood=0.01,
        ),
        SecurityThreat(
            threat_id="threat_critical_002",
            threat_type="privilege_escalation",
            severity=SecurityLevel.CRITICAL,
            component_type="mcp",
            component_id="test_mcp_1",
            description="Unauthorized privilege escalation attempt",
            details={"from_role": "user", "to_role": "admin", "blocked": True},
            mitigation_suggestions=["Review permission model", "Implement RBAC"],
            confidence_score=0.95,
            false_positive_likelihood=0.05,
        ),
    ]


def create_security_tests() -> Dict[str, SecurityTest]:
    """Create sample security tests."""
    return {
        "prompt_injection_basic": SecurityTest(
            test_id="prompt_injection_basic",
            test_name="Basic Prompt Injection Test",
            test_type=SecurityTestType.DYNAMIC_ANALYSIS,
            category=ThreatCategory.INJECTION,
            description="Tests for basic prompt injection vulnerabilities",
            enabled=True,
            severity_weight=2.0,
            timeout_seconds=30,
        ),
        "secrets_detection": SecurityTest(
            test_id="secrets_detection",
            test_name="Secrets Detection Test",
            test_type=SecurityTestType.STATIC_ANALYSIS,
            category=ThreatCategory.DATA_LEAKAGE,
            description="Scans for exposed secrets and credentials",
            enabled=True,
            severity_weight=1.5,
            timeout_seconds=20,
        ),
        "llm_config_audit": SecurityTest(
            test_id="llm_config_audit",
            test_name="LLM Configuration Audit",
            test_type=SecurityTestType.CONFIGURATION_AUDIT,
            category=ThreatCategory.CONFIGURATION_ERROR,
            description="Audits LLM configuration for security issues",
            enabled=True,
            severity_weight=1.0,
            timeout_seconds=15,
        ),
        "toxicity_detection": SecurityTest(
            test_id="toxicity_detection",
            test_name="Toxicity Detection Test",
            test_type=SecurityTestType.BEHAVIORAL_ANALYSIS,
            category=ThreatCategory.MALICIOUS_BEHAVIOR,
            description="Detects toxic or harmful content",
            enabled=True,
            severity_weight=1.2,
            timeout_seconds=25,
        ),
        "token_limit_check": SecurityTest(
            test_id="token_limit_check",
            test_name="Token Limit Security Check",
            test_type=SecurityTestType.CONFIGURATION_AUDIT,
            category=ThreatCategory.PERFORMANCE_IMPACT,
            description="Checks token limits for security implications",
            enabled=False,  # Disabled by default
            severity_weight=0.8,
            timeout_seconds=10,
        ),
    }


def create_test_results_passing() -> List[SecurityTestResult]:
    """Create passing test results."""
    return [
        SecurityTestResult(
            test_id="prompt_injection_basic",
            test_name="Basic Prompt Injection Test",
            passed=True,
            score=9.5,
            threats_detected=[],
            recommendations=[],
            execution_time_seconds=2.5,
        ),
        SecurityTestResult(
            test_id="secrets_detection",
            test_name="Secrets Detection Test",
            passed=True,
            score=10.0,
            threats_detected=[],
            recommendations=[],
            execution_time_seconds=1.8,
        ),
        SecurityTestResult(
            test_id="llm_config_audit",
            test_name="LLM Configuration Audit",
            passed=True,
            score=8.0,
            threats_detected=[],
            recommendations=["Consider lowering temperature for more consistent outputs"],
            execution_time_seconds=1.2,
        ),
    ]


def create_test_results_with_failures() -> List[SecurityTestResult]:
    """Create test results with some failures."""
    threats = create_security_threats()
    return [
        SecurityTestResult(
            test_id="prompt_injection_basic",
            test_name="Basic Prompt Injection Test",
            passed=False,
            score=3.0,
            threats_detected=[
                {
                    "threat_id": threats[0].threat_id,
                    "threat_type": threats[0].threat_type,
                    "severity": threats[0].severity.value,
                    "description": threats[0].description,
                }
            ],
            recommendations=["Implement input validation", "Use prompt guards"],
            execution_time_seconds=3.2,
        ),
        SecurityTestResult(
            test_id="secrets_detection",
            test_name="Secrets Detection Test",
            passed=False,
            score=4.5,
            threats_detected=[
                {
                    "threat_id": threats[1].threat_id,
                    "threat_type": threats[1].threat_type,
                    "severity": threats[1].severity.value,
                    "description": threats[1].description,
                }
            ],
            recommendations=["Implement data masking", "Add output filtering"],
            execution_time_seconds=2.1,
        ),
        SecurityTestResult(
            test_id="llm_config_audit",
            test_name="LLM Configuration Audit",
            passed=True,
            score=7.5,
            threats_detected=[],
            recommendations=["Temperature setting could be optimized"],
            execution_time_seconds=1.5,
        ),
    ]


def create_llm_config() -> Dict[str, Any]:
    """Create a sample LLM configuration for testing."""
    return {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 1000,
        "api_key_env_var": "OPENAI_API_KEY",
    }


def create_mcp_config() -> Dict[str, Any]:
    """Create a sample MCP configuration for testing."""
    return {
        "name": "test_mcp_server",
        "command": "python",
        "args": ["-m", "test_server"],
        "env": {"TEST_ENV": "value"},
    }


def create_agent_config() -> Dict[str, Any]:
    """Create a sample Agent configuration for testing."""
    return {
        "name": "test_agent",
        "llm": "test_llm",
        "tools": ["search", "calculator"],
        "max_iterations": 5,
    }


def create_workflow_config() -> Dict[str, Any]:
    """Create a sample Workflow configuration for testing."""
    return {
        "name": "test_workflow",
        "steps": [
            {"type": "agent", "config": "test_agent"},
            {"type": "llm", "config": "test_llm"},
        ],
    }


# --- Fixtures ---


@pytest.fixture
def security_config() -> SecurityConfig:
    """Default security configuration for testing."""
    return create_default_security_config()


@pytest.fixture
def llm_security_config() -> ComponentSecurityConfig:
    """LLM-specific security configuration."""
    return create_default_llm_config()


@pytest.fixture
def sample_threats() -> List[SecurityThreat]:
    """Sample security threats for testing."""
    return create_security_threats()


@pytest.fixture
def critical_threats() -> List[SecurityThreat]:
    """Critical security threats for testing."""
    return create_critical_threats()


@pytest.fixture
def sample_security_tests() -> Dict[str, SecurityTest]:
    """Sample security tests."""
    return create_security_tests()


@pytest.fixture
def passing_test_results() -> List[SecurityTestResult]:
    """Test results with all tests passing."""
    return create_test_results_passing()


@pytest.fixture
def failing_test_results() -> List[SecurityTestResult]:
    """Test results with some failures."""
    return create_test_results_with_failures()


@pytest.fixture
def sample_assessment_result(sample_threats, passing_test_results) -> SecurityAssessmentResult:
    """Sample security assessment result."""
    return SecurityAssessmentResult(
        assessment_id="security_test123",
        component_type="llm",
        component_id="test_llm_1",
        status=SecurityStatus.COMPLETED,
        overall_score=8.5,
        threats=sample_threats,
        recommendations=[
            "Implement input validation",
            "Use prompt guards",
            "Implement data masking",
            "Adjust temperature setting",
        ],
        test_results=passing_test_results,
        metadata={"test": True, "framework": "aurite"},
        started_at=datetime(2024, 1, 1, 0, 0, 0),
        completed_at=datetime(2024, 1, 1, 0, 0, 10),
        duration_seconds=10.0,
    )


@pytest.fixture
def failed_assessment_result(critical_threats, failing_test_results) -> SecurityAssessmentResult:
    """Failed security assessment result with critical threats."""
    return SecurityAssessmentResult(
        assessment_id="security_failed_test",
        component_type="agent",
        component_id="test_agent_1",
        status=SecurityStatus.COMPLETED,
        overall_score=3.5,
        threats=critical_threats,
        recommendations=[
            "CRITICAL: Enable sandboxing immediately",
            "CRITICAL: Restrict system access",
            "Review and update security policies",
        ],
        test_results=failing_test_results,
        metadata={"test": True, "critical": True},
        started_at=datetime(2024, 1, 1, 0, 0, 0),
        completed_at=datetime(2024, 1, 1, 0, 0, 15),
        duration_seconds=15.0,
    )


@pytest.fixture
def mock_security_engine():
    """Mock SecurityEngine for testing."""
    engine = AsyncMock()

    # Mock assessment methods
    async def assess_component_side_effect(
        component_type: str,
        component_id: str,
        component_config: Dict[str, Any],
        assessment_options: Optional[Dict[str, Any]] = None,
    ):
        # Return different results based on component type
        if component_type == "llm":
            threats = create_security_threats()
            test_results = create_test_results_with_failures()
        elif component_type == "agent" and "malicious" in component_id:
            threats = create_critical_threats()
            test_results = create_test_results_with_failures()
        else:
            threats = []
            test_results = create_test_results_passing()

        return SecurityAssessmentResult(
            assessment_id=f"security_{component_id}_{datetime.utcnow().isoformat()}",
            component_type=component_type,
            component_id=component_id,
            status=SecurityStatus.COMPLETED,
            overall_score=8.5 if not threats else 3.5,
            threats=threats,
            recommendations=["Test recommendation"],
            test_results=test_results,
            metadata=assessment_options or {},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=5.0,
        )

    engine.assess_component_security.side_effect = assess_component_side_effect

    # Mock full configuration assessment
    async def assess_full_config_side_effect(
        configuration: Dict[str, Any],
        assessment_options: Optional[Dict[str, Any]] = None,
    ):
        results = {}
        for comp_type, components in configuration.items():
            if isinstance(components, dict):
                for comp_id, comp_config in components.items():
                    result = await assess_component_side_effect(comp_type, comp_id, comp_config, assessment_options)
                    results[f"{comp_type}_{comp_id}"] = result
        return results

    engine.assess_full_configuration.side_effect = assess_full_config_side_effect

    return engine


@pytest.fixture
def mock_llm_guard():
    """Mock LLMGuardBasic for testing."""
    guard = AsyncMock()

    # Mock scan methods
    async def scan_input_side_effect(text: str):
        if "ignore previous instructions" in text.lower():
            return {
                "valid": False,
                "score": 3.0,
                "threats": [
                    {
                        "type": "prompt_injection",
                        "severity": "high",
                        "confidence": 0.85,
                    }
                ],
            }
        elif "api key" in text.lower() or "sk-" in text:
            return {
                "valid": False,
                "score": 4.0,
                "threats": [
                    {
                        "type": "secrets_detected",
                        "severity": "critical",
                        "confidence": 0.95,
                    }
                ],
            }
        else:
            return {
                "valid": True,
                "score": 9.5,
                "threats": [],
            }

    guard.scan_input.side_effect = scan_input_side_effect

    async def scan_output_side_effect(text: str):
        if "malware" in text.lower() or "http://malware" in text:
            return {
                "valid": False,
                "score": 2.0,
                "threats": [
                    {
                        "type": "malicious_url",
                        "severity": "critical",
                        "confidence": 0.90,
                    }
                ],
            }
        elif any(toxic in text.lower() for toxic in ["hate", "kill", "die"]):
            return {
                "valid": False,
                "score": 3.5,
                "threats": [
                    {
                        "type": "toxicity",
                        "severity": "high",
                        "confidence": 0.80,
                    }
                ],
            }
        else:
            return {
                "valid": True,
                "score": 9.0,
                "threats": [],
            }

    guard.scan_output.side_effect = scan_output_side_effect

    return guard


# --- Helper Functions ---


def assert_assessment_result_valid(result: SecurityAssessmentResult) -> None:
    """Helper to assert that a security assessment result is valid."""
    assert result.assessment_id
    assert result.status in [
        SecurityStatus.PENDING,
        SecurityStatus.RUNNING,
        SecurityStatus.COMPLETED,
        SecurityStatus.FAILED,
        SecurityStatus.CANCELLED,
    ]
    assert 0 <= result.overall_score <= 10
    assert isinstance(result.threats, list)
    assert isinstance(result.recommendations, list)
    assert isinstance(result.test_results, list)
    assert result.started_at
    if result.status in [SecurityStatus.COMPLETED, SecurityStatus.FAILED]:
        assert result.completed_at
        assert result.duration_seconds is not None and result.duration_seconds >= 0


def assert_threat_valid(threat: SecurityThreat) -> None:
    """Helper to assert that a security threat is valid."""
    assert threat.threat_id
    assert threat.threat_type
    assert threat.severity in [
        SecurityLevel.LOW,
        SecurityLevel.MEDIUM,
        SecurityLevel.HIGH,
        SecurityLevel.CRITICAL,
    ]
    assert threat.description
    assert isinstance(threat.mitigation_suggestions, list)
    assert 0 <= threat.confidence_score <= 1
    assert 0 <= threat.false_positive_likelihood <= 1


def assert_test_result_valid(result: SecurityTestResult) -> None:
    """Helper to assert that a test result is valid."""
    assert result.test_id
    assert result.test_name
    assert isinstance(result.passed, bool)
    assert 0 <= result.score <= 10
    assert isinstance(result.threats_detected, list)
    assert isinstance(result.recommendations, list)
    assert result.execution_time_seconds >= 0
