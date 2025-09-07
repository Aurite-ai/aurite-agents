"""
Aurite Security Framework - Main Security Engine

This module provides the core orchestration engine for the Aurite Security Framework.
It coordinates security assessments across all component types (LLM, MCP, Agent, Workflow)
and provides a unified interface for security operations.

Architecture Design:
- Component-based security testing approach
- Extensible plugin architecture for security tools
- Real-time monitoring and alerting capabilities
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_security_tester import BaseSecurityTester
from .security_models import (
    ComponentSecurityConfig,
    SecurityAssessmentResult,
    SecurityConfig,
    SecurityLevel,
    SecurityStatus,
    SecurityThreat,
)

# Models have been moved to security_models.py

__all__ = ["SecurityEngine"]


class SecurityEngine:
    """
    Main orchestration engine for the Aurite Security Framework.

    This class coordinates security assessments across all component types
    and provides a unified interface for security operations.
    """

    def __init__(self, config: SecurityConfig):
        """
        Initialize the Security Engine.

        Args:
            config: Security configuration containing component settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._component_testers: Dict[str, BaseSecurityTester] = {}
        self._active_assessments: Dict[str, SecurityAssessmentResult] = {}
        self._executor = ThreadPoolExecutor(max_workers=config.max_concurrent_assessments)

        # Initialize component testers
        self._initialize_component_testers()

    def _initialize_component_testers(self) -> None:
        """Initialize security testers for each component type"""
        for component_type, component_config in self.config.components.items():
            if component_config.enabled:
                tester = self._create_component_tester(component_type, component_config)
                if tester:
                    self._component_testers[component_type] = tester
                    self.logger.info(f"Initialized {component_type} security tester")

    def _create_component_tester(
        self, component_type: str, config: ComponentSecurityConfig
    ) -> Optional[BaseSecurityTester]:
        """
        Create a security tester for the specified component type.

        This method uses a factory pattern to create appropriate testers
        based on component type. It's designed to be easily extensible.
        """
        # Import here to avoid circular dependencies
        try:
            if component_type == "llm":
                from .components.llm.llm_security_tester import LLMSecurityTester

                return LLMSecurityTester(config)
            elif component_type == "mcp":
                from ..components.mcp_security.mcp_security_tester import MCPSecurityTester  # type: ignore

                return MCPSecurityTester(config)
            elif component_type == "agent":
                from ..components.agent_security.agent_security_tester import AgentSecurityTester  # type: ignore

                return AgentSecurityTester(config)
            elif component_type == "workflow":
                from ..components.workflow_security.workflow_security_tester import (  # type: ignore
                    WorkflowSecurityTester,
                )

                return WorkflowSecurityTester(config)
            else:
                self.logger.warning(f"Unknown component type: {component_type}")
                return None
        except ImportError as e:
            self.logger.warning(f"Could not import tester for {component_type}: {e}")
            return None

    async def assess_component_security(
        self,
        component_type: str,
        component_id: str,
        component_config: Dict[str, Any],
        assessment_options: Optional[Dict[str, Any]] = None,
    ) -> SecurityAssessmentResult:
        """
        Perform security assessment on a specific component.

        Args:
            component_type: Type of component (llm, mcp, agent, workflow)
            component_id: Unique identifier for the component
            component_config: Component configuration to assess
            assessment_options: Optional assessment parameters

        Returns:
            SecurityAssessmentResult containing assessment results
        """
        assessment_id = f"{component_type}_{component_id}_{datetime.utcnow().isoformat()}"

        # Create assessment result
        result = SecurityAssessmentResult(
            assessment_id=assessment_id,
            component_type=component_type,
            component_id=component_id,
            status=SecurityStatus.PENDING,
            overall_score=0.0,
            threats=[],
            recommendations=[],
            test_results=[],
            metadata=assessment_options or {},
            started_at=datetime.utcnow(),
        )

        # Store active assessment
        self._active_assessments[assessment_id] = result

        try:
            # Get component tester
            tester = self._component_testers.get(component_type)
            if not tester:
                raise ValueError(f"No security tester available for component type: {component_type}")

            # Update status
            result.status = SecurityStatus.RUNNING
            self.logger.info(f"Starting security assessment: {assessment_id}")

            # Perform assessment
            assessment_result = await tester.assess_security(
                component_id=component_id, component_config=component_config, options=assessment_options or {}
            )

            # Update result with assessment findings
            # Convert threats from dicts to SecurityThreat objects if needed
            converted_threats = []
            for threat in assessment_result.threats:
                if isinstance(threat, SecurityThreat):
                    converted_threats.append(threat)
                elif isinstance(threat, dict):
                    # Convert dict to SecurityThreat object
                    # Handle severity conversion
                    severity = threat.get("severity", "LOW")
                    if isinstance(severity, str):
                        severity = SecurityLevel[severity.upper()]
                    elif not isinstance(severity, SecurityLevel):
                        severity = SecurityLevel.LOW

                    converted_threats.append(
                        SecurityThreat(
                            threat_id=threat.get("threat_id", ""),
                            threat_type=threat.get("threat_type", ""),
                            severity=severity,
                            component_type=threat.get("component_type", ""),
                            component_id=threat.get("component_id", ""),
                            description=threat.get("description", ""),
                            details=threat.get("details", {}),
                            mitigation_suggestions=threat.get("mitigation_suggestions", []),
                            detected_at=threat.get("detected_at", datetime.utcnow()),
                            confidence_score=threat.get("confidence_score", 0.0),
                            false_positive_likelihood=threat.get("false_positive_likelihood", 0.0),
                        )
                    )
            result.threats = converted_threats
            result.recommendations = assessment_result.recommendations
            result.overall_score = assessment_result.overall_score
            result.metadata.update(assessment_result.metadata)
            result.status = SecurityStatus.COMPLETED
            result.completed_at = datetime.utcnow()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

            self.logger.info(f"Completed security assessment: {assessment_id} (Score: {result.overall_score:.2f})")

        except Exception as e:
            result.status = SecurityStatus.FAILED
            result.completed_at = datetime.utcnow()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            self.logger.error(f"Security assessment failed: {assessment_id} - {str(e)}")

            # Add failure as a critical threat
            failure_threat = SecurityThreat(
                threat_id=f"assessment_failure_{assessment_id}",
                threat_type="assessment_failure",
                severity=SecurityLevel.CRITICAL,
                component_type=component_type,
                component_id=component_id,
                description=f"Security assessment failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                mitigation_suggestions=["Review component configuration", "Check security tool availability"],
            )
            result.add_threat(failure_threat)

        return result

    async def assess_full_configuration(
        self, configuration: Dict[str, Any], assessment_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, SecurityAssessmentResult]:
        """
        Perform comprehensive security assessment on a full configuration.

        This method assesses all components in a configuration and provides
        cross-component security analysis.

        Args:
            configuration: Full configuration to assess
            assessment_options: Optional assessment parameters

        Returns:
            Dictionary mapping component IDs to their assessment results
        """
        results = {}
        assessment_tasks = []

        # Create assessment tasks for each component
        for component_type, components in configuration.items():
            if component_type in self._component_testers:
                if isinstance(components, dict):
                    for component_id, component_config in components.items():
                        task = self.assess_component_security(
                            component_type=component_type,
                            component_id=component_id,
                            component_config=component_config,
                            assessment_options=assessment_options,
                        )
                        assessment_tasks.append((f"{component_type}_{component_id}", task))

        # Execute assessments concurrently
        if assessment_tasks:
            self.logger.info(f"Starting {len(assessment_tasks)} concurrent security assessments")

            # Wait for all assessments to complete
            for component_key, task in assessment_tasks:
                try:
                    result = await task
                    results[component_key] = result
                except Exception as e:
                    self.logger.error(f"Failed to complete assessment for {component_key}: {e}")

        # Perform cross-component analysis
        if len(results) > 1:
            cross_component_threats = await self._analyze_cross_component_threats(results)
            for threat in cross_component_threats:
                # Add cross-component threats to relevant results
                for result in results.values():
                    if result.component_type in threat.details.get("affected_components", []):
                        result.add_threat(threat)

        return results

    async def _analyze_cross_component_threats(
        self, results: Dict[str, SecurityAssessmentResult]
    ) -> List[SecurityThreat]:
        """
        Analyze potential security threats that span multiple components.

        This method looks for patterns and interactions between components
        that could create security vulnerabilities.
        """
        cross_component_threats = []

        # Example: Check for privilege escalation across components
        high_privilege_components = []
        for _component_key, result in results.items():
            for threat in result.threats:
                # Handle both SecurityThreat objects and dict representations
                if isinstance(threat, SecurityThreat):
                    threat_type = threat.threat_type
                elif isinstance(threat, dict):
                    threat_type = threat.get("threat_type", "")
                else:
                    continue

                if "privilege" in threat_type.lower():
                    high_privilege_components.append(result.component_type)

        if len(set(high_privilege_components)) > 1:
            threat = SecurityThreat(
                threat_id=f"cross_component_privilege_escalation_{datetime.utcnow().isoformat()}",
                threat_type="cross_component_privilege_escalation",
                severity=SecurityLevel.HIGH,
                component_type="cross_component",
                component_id="multiple",
                description="Multiple components with elevated privileges detected",
                details={
                    "affected_components": list(set(high_privilege_components)),
                    "risk": "Potential for privilege escalation across component boundaries",
                },
                mitigation_suggestions=[
                    "Review privilege requirements for each component",
                    "Implement principle of least privilege",
                    "Add inter-component access controls",
                ],
            )
            cross_component_threats.append(threat)

        return cross_component_threats

    def get_assessment_status(self, assessment_id: str) -> Optional[SecurityAssessmentResult]:
        """Get the status of a specific assessment"""
        return self._active_assessments.get(assessment_id)

    def get_active_assessments(self) -> Dict[str, SecurityAssessmentResult]:
        """Get all currently active assessments"""
        return {
            aid: result
            for aid, result in self._active_assessments.items()
            if result.status in [SecurityStatus.PENDING, SecurityStatus.RUNNING]
        }

    def get_completed_assessments(self) -> Dict[str, SecurityAssessmentResult]:
        """Get all completed assessments"""
        return {
            aid: result
            for aid, result in self._active_assessments.items()
            if result.status in [SecurityStatus.COMPLETED, SecurityStatus.FAILED]
        }

    async def cancel_assessment(self, assessment_id: str) -> bool:
        """Cancel a running assessment"""
        result = self._active_assessments.get(assessment_id)
        if result and result.status == SecurityStatus.RUNNING:
            result.status = SecurityStatus.CANCELLED
            result.completed_at = datetime.utcnow()
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            self.logger.info(f"Cancelled security assessment: {assessment_id}")
            return True
        return False

    def cleanup_old_assessments(self, max_age_hours: int = 24) -> int:
        """Clean up old assessment results"""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        old_assessments = []

        for assessment_id, result in self._active_assessments.items():
            if result.started_at.timestamp() < cutoff_time:
                old_assessments.append(assessment_id)

        for assessment_id in old_assessments:
            del self._active_assessments[assessment_id]

        self.logger.info(f"Cleaned up {len(old_assessments)} old assessments")
        return len(old_assessments)

    async def shutdown(self) -> None:
        """Shutdown the security engine and cleanup resources"""
        self.logger.info("Shutting down Security Engine")

        # Cancel all running assessments
        for assessment_id, result in self._active_assessments.items():
            if result.status == SecurityStatus.RUNNING:
                await self.cancel_assessment(assessment_id)

        # Shutdown executor
        self._executor.shutdown(wait=True)

        # Shutdown component testers
        for tester in self._component_testers.values():
            if hasattr(tester, "shutdown"):
                await tester.shutdown()

        self.logger.info("Security Engine shutdown complete")
