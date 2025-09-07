"""
Aurite Security Framework - LLM Security Tester

This module implements the LLM security tester that extends the base security tester
to provide comprehensive security assessment for Large Language Model components.

Features:
- Integration with LLM Guard for input/output scanning
- Real-time security assessment of LLM interactions
- Configuration security validation
- Threat detection and reporting
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from ....runners.llm_guard import LLMGuardBasic
from ...base_security_tester import BaseSecurityTester
from ...security_models import (
    ComponentSecurityConfig,
    SecurityTest,
    SecurityTestResult,
    SecurityTestType,
    ThreatCategory,
)


class LLMSecurityTester(BaseSecurityTester):
    """
    Security tester for Large Language Model components.

    This class extends BaseSecurityTester to provide LLM-specific security
    assessment capabilities for production use, including real-time scanning
    of inputs/outputs and configuration validation.
    """

    def __init__(self, config: ComponentSecurityConfig):
        """
        Initialize the LLM security tester.

        Args:
            config: LLM-specific security configuration
        """
        super().__init__(config)
        self.llm_guard = None
        self._initialize_llm_guard()

    def _initialize_llm_guard(self) -> None:
        """Initialize LLM Guard integration"""
        llm_guard_config = self.config.security_tools.get("llm_guard")
        if llm_guard_config and llm_guard_config.enabled:
            try:
                self.llm_guard = LLMGuardBasic(llm_guard_config.config)
                self.logger.info("LLM Guard integration initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM Guard: {str(e)}")
                self.llm_guard = None
        else:
            self.logger.warning("LLM Guard not configured or disabled")

    def _initialize_tests(self) -> None:
        """Initialize LLM-specific security tests"""

        # Configuration Security Tests
        self._security_tests["llm_config_audit"] = SecurityTest(
            test_id="llm_config_audit",
            test_name="LLM Configuration Security Audit",
            test_type=SecurityTestType.CONFIGURATION_AUDIT,
            category=ThreatCategory.CONFIGURATION_ERROR,
            description="Audit LLM configuration for security issues",
            enabled=True,
            severity_weight=1.5,
            timeout_seconds=15,
        )

        # Performance Impact Tests
        self._security_tests["token_limit_check"] = SecurityTest(
            test_id="token_limit_check",
            test_name="Token Limit Security Check",
            test_type=SecurityTestType.STATIC_ANALYSIS,
            category=ThreatCategory.PERFORMANCE_IMPACT,
            description="Check for excessive token usage that could impact performance or cost",
            enabled=True,
            severity_weight=0.5,
            timeout_seconds=10,
        )

        # Input/Output Security Assessment
        self._security_tests["input_security_scan"] = SecurityTest(
            test_id="input_security_scan",
            test_name="Input Security Scanning",
            test_type=SecurityTestType.DYNAMIC_ANALYSIS,
            category=ThreatCategory.INJECTION,
            description="Scan LLM inputs for security threats",
            enabled=True,
            severity_weight=2.0,
            timeout_seconds=30,
        )

        self._security_tests["output_security_scan"] = SecurityTest(
            test_id="output_security_scan",
            test_name="Output Security Scanning",
            test_type=SecurityTestType.DYNAMIC_ANALYSIS,
            category=ThreatCategory.DATA_LEAKAGE,
            description="Scan LLM outputs for security issues",
            enabled=True,
            severity_weight=2.0,
            timeout_seconds=30,
        )

    async def _execute_test(
        self, test: SecurityTest, component_id: str, component_config: Dict[str, Any], options: Dict[str, Any]
    ) -> SecurityTestResult:
        """
        Execute a specific LLM security test.

        Args:
            test: The security test to execute
            component_id: Unique identifier for the LLM component
            component_config: LLM configuration to test
            options: Additional test options (may include inputs/outputs to scan)

        Returns:
            SecurityTestResult containing the test results
        """
        start_time = datetime.utcnow()

        try:
            # Execute test based on test ID
            if test.test_id == "llm_config_audit":
                result = await self._audit_llm_configuration(component_config, options)
            elif test.test_id == "token_limit_check":
                result = await self._check_token_limits(component_config, options)
            elif test.test_id == "input_security_scan":
                result = await self._scan_inputs_for_threats(component_config, options)
            elif test.test_id == "output_security_scan":
                result = await self._scan_outputs_for_threats(component_config, options)
            else:
                # Unknown test
                result = SecurityTestResult(
                    test_id=test.test_id,
                    test_name=test.test_name,
                    passed=False,
                    score=0.0,
                    threats_detected=[],
                    recommendations=[f"Test {test.test_id} not implemented"],
                    execution_time_seconds=0.0,
                    error_message=f"Unknown test: {test.test_id}",
                )

            # Calculate execution time
            end_time = datetime.utcnow()
            result.execution_time_seconds = (end_time - start_time).total_seconds()

            return result

        except asyncio.TimeoutError:
            return SecurityTestResult(
                test_id=test.test_id,
                test_name=test.test_name,
                passed=False,
                score=0.0,
                threats_detected=[],
                recommendations=[f"Test timed out after {test.timeout_seconds} seconds"],
                execution_time_seconds=test.timeout_seconds,
                error_message="Test execution timed out",
            )
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()

            return SecurityTestResult(
                test_id=test.test_id,
                test_name=test.test_name,
                passed=False,
                score=0.0,
                threats_detected=[],
                recommendations=[f"Test failed with error: {str(e)}"],
                execution_time_seconds=execution_time,
                error_message=str(e),
            )

    async def _audit_llm_configuration(
        self, component_config: Dict[str, Any], options: Dict[str, Any]
    ) -> SecurityTestResult:
        """Audit LLM configuration for security issues"""
        threats_detected = []
        recommendations = []

        # Check for common configuration issues
        if not component_config.get("temperature"):
            threats_detected.append(
                {
                    "type": "config_missing",
                    "severity": "low",
                    "description": "Temperature parameter not configured",
                    "details": {"parameter": "temperature"},
                }
            )
            recommendations.append("Consider setting temperature parameter for consistent behavior")

        if component_config.get("temperature", 0) > 1.5:
            threats_detected.append(
                {
                    "type": "config_risk",
                    "severity": "medium",
                    "description": "High temperature setting may lead to unpredictable outputs",
                    "details": {"temperature": component_config.get("temperature")},
                }
            )
            recommendations.append("Consider lowering temperature for more predictable outputs")

        if not component_config.get("max_tokens"):
            threats_detected.append(
                {
                    "type": "config_missing",
                    "severity": "medium",
                    "description": "Max tokens not configured - could lead to excessive resource usage",
                    "details": {"parameter": "max_tokens"},
                }
            )
            recommendations.append("Set max_tokens to prevent excessive resource usage")

        # Check for insecure API configurations
        api_base = component_config.get("api_base")
        if api_base and not api_base.startswith("https://"):
            threats_detected.append(
                {
                    "type": "insecure_connection",
                    "severity": "high",
                    "description": "API base URL does not use HTTPS",
                    "details": {"api_base": api_base},
                }
            )
            recommendations.append("Use HTTPS for API connections to ensure secure communication")

        # Calculate score based on number and severity of issues
        score = 1.0
        for threat in threats_detected:
            severity = threat.get("severity", "low")
            if severity == "critical":
                score -= 0.4
            elif severity == "high":
                score -= 0.3
            elif severity == "medium":
                score -= 0.2
            elif severity == "low":
                score -= 0.1

        score = max(0.0, score)

        return SecurityTestResult(
            test_id="llm_config_audit",
            test_name="LLM Configuration Security Audit",
            passed=len(threats_detected) == 0,
            score=score,
            threats_detected=threats_detected,
            recommendations=recommendations if recommendations else ["LLM configuration looks secure"],
            execution_time_seconds=0.0,
            metadata={"config_issues_found": len(threats_detected)},
        )

    async def _check_token_limits(
        self, component_config: Dict[str, Any], options: Dict[str, Any]
    ) -> SecurityTestResult:
        """Check for token limit configuration and potential issues"""
        threats_detected = []
        recommendations = []

        max_tokens = component_config.get("max_tokens")
        if not max_tokens:
            threats_detected.append(
                {
                    "type": "performance_risk",
                    "severity": "medium",
                    "description": "No token limit configured - could lead to excessive resource usage",
                    "details": {"issue": "unlimited_tokens"},
                }
            )
            recommendations.append("Configure max_tokens to prevent excessive resource usage and costs")
        elif max_tokens > 8000:
            threats_detected.append(
                {
                    "type": "performance_risk",
                    "severity": "low",
                    "description": f"Very high token limit configured: {max_tokens}",
                    "details": {"max_tokens": max_tokens},
                }
            )
            recommendations.append("Consider if such a high token limit is necessary for your use case")
        elif max_tokens > 4000:
            threats_detected.append(
                {
                    "type": "performance_risk",
                    "severity": "low",
                    "description": f"High token limit configured: {max_tokens}",
                    "details": {"max_tokens": max_tokens},
                }
            )
            recommendations.append("Monitor token usage to ensure cost efficiency")

        score = 1.0 if len(threats_detected) == 0 else max(0.5, 1.0 - (len(threats_detected) * 0.2))

        return SecurityTestResult(
            test_id="token_limit_check",
            test_name="Token Limit Security Check",
            passed=len(threats_detected) == 0,
            score=score,
            threats_detected=threats_detected,
            recommendations=recommendations if recommendations else ["Token limits are appropriately configured"],
            execution_time_seconds=0.0,
            metadata={"max_tokens": max_tokens},
        )

    async def _scan_inputs_for_threats(
        self, component_config: Dict[str, Any], options: Dict[str, Any]
    ) -> SecurityTestResult:
        """Scan provided inputs for security threats"""
        threats_detected = []
        recommendations = []

        # Get inputs to scan from options
        inputs_to_scan = options.get("inputs", [])
        if not inputs_to_scan:
            return SecurityTestResult(
                test_id="input_security_scan",
                test_name="Input Security Scanning",
                passed=True,
                score=1.0,
                threats_detected=[],
                recommendations=["No inputs provided for scanning"],
                execution_time_seconds=0.0,
                metadata={"inputs_scanned": 0},
            )

        if not self.llm_guard:
            return SecurityTestResult(
                test_id="input_security_scan",
                test_name="Input Security Scanning",
                passed=False,
                score=0.0,
                threats_detected=[],
                recommendations=["LLM Guard not available - cannot perform input security scanning"],
                execution_time_seconds=0.0,
                error_message="LLM Guard integration not available",
            )

        total_inputs = len(inputs_to_scan)
        threats_found = 0

        for i, input_text in enumerate(inputs_to_scan):
            try:
                scan_result = await self.llm_guard.scan_input(input_text)

                if not scan_result["valid"]:
                    threats_found += 1
                    for threat in scan_result["threats"]:
                        threat_type = threat.get("type", "unknown")
                        severity = self._map_threat_severity(threat_type)

                        threats_detected.append(
                            {
                                "type": f"input_{threat_type}",
                                "severity": severity,
                                "description": f"Security threat detected in input {i + 1}: {threat_type}",
                                "details": {
                                    "input_index": i,
                                    "threat_details": threat.get("details", {}),
                                    "confidence": scan_result.get("score", 0.0),
                                },
                            }
                        )

            except Exception as e:
                self.logger.error(f"Error scanning input {i}: {e}")
                threats_detected.append(
                    {
                        "type": "scan_error",
                        "severity": "medium",
                        "description": f"Failed to scan input {i + 1}",
                        "details": {"error": str(e)},
                    }
                )

        # Generate recommendations based on findings
        if threats_found > 0:
            threat_rate = threats_found / total_inputs
            if threat_rate > 0.5:
                recommendations.append("High rate of threats detected in inputs. Implement stronger input validation.")
            elif threat_rate > 0.2:
                recommendations.append("Moderate threat rate detected. Consider additional input filtering.")
            else:
                recommendations.append("Some threats detected in inputs. Monitor input patterns.")
        else:
            recommendations.append("No security threats detected in provided inputs.")

        # Balanced scoring algorithm - practical for real-world prompt variability
        threat_rate = threats_found / total_inputs if total_inputs > 0 else 0

        # Check for critical threats and educational context
        has_critical_threats = any(threat.get("severity") == "critical" for threat in threats_detected)
        has_high_threats = any(threat.get("severity") == "high" for threat in threats_detected)

        # More lenient scoring focused on intent rather than strict pattern matching
        if has_critical_threats:
            # Only truly critical threats (like real secrets) drop score significantly
            score = max(0.0, 0.6 - (threat_rate * 0.2))
        elif has_high_threats and threat_rate > 0.4:
            # High threat rate with high severity threats
            score = max(0.0, 0.7 - (threat_rate * 0.3))
        elif threat_rate > 0.5:
            # Very high threat rate
            score = max(0.0, 0.8 - (threat_rate * 0.2))
        elif threat_rate > 0.2:
            # Moderate threat rate
            score = max(0.0, 0.9 - (threat_rate * 0.3))
        else:
            # Low threat rate
            score = max(0.0, 1.0 - (threat_rate * 0.4))

        return SecurityTestResult(
            test_id="input_security_scan",
            test_name="Input Security Scanning",
            passed=threats_found == 0,
            score=score,
            threats_detected=threats_detected,
            recommendations=recommendations,
            execution_time_seconds=0.0,
            metadata={
                "inputs_scanned": total_inputs,
                "threats_found": threats_found,
                "threat_rate": threat_rate,
            },
        )

    async def _scan_outputs_for_threats(
        self, component_config: Dict[str, Any], options: Dict[str, Any]
    ) -> SecurityTestResult:
        """Scan provided outputs for security threats"""
        threats_detected = []
        recommendations = []

        # Get outputs to scan from options
        outputs_to_scan = options.get("outputs", [])
        if not outputs_to_scan:
            return SecurityTestResult(
                test_id="output_security_scan",
                test_name="Output Security Scanning",
                passed=True,
                score=1.0,
                threats_detected=[],
                recommendations=["No outputs provided for scanning"],
                execution_time_seconds=0.0,
                metadata={"outputs_scanned": 0},
            )

        if not self.llm_guard:
            return SecurityTestResult(
                test_id="output_security_scan",
                test_name="Output Security Scanning",
                passed=False,
                score=0.0,
                threats_detected=[],
                recommendations=["LLM Guard not available - cannot perform output security scanning"],
                execution_time_seconds=0.0,
                error_message="LLM Guard integration not available",
            )

        total_outputs = len(outputs_to_scan)
        threats_found = 0

        for i, output_text in enumerate(outputs_to_scan):
            try:
                scan_result = await self.llm_guard.scan_output(output_text)

                if not scan_result["valid"]:
                    threats_found += 1
                    for threat in scan_result["threats"]:
                        threat_type = threat.get("type", "unknown")
                        severity = self._map_threat_severity(threat_type)

                        threats_detected.append(
                            {
                                "type": f"output_{threat_type}",
                                "severity": severity,
                                "description": f"Security threat detected in output {i + 1}: {threat_type}",
                                "details": {
                                    "output_index": i,
                                    "threat_details": threat.get("details", {}),
                                    "confidence": scan_result.get("score", 0.0),
                                },
                            }
                        )

            except Exception as e:
                self.logger.error(f"Error scanning output {i}: {e}")
                threats_detected.append(
                    {
                        "type": "scan_error",
                        "severity": "medium",
                        "description": f"Failed to scan output {i + 1}",
                        "details": {"error": str(e)},
                    }
                )

        # Generate recommendations based on findings
        if threats_found > 0:
            threat_rate = threats_found / total_outputs
            if threat_rate > 0.3:
                recommendations.append("High rate of threats in outputs. Review LLM behavior and add output filtering.")
            elif threat_rate > 0.1:
                recommendations.append("Some threats detected in outputs. Consider additional safety measures.")
            else:
                recommendations.append("Few threats detected in outputs. Monitor output patterns.")
        else:
            recommendations.append("No security threats detected in provided outputs.")

        # Balanced scoring algorithm - practical for real-world output variability (same as input)
        threat_rate = threats_found / total_outputs if total_outputs > 0 else 0

        # Check for critical threats and educational context
        has_critical_threats = any(threat.get("severity") == "critical" for threat in threats_detected)
        has_high_threats = any(threat.get("severity") == "high" for threat in threats_detected)

        # More lenient scoring focused on intent rather than strict pattern matching
        if has_critical_threats:
            # Only truly critical threats (like real secrets) drop score significantly
            score = max(0.0, 0.6 - (threat_rate * 0.2))
        elif has_high_threats and threat_rate > 0.4:
            # High threat rate with high severity threats
            score = max(0.0, 0.7 - (threat_rate * 0.3))
        elif threat_rate > 0.5:
            # Very high threat rate
            score = max(0.0, 0.8 - (threat_rate * 0.2))
        elif threat_rate > 0.2:
            # Moderate threat rate
            score = max(0.0, 0.9 - (threat_rate * 0.3))
        else:
            # Low threat rate
            score = max(0.0, 1.0 - (threat_rate * 0.4))

        return SecurityTestResult(
            test_id="output_security_scan",
            test_name="Output Security Scanning",
            passed=threats_found == 0,
            score=score,
            threats_detected=threats_detected,
            recommendations=recommendations,
            execution_time_seconds=0.0,
            metadata={
                "outputs_scanned": total_outputs,
                "threats_found": threats_found,
                "threat_rate": threat_rate,
            },
        )

    def _map_threat_severity(self, threat_type: str) -> str:
        """Map threat types to severity levels"""
        severity_mapping = {
            "prompt_injection": "high",
            "secrets": "critical",
            "pii": "high",
            "toxicity": "medium",
            "bias": "medium",
            "malicious_urls": "high",
            "sensitive": "medium",
        }
        return severity_mapping.get(threat_type.lower(), "medium")

    async def scan_input(self, input_text: str) -> Dict[str, Any]:
        """
        Scan a single input for security threats.

        Args:
            input_text: The input text to scan

        Returns:
            Dictionary containing scan results
        """
        if not self.llm_guard:
            return {"valid": False, "error": "LLM Guard not available", "threats": [], "score": 0.0}

        try:
            return await self.llm_guard.scan_input(input_text)
        except Exception as e:
            self.logger.error(f"Error scanning input: {e}")
            return {"valid": False, "error": str(e), "threats": [], "score": 0.0}

    async def scan_output(self, output_text: str) -> Dict[str, Any]:
        """
        Scan a single output for security threats.

        Args:
            output_text: The output text to scan

        Returns:
            Dictionary containing scan results
        """
        if not self.llm_guard:
            return {"valid": False, "error": "LLM Guard not available", "threats": [], "score": 0.0}

        try:
            return await self.llm_guard.scan_output(output_text)
        except Exception as e:
            self.logger.error(f"Error scanning output: {e}")
            return {"valid": False, "error": str(e), "threats": [], "score": 0.0}

    def get_component_type(self) -> str:
        """Get the component type this tester handles"""
        return "llm"

    async def validate_component_config(self, component_config: Dict[str, Any]) -> List[str]:
        """Validate LLM component configuration"""
        errors = await super().validate_component_config(component_config)

        # LLM-specific validation
        if "provider" not in component_config:
            errors.append("LLM provider must be specified")

        if "model" not in component_config:
            errors.append("LLM model must be specified")

        # Validate temperature if present
        temperature = component_config.get("temperature")
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                errors.append("Temperature must be a number")
            elif temperature < 0 or temperature > 2:
                errors.append("Temperature must be between 0 and 2")

        # Validate max_tokens if present
        max_tokens = component_config.get("max_tokens")
        if max_tokens is not None:
            if not isinstance(max_tokens, int):
                errors.append("max_tokens must be an integer")
            elif max_tokens <= 0:
                errors.append("max_tokens must be greater than 0")

        return errors

    def _get_component_specific_recommendations(
        self, test_results: List[SecurityTestResult], threats: List[Dict[str, Any]], options: Dict[str, Any]
    ) -> List[str]:
        """Generate LLM-specific security recommendations"""
        recommendations = super()._get_component_specific_recommendations(test_results, threats, options)

        # Analyze test results for specific recommendations
        config_tests = [r for r in test_results if "config" in r.test_id]
        if any(not r.passed for r in config_tests):
            recommendations.append("Review and secure LLM configuration parameters")

        input_tests = [r for r in test_results if "input" in r.test_id]
        if any(not r.passed for r in input_tests):
            recommendations.append("Implement stronger input validation and filtering")

        output_tests = [r for r in test_results if "output" in r.test_id]
        if any(not r.passed for r in output_tests):
            recommendations.append("Add output filtering and content moderation")

        # Check for specific threat types
        threat_types = [t.get("type", "") for t in threats]
        if any("prompt_injection" in t for t in threat_types):
            recommendations.append("Strengthen prompt injection defenses")
        if any("secrets" in t for t in threat_types):
            recommendations.append("Implement secrets detection and redaction")
        if any("toxicity" in t for t in threat_types):
            recommendations.append("Add toxicity filtering and content moderation")

        return recommendations
