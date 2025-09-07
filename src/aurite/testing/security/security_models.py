"""
Aurite Security Framework - Security Models

This module provides all data models for the security framework,
including configuration, assessment results, threats, and test definitions.

Architecture Design:
- Centralized model definitions
- Component-specific security settings
- Validation and default value handling
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# ============================================================================
# Security Enums
# ============================================================================

__all__ = [
    # Enums
    "SecurityLevel",
    "SecurityStatus",
    "ThreatCategory",
    "SecurityTestType",
    "SecurityMode",
    "LogLevel",
    # Assessment Models
    "SecurityThreat",
    "SecurityTest",
    "SecurityTestResult",
    "SecurityAssessmentResult",
    "ComponentSecurityAssessment",
    # Configuration Models
    "SecurityToolConfig",
    "ComponentSecurityConfig",
    "MonitoringConfig",
    "StorageConfig",
    "APIConfig",
    "SecurityConfig",
    # Factory/utility functions
    "create_default_llm_config",
    "create_default_mcp_config",
    "create_default_agent_config",
    "create_default_workflow_config",
    "create_default_security_config",
    "load_security_config_from_dict",
    "create_production_security_config",
]


class SecurityLevel(Enum):
    """Security assessment levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityStatus(Enum):
    """Security assessment status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ThreatCategory(Enum):
    """Categories of security threats"""

    INJECTION = "injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_LEAKAGE = "data_leakage"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MALICIOUS_BEHAVIOR = "malicious_behavior"
    CONFIGURATION_ERROR = "configuration_error"
    PERFORMANCE_IMPACT = "performance_impact"
    COMPLIANCE_VIOLATION = "compliance_violation"


class SecurityTestType(Enum):
    """Types of security tests"""

    STATIC_ANALYSIS = "static_analysis"
    DYNAMIC_ANALYSIS = "dynamic_analysis"
    BEHAVIORAL_ANALYSIS = "behavioral_analysis"
    CONFIGURATION_AUDIT = "configuration_audit"
    PENETRATION_TEST = "penetration_test"
    COMPLIANCE_CHECK = "compliance_check"


class SecurityMode(Enum):
    """Security assessment modes"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    AUDIT = "audit"


class LogLevel(Enum):
    """Logging levels for security operations"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ============================================================================
# Security Assessment Models
# ============================================================================


@dataclass
class SecurityThreat:
    """Represents a detected security threat"""

    threat_id: str
    threat_type: str
    severity: SecurityLevel
    component_type: str
    component_id: str
    description: str
    details: Dict[str, Any]
    mitigation_suggestions: List[str]
    detected_at: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 0.0
    false_positive_likelihood: float = 0.0


@dataclass
class SecurityTest:
    """Represents a single security test"""

    test_id: str
    test_name: str
    test_type: SecurityTestType
    category: ThreatCategory
    description: str
    enabled: bool = True
    severity_weight: float = 1.0
    timeout_seconds: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityTestResult:
    """Results of a single security test"""

    test_id: str
    test_name: str
    passed: bool
    score: float
    threats_detected: List[Dict[str, Any]]
    recommendations: List[str]
    execution_time_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class SecurityAssessmentResult:
    """Results of a security assessment (aligned with QAEvaluationResult)"""

    assessment_id: str
    component_type: str
    component_id: str
    status: SecurityStatus
    overall_score: float
    threats: List[SecurityThreat]
    recommendations: List[str]
    test_results: List[SecurityTestResult]
    metadata: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    def add_threat(self, threat: SecurityThreat) -> None:
        """Add a threat to the assessment results"""
        self.threats.append(threat)

    def get_threats_by_severity(self, severity: SecurityLevel) -> List[SecurityThreat]:
        """Get threats filtered by severity level"""
        result = []
        for threat in self.threats:
            if isinstance(threat, SecurityThreat):
                if threat.severity == severity:
                    result.append(threat)
            elif isinstance(threat, dict):
                threat_severity = threat.get("severity", "unknown")
                if threat_severity == severity.value:
                    result.append(threat)
        return result

    def get_critical_threats(self) -> List[SecurityThreat]:
        """Get all critical threats"""
        return self.get_threats_by_severity(SecurityLevel.CRITICAL)

    def has_critical_threats(self) -> bool:
        """Check if assessment has critical threats"""
        return len(self.get_critical_threats()) > 0

    def to_legacy_format(self) -> Dict[str, Any]:
        """Convert to legacy format for backward compatibility (if needed)"""
        return {
            "assessment_id": self.assessment_id,
            "status": self.status.value,
            "overall_score": self.overall_score,
            "threats": [
                {
                    "threat_id": t.threat_id if isinstance(t, SecurityThreat) else t.get("threat_id"),
                    "severity": t.severity.value if isinstance(t, SecurityThreat) else t.get("severity"),
                    "description": t.description if isinstance(t, SecurityThreat) else t.get("description"),
                }
                for t in self.threats
            ],
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


# Alias for consistency with base_security_tester.py
ComponentSecurityAssessment = SecurityAssessmentResult


# ============================================================================
# Configuration Models
# ============================================================================


@dataclass
class SecurityToolConfig:
    """Configuration for a specific security tool"""

    tool_name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_attempts: int = 3
    priority: int = 1  # Higher numbers = higher priority


@dataclass
class ComponentSecurityConfig:
    """Security configuration for a specific component type"""

    component_type: str
    enabled: bool = True
    security_tools: Dict[str, SecurityToolConfig] = field(default_factory=dict)
    test_timeout_seconds: int = 60
    max_concurrent_tests: int = 5
    severity_threshold: str = "medium"  # minimum severity to report
    custom_rules: Dict[str, Any] = field(default_factory=dict)

    def add_security_tool(self, tool_config: SecurityToolConfig) -> None:
        """Add a security tool configuration"""
        self.security_tools[tool_config.tool_name] = tool_config

    def get_enabled_tools(self) -> Dict[str, SecurityToolConfig]:
        """Get all enabled security tools"""
        return {name: config for name, config in self.security_tools.items() if config.enabled}

    def enable_tool(self, tool_name: str) -> bool:
        """Enable a specific security tool"""
        if tool_name in self.security_tools:
            self.security_tools[tool_name].enabled = True
            return True
        return False

    def disable_tool(self, tool_name: str) -> bool:
        """Disable a specific security tool"""
        if tool_name in self.security_tools:
            self.security_tools[tool_name].enabled = False
            return True
        return False


@dataclass
class MonitoringConfig:
    """Configuration for real-time security monitoring"""

    enabled: bool = True
    monitoring_interval_seconds: int = 60
    alert_thresholds: Dict[str, Any] = field(
        default_factory=lambda: {
            "critical_threats": 1,
            "high_threats": 5,
            "failed_assessments": 3,
            "assessment_timeout_rate": 0.1,
        }
    )
    notification_channels: List[str] = field(default_factory=list)
    retention_days: int = 30


@dataclass
class StorageConfig:
    """Configuration for security data storage"""

    database_url: Optional[str] = None
    redis_url: Optional[str] = None
    storage_backend: str = "postgresql"  # postgresql, sqlite, memory
    encryption_enabled: bool = True
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    data_retention_days: int = 90


@dataclass
class APIConfig:
    """Configuration for security API endpoints"""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8001
    authentication_required: bool = True
    rate_limiting_enabled: bool = True
    max_requests_per_minute: int = 100
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])


@dataclass
class SecurityConfig:
    """Main security framework configuration"""

    # Core settings
    mode: SecurityMode = SecurityMode.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO
    max_concurrent_assessments: int = 10
    default_timeout_seconds: int = 120

    # Component configurations
    components: Dict[str, ComponentSecurityConfig] = field(default_factory=dict)

    # Infrastructure configurations
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    api: APIConfig = field(default_factory=APIConfig)

    # Framework-specific settings
    framework_adapter: Optional[str] = None
    custom_adapters: Dict[str, Any] = field(default_factory=dict)

    def add_component_config(self, config: ComponentSecurityConfig) -> None:
        """Add a component security configuration"""
        self.components[config.component_type] = config

    def get_component_config(self, component_type: str) -> Optional[ComponentSecurityConfig]:
        """Get configuration for a specific component type"""
        return self.components.get(component_type)

    def get_enabled_components(self) -> Dict[str, ComponentSecurityConfig]:
        """Get all enabled component configurations"""
        return {comp_type: config for comp_type, config in self.components.items() if config.enabled}

    def enable_component(self, component_type: str) -> bool:
        """Enable security for a specific component type"""
        if component_type in self.components:
            self.components[component_type].enabled = True
            return True
        return False

    def disable_component(self, component_type: str) -> bool:
        """Disable security for a specific component type"""
        if component_type in self.components:
            self.components[component_type].enabled = False
            return True
        return False

    def validate(self) -> List[str]:
        """
        Validate the security configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Validate basic settings
        if self.max_concurrent_assessments <= 0:
            errors.append("max_concurrent_assessments must be greater than 0")

        if self.default_timeout_seconds <= 0:
            errors.append("default_timeout_seconds must be greater than 0")

        # Validate component configurations
        if not self.components:
            errors.append("At least one component configuration is required")

        for comp_type, config in self.components.items():
            if not config.component_type:
                errors.append(f"Component type cannot be empty for {comp_type}")

            if config.test_timeout_seconds <= 0:
                errors.append(f"test_timeout_seconds must be greater than 0 for {comp_type}")

            if config.max_concurrent_tests <= 0:
                errors.append(f"max_concurrent_tests must be greater than 0 for {comp_type}")

        # Validate storage configuration
        if self.storage.storage_backend not in ["postgresql", "sqlite", "memory"]:
            errors.append("storage_backend must be one of: postgresql, sqlite, memory")

        if self.storage.storage_backend == "postgresql" and not self.storage.database_url:
            errors.append("database_url is required when using postgresql storage backend")

        # Validate API configuration
        if self.api.enabled:
            if self.api.port <= 0 or self.api.port > 65535:
                errors.append("API port must be between 1 and 65535")

            if self.api.max_requests_per_minute <= 0:
                errors.append("max_requests_per_minute must be greater than 0")

        # Validate monitoring configuration
        if self.monitoring.enabled:
            if self.monitoring.monitoring_interval_seconds <= 0:
                errors.append("monitoring_interval_seconds must be greater than 0")

            if self.monitoring.retention_days <= 0:
                errors.append("monitoring retention_days must be greater than 0")

        return errors


def create_default_llm_config() -> ComponentSecurityConfig:
    """Create default LLM security configuration"""
    config = ComponentSecurityConfig(
        component_type="llm", enabled=True, test_timeout_seconds=60, max_concurrent_tests=3, severity_threshold="medium"
    )

    # Add LLM Guard configuration
    llm_guard_config = SecurityToolConfig(
        tool_name="llm_guard",
        enabled=True,
        config={
            "input_scanners": [
                "Anonymize",
                "BanTopics",
                "Code",
                "Language",
                "PromptInjection",
                "Secrets",
                "TokenLimit",
                "Toxicity",
            ],
            "output_scanners": ["BanTopics", "Bias", "Code", "MaliciousURLs", "NoRefusal", "Sensitive", "Toxicity"],
            "fail_fast": False,
            "return_scores": True,
        },
        timeout_seconds=30,
        priority=1,
    )
    config.add_security_tool(llm_guard_config)

    return config


def create_default_mcp_config() -> ComponentSecurityConfig:
    """Create default MCP security configuration"""
    config = ComponentSecurityConfig(
        component_type="mcp", enabled=True, test_timeout_seconds=45, max_concurrent_tests=5, severity_threshold="medium"
    )

    # Add MCP-specific security tools (placeholder for future implementation)
    mcp_validator_config = SecurityToolConfig(
        tool_name="mcp_validator",
        enabled=True,
        config={
            "check_permissions": True,
            "validate_tools": True,
            "scan_communications": True,
            "audit_privileges": True,
        },
        timeout_seconds=30,
        priority=1,
    )
    config.add_security_tool(mcp_validator_config)

    return config


def create_default_agent_config() -> ComponentSecurityConfig:
    """Create default Agent security configuration"""
    config = ComponentSecurityConfig(
        component_type="agent",
        enabled=True,
        test_timeout_seconds=90,
        max_concurrent_tests=3,
        severity_threshold="medium",
    )

    # Add AgentOps configuration (placeholder for future implementation)
    agentops_config = SecurityToolConfig(
        tool_name="agentops",
        enabled=True,
        config={"monitor_behavior": True, "track_goals": True, "detect_anomalies": True, "audit_memory": True},
        timeout_seconds=45,
        priority=1,
    )
    config.add_security_tool(agentops_config)

    return config


def create_default_workflow_config() -> ComponentSecurityConfig:
    """Create default Workflow security configuration"""
    config = ComponentSecurityConfig(
        component_type="workflow",
        enabled=True,
        test_timeout_seconds=120,
        max_concurrent_tests=2,
        severity_threshold="medium",
    )

    # Add workflow-specific security tools (placeholder for future implementation)
    workflow_validator_config = SecurityToolConfig(
        tool_name="workflow_validator",
        enabled=True,
        config={
            "validate_data_flow": True,
            "check_step_isolation": True,
            "audit_permissions": True,
            "detect_injections": True,
        },
        timeout_seconds=60,
        priority=1,
    )
    config.add_security_tool(workflow_validator_config)

    return config


def create_default_security_config() -> SecurityConfig:
    """
    Create a default security configuration with all components enabled.

    This provides a good starting point for most use cases and can be
    customized based on specific requirements.
    """
    config = SecurityConfig(
        mode=SecurityMode.DEVELOPMENT,
        log_level=LogLevel.INFO,
        max_concurrent_assessments=10,
        default_timeout_seconds=120,
    )

    # Add default component configurations
    config.add_component_config(create_default_llm_config())
    config.add_component_config(create_default_mcp_config())
    config.add_component_config(create_default_agent_config())
    config.add_component_config(create_default_workflow_config())

    # Configure monitoring
    config.monitoring = MonitoringConfig(
        enabled=True,
        monitoring_interval_seconds=60,
        alert_thresholds={
            "critical_threats": 1,
            "high_threats": 5,
            "failed_assessments": 3,
            "assessment_timeout_rate": 0.1,
        },
        retention_days=30,
    )

    # Configure storage
    config.storage = StorageConfig(
        storage_backend="postgresql", encryption_enabled=True, backup_enabled=True, data_retention_days=90
    )

    # Configure API
    config.api = APIConfig(
        enabled=True,
        host="0.0.0.0",
        port=8001,
        authentication_required=True,
        rate_limiting_enabled=True,
        max_requests_per_minute=100,
    )

    return config


def load_security_config_from_dict(config_dict: Dict[str, Any]) -> SecurityConfig:
    """
    Load security configuration from a dictionary.

    This function provides a way to create SecurityConfig instances
    from configuration files or environment variables.

    Args:
        config_dict: Dictionary containing configuration values

    Returns:
        SecurityConfig instance
    """
    # Start with default configuration
    config = create_default_security_config()

    # Override with provided values
    if "mode" in config_dict:
        config.mode = SecurityMode(config_dict["mode"])

    if "log_level" in config_dict:
        config.log_level = LogLevel(config_dict["log_level"])

    if "max_concurrent_assessments" in config_dict:
        config.max_concurrent_assessments = config_dict["max_concurrent_assessments"]

    if "default_timeout_seconds" in config_dict:
        config.default_timeout_seconds = config_dict["default_timeout_seconds"]

    # Override component configurations
    if "components" in config_dict:
        for comp_type, comp_config in config_dict["components"].items():
            if comp_type in config.components:
                # Update existing component config
                existing_config = config.components[comp_type]
                if "enabled" in comp_config:
                    existing_config.enabled = comp_config["enabled"]
                if "test_timeout_seconds" in comp_config:
                    existing_config.test_timeout_seconds = comp_config["test_timeout_seconds"]
                if "max_concurrent_tests" in comp_config:
                    existing_config.max_concurrent_tests = comp_config["max_concurrent_tests"]
                if "severity_threshold" in comp_config:
                    existing_config.severity_threshold = comp_config["severity_threshold"]

    # Override monitoring configuration
    if "monitoring" in config_dict:
        monitoring_config = config_dict["monitoring"]
        if "enabled" in monitoring_config:
            config.monitoring.enabled = monitoring_config["enabled"]
        if "monitoring_interval_seconds" in monitoring_config:
            config.monitoring.monitoring_interval_seconds = monitoring_config["monitoring_interval_seconds"]
        if "alert_thresholds" in monitoring_config:
            config.monitoring.alert_thresholds.update(monitoring_config["alert_thresholds"])

    # Override storage configuration
    if "storage" in config_dict:
        storage_config = config_dict["storage"]
        if "database_url" in storage_config:
            config.storage.database_url = storage_config["database_url"]
        if "redis_url" in storage_config:
            config.storage.redis_url = storage_config["redis_url"]
        if "storage_backend" in storage_config:
            config.storage.storage_backend = storage_config["storage_backend"]
        if "encryption_enabled" in storage_config:
            config.storage.encryption_enabled = storage_config["encryption_enabled"]

    # Override API configuration
    if "api" in config_dict:
        api_config = config_dict["api"]
        if "enabled" in api_config:
            config.api.enabled = api_config["enabled"]
        if "host" in api_config:
            config.api.host = api_config["host"]
        if "port" in api_config:
            config.api.port = api_config["port"]
        if "authentication_required" in api_config:
            config.api.authentication_required = api_config["authentication_required"]

    return config


def create_production_security_config() -> SecurityConfig:
    """
    Create a production-ready security configuration.

    This configuration is optimized for production environments with
    enhanced security settings and monitoring.
    """
    config = create_default_security_config()

    # Production-specific settings
    config.mode = SecurityMode.PRODUCTION
    config.log_level = LogLevel.WARNING
    config.max_concurrent_assessments = 20

    # Enhanced monitoring for production
    config.monitoring.enabled = True
    config.monitoring.monitoring_interval_seconds = 30
    config.monitoring.alert_thresholds = {
        "critical_threats": 1,
        "high_threats": 3,
        "failed_assessments": 2,
        "assessment_timeout_rate": 0.05,
    }
    config.monitoring.retention_days = 90

    # Production storage settings
    config.storage.encryption_enabled = True
    config.storage.backup_enabled = True
    config.storage.backup_interval_hours = 6
    config.storage.data_retention_days = 365

    # Production API settings
    config.api.authentication_required = True
    config.api.rate_limiting_enabled = True
    config.api.max_requests_per_minute = 200
    config.api.cors_enabled = False  # More restrictive in production

    # Tighter timeouts for production
    for component_config in config.components.values():
        component_config.test_timeout_seconds = min(component_config.test_timeout_seconds, 60)
        component_config.severity_threshold = "low"  # Report more threats in production

    return config
