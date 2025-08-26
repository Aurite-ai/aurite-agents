"""
Aurite Security Framework - Base Security Tester

This module provides the abstract base class for all component security testers.
It defines the common interface and shared functionality that all security testers
must implement, ensuring consistency across different component types.

Architecture Design:
- Abstract base class for all security testers
- Standardized interface for security assessments
- Common threat detection and reporting patterns
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio
from enum import Enum

from .security_config import ComponentSecurityConfig


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
class ComponentSecurityAssessment:
    """Complete security assessment results for a component"""
    component_id: str
    component_type: str
    overall_score: float
    threats: List[Dict[str, Any]]
    recommendations: List[str]
    test_results: List[SecurityTestResult]
    metadata: Dict[str, Any]
    assessment_duration: float


class BaseSecurityTester(ABC):
    """
    Abstract base class for all component security testers.
    
    This class defines the common interface that all security testers must implement,
    ensuring consistency across different component types (LLM, MCP, Agent, Workflow).
    """
    
    def __init__(self, config: ComponentSecurityConfig):
        """
        Initialize the security tester.
        
        Args:
            config: Component-specific security configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._security_tests: Dict[str, SecurityTest] = {}
        self._initialize_tests()
    
    @abstractmethod
    def _initialize_tests(self) -> None:
        """
        Initialize the security tests for this component type.
        
        This method should populate self._security_tests with all available
        security tests for the specific component type.
        """
        pass
    
    @abstractmethod
    async def _execute_test(
        self,
        test: SecurityTest,
        component_id: str,
        component_config: Dict[str, Any],
        options: Dict[str, Any]
    ) -> SecurityTestResult:
        """
        Execute a single security test.
        
        Args:
            test: The security test to execute
            component_id: Unique identifier for the component
            component_config: Component configuration to test
            options: Additional test options
            
        Returns:
            SecurityTestResult containing the test results
        """
        pass
    
    async def assess_security(
        self,
        component_id: str,
        component_config: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> ComponentSecurityAssessment:
        """
        Perform comprehensive security assessment on a component.
        
        Args:
            component_id: Unique identifier for the component
            component_config: Component configuration to assess
            options: Optional assessment parameters
            
        Returns:
            ComponentSecurityAssessment containing all assessment results
        """
        start_time = datetime.utcnow()
        options = options or {}
        
        self.logger.info(f"Starting security assessment for {self.__class__.__name__}: {component_id}")
        
        # Get enabled tests
        enabled_tests = [
            test for test in self._security_tests.values()
            if test.enabled and self._should_run_test(test, options)
        ]
        
        if not enabled_tests:
            self.logger.warning(f"No enabled tests found for {component_id}")
            return ComponentSecurityAssessment(
                component_id=component_id,
                component_type=self.get_component_type(),
                overall_score=0.0,
                threats=[],
                recommendations=["No security tests were executed"],
                test_results=[],
                metadata={"warning": "No enabled tests found"},
                assessment_duration=0.0
            )
        
        # Execute tests
        test_results = []
        for test in enabled_tests:
            try:
                self.logger.debug(f"Executing test: {test.test_name}")
                result = await self._execute_test(test, component_id, component_config, options)
                test_results.append(result)
                
                if not result.passed:
                    self.logger.warning(f"Test failed: {test.test_name} - {result.error_message}")
                
            except asyncio.TimeoutError:
                self.logger.error(f"Test timeout: {test.test_name}")
                test_results.append(SecurityTestResult(
                    test_id=test.test_id,
                    test_name=test.test_name,
                    passed=False,
                    score=0.0,
                    threats_detected=[],
                    recommendations=[f"Test timed out after {test.timeout_seconds} seconds"],
                    execution_time_seconds=test.timeout_seconds,
                    error_message=f"Test timed out after {test.timeout_seconds} seconds"
                ))
            except Exception as e:
                self.logger.error(f"Test error: {test.test_name} - {str(e)}")
                test_results.append(SecurityTestResult(
                    test_id=test.test_id,
                    test_name=test.test_name,
                    passed=False,
                    score=0.0,
                    threats_detected=[],
                    recommendations=[f"Test failed with error: {str(e)}"],
                    execution_time_seconds=0.0,
                    error_message=str(e)
                ))
        
        # Calculate overall assessment results
        assessment = self._calculate_assessment_results(
            component_id=component_id,
            test_results=test_results,
            start_time=start_time,
            options=options
        )
        
        self.logger.info(
            f"Completed security assessment for {component_id}: "
            f"Score={assessment.overall_score:.2f}, "
            f"Threats={len(assessment.threats)}, "
            f"Duration={assessment.assessment_duration:.2f}s"
        )
        
        return assessment
    
    def _should_run_test(self, test: SecurityTest, options: Dict[str, Any]) -> bool:
        """
        Determine if a test should be run based on options and configuration.
        
        Args:
            test: The security test to check
            options: Assessment options
            
        Returns:
            True if the test should be run, False otherwise
        """
        # Check if specific tests are requested
        if "tests" in options:
            return test.test_id in options["tests"]
        
        # Check if specific categories are requested
        if "categories" in options:
            return test.category.value in options["categories"]
        
        # Check if specific test types are requested
        if "test_types" in options:
            return test.test_type.value in options["test_types"]
        
        # Default: run all enabled tests
        return True
    
    def _calculate_assessment_results(
        self,
        component_id: str,
        test_results: List[SecurityTestResult],
        start_time: datetime,
        options: Dict[str, Any]
    ) -> ComponentSecurityAssessment:
        """
        Calculate overall assessment results from individual test results.
        
        Args:
            component_id: Component identifier
            test_results: Results from all executed tests
            start_time: Assessment start time
            options: Assessment options
            
        Returns:
            ComponentSecurityAssessment with calculated results
        """
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Collect all threats and recommendations
        all_threats = []
        all_recommendations = []
        
        for result in test_results:
            all_threats.extend(result.threats_detected)
            all_recommendations.extend(result.recommendations)
        
        # Remove duplicate recommendations
        unique_recommendations = list(set(all_recommendations))
        
        # Calculate overall score
        if test_results:
            # Weighted average based on test severity weights
            total_weighted_score = 0.0
            total_weight = 0.0
            
            for result in test_results:
                test = self._security_tests.get(result.test_id)
                weight = test.severity_weight if test else 1.0
                total_weighted_score += result.score * weight
                total_weight += weight
            
            overall_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        else:
            overall_score = 0.0
        
        # Add component-specific recommendations
        component_recommendations = self._get_component_specific_recommendations(
            test_results, all_threats, options
        )
        unique_recommendations.extend(component_recommendations)
        unique_recommendations = list(set(unique_recommendations))
        
        # Create metadata
        metadata = {
            "tests_executed": len(test_results),
            "tests_passed": sum(1 for r in test_results if r.passed),
            "tests_failed": sum(1 for r in test_results if not r.passed),
            "total_threats": len(all_threats),
            "assessment_options": options,
            "component_type": self.get_component_type()
        }
        
        # Add threat severity breakdown
        threat_severity_counts = {}
        for threat in all_threats:
            severity = threat.get("severity", "unknown")
            threat_severity_counts[severity] = threat_severity_counts.get(severity, 0) + 1
        metadata["threat_severity_breakdown"] = threat_severity_counts
        
        return ComponentSecurityAssessment(
            component_id=component_id,
            component_type=self.get_component_type(),
            overall_score=overall_score,
            threats=all_threats,
            recommendations=unique_recommendations,
            test_results=test_results,
            metadata=metadata,
            assessment_duration=duration
        )
    
    def _get_component_specific_recommendations(
        self,
        test_results: List[SecurityTestResult],
        threats: List[Dict[str, Any]],
        options: Dict[str, Any]
    ) -> List[str]:
        """
        Generate component-specific security recommendations.
        
        This method can be overridden by subclasses to provide
        component-specific recommendations based on assessment results.
        
        Args:
            test_results: Results from all executed tests
            threats: All detected threats
            options: Assessment options
            
        Returns:
            List of component-specific recommendations
        """
        recommendations = []
        
        # Generic recommendations based on test results
        failed_tests = [r for r in test_results if not r.passed]
        if failed_tests:
            recommendations.append(
                f"Review and address {len(failed_tests)} failed security tests"
            )
        
        # Recommendations based on threat severity
        critical_threats = [t for t in threats if t.get("severity") == "critical"]
        if critical_threats:
            recommendations.append(
                f"Immediately address {len(critical_threats)} critical security threats"
            )
        
        high_threats = [t for t in threats if t.get("severity") == "high"]
        if high_threats:
            recommendations.append(
                f"Prioritize resolution of {len(high_threats)} high-severity threats"
            )
        
        return recommendations
    
    @abstractmethod
    def get_component_type(self) -> str:
        """
        Get the component type this tester handles.
        
        Returns:
            String identifier for the component type (e.g., "llm", "mcp", "agent", "workflow")
        """
        pass
    
    def get_available_tests(self) -> Dict[str, SecurityTest]:
        """Get all available security tests for this component type"""
        return self._security_tests.copy()
    
    def get_enabled_tests(self) -> Dict[str, SecurityTest]:
        """Get all enabled security tests for this component type"""
        return {
            test_id: test for test_id, test in self._security_tests.items()
            if test.enabled
        }
    
    def enable_test(self, test_id: str) -> bool:
        """Enable a specific security test"""
        if test_id in self._security_tests:
            self._security_tests[test_id].enabled = True
            return True
        return False
    
    def disable_test(self, test_id: str) -> bool:
        """Disable a specific security test"""
        if test_id in self._security_tests:
            self._security_tests[test_id].enabled = False
            return True
        return False
    
    def get_test_categories(self) -> Set[ThreatCategory]:
        """Get all threat categories covered by this tester"""
        return {test.category for test in self._security_tests.values()}
    
    def get_test_types(self) -> Set[SecurityTestType]:
        """Get all test types supported by this tester"""
        return {test.test_type for test in self._security_tests.values()}
    
    async def validate_component_config(self, component_config: Dict[str, Any]) -> List[str]:
        """
        Validate component configuration for security assessment.
        
        Args:
            component_config: Component configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Basic validation - can be overridden by subclasses
        if not isinstance(component_config, dict):
            errors.append("Component configuration must be a dictionary")
        
        if not component_config:
            errors.append("Component configuration cannot be empty")
        
        return errors
    
    async def shutdown(self) -> None:
        """
        Shutdown the security tester and cleanup resources.
        
        This method can be overridden by subclasses to perform
        component-specific cleanup operations.
        """
        self.logger.info(f"Shutting down {self.__class__.__name__}")
        # Base implementation does nothing - subclasses can override
        pass
