"""
Integration tests for the Security Engine.

This module tests the SecurityEngine functionality, including security assessments,
threat detection, cross-component analysis, and error handling.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from aurite.testing.security.security_engine import SecurityEngine
from aurite.testing.security.security_models import (
    SecurityAssessmentResult,
    SecurityLevel,
    SecurityStatus,
    SecurityThreat,
)

# Import fixtures
from tests.fixtures.security_fixtures import (
    assert_assessment_result_valid,
    assert_threat_valid,
    create_agent_config,
    create_llm_config,
)


@pytest.mark.anyio
@pytest.mark.testing
class TestSecurityEngine:
    """Test suite for the SecurityEngine class."""

    async def test_engine_initialization(self, security_config):
        """Test SecurityEngine initialization with configuration."""
        engine = SecurityEngine(security_config)

        assert engine.config == security_config
        assert engine._component_testers is not None
        assert engine._active_assessments == {}

        # Check that LLM tester was initialized (others may fail due to missing imports)
        assert "llm" in engine._component_testers

    async def test_basic_component_assessment(self, security_config):
        """Test basic security assessment of a component."""
        engine = SecurityEngine(security_config)

        # Create a mock tester
        mock_tester = AsyncMock()
        mock_tester.assess_security.return_value = SecurityAssessmentResult(
            assessment_id="test_assessment",
            component_type="llm",
            component_id="test_llm",
            status=SecurityStatus.COMPLETED,
            overall_score=8.5,
            threats=[],
            recommendations=["All good"],
            test_results=[],
            metadata={},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=5.0,
        )

        # Replace the LLM tester with our mock
        engine._component_testers["llm"] = mock_tester

        # Run assessment
        result = await engine.assess_component_security(
            component_type="llm",
            component_id="test_llm",
            component_config=create_llm_config(),
        )

        # Verify result
        assert_assessment_result_valid(result)
        assert result.component_type == "llm"
        assert result.component_id == "test_llm"
        assert result.status == SecurityStatus.COMPLETED
        assert result.overall_score == 8.5

        # Verify the tester was called
        mock_tester.assess_security.assert_called_once()

    async def test_assessment_with_threats_detected(self, security_config, sample_threats):
        """Test security assessment that detects threats."""
        engine = SecurityEngine(security_config)

        # Create a mock tester that returns threats
        mock_tester = AsyncMock()
        mock_tester.assess_security.return_value = SecurityAssessmentResult(
            assessment_id="test_assessment",
            component_type="llm",
            component_id="test_llm",
            status=SecurityStatus.COMPLETED,
            overall_score=3.5,
            threats=sample_threats,
            recommendations=[
                "Implement input validation",
                "Use prompt guards",
                "Implement data masking",
            ],
            test_results=[],
            metadata={},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=5.0,
        )

        engine._component_testers["llm"] = mock_tester

        # Run assessment
        result = await engine.assess_component_security(
            component_type="llm",
            component_id="test_llm",
            component_config=create_llm_config(),
        )

        # Verify threats were detected
        assert_assessment_result_valid(result)
        assert len(result.threats) == 3
        assert result.overall_score == 3.5

        # Check threat details
        for threat in result.threats:
            assert_threat_valid(threat)

        # Check threat severities
        severities = [t.severity for t in result.threats]
        assert SecurityLevel.HIGH in severities
        assert SecurityLevel.MEDIUM in severities
        assert SecurityLevel.LOW in severities

    async def test_assessment_with_critical_threats(self, security_config, critical_threats):
        """Test security assessment with critical threats."""
        engine = SecurityEngine(security_config)

        # Create a mock tester that returns critical threats
        mock_tester = AsyncMock()
        mock_tester.assess_security.return_value = SecurityAssessmentResult(
            assessment_id="test_assessment",
            component_type="agent",
            component_id="malicious_agent",
            status=SecurityStatus.COMPLETED,
            overall_score=1.0,
            threats=critical_threats,
            recommendations=["CRITICAL: Enable sandboxing immediately"],
            test_results=[],
            metadata={"critical": True},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=5.0,
        )

        engine._component_testers["agent"] = mock_tester

        # Run assessment
        result = await engine.assess_component_security(
            component_type="agent",
            component_id="malicious_agent",
            component_config=create_agent_config(),
        )

        # Verify critical threats
        assert_assessment_result_valid(result)
        assert len(result.threats) == 2
        assert result.overall_score == 1.0

        # Check all threats are critical
        for threat in result.threats:
            assert threat.severity == SecurityLevel.CRITICAL
            assert threat.confidence_score > 0.9

    async def test_assessment_with_invalid_component_type(self, security_config):
        """Test assessment with invalid component type."""
        engine = SecurityEngine(security_config)

        # Try to assess unknown component type
        result = await engine.assess_component_security(
            component_type="unknown_type",
            component_id="test_id",
            component_config={},
        )

        # Should fail gracefully
        assert_assessment_result_valid(result)
        assert result.status == SecurityStatus.FAILED
        assert len(result.threats) == 1
        assert result.threats[0].severity == SecurityLevel.CRITICAL
        assert "No security tester available" in result.threats[0].description

    async def test_assessment_with_tester_exception(self, security_config):
        """Test assessment when tester raises an exception."""
        engine = SecurityEngine(security_config)

        # Create a mock tester that raises an exception
        mock_tester = AsyncMock()
        mock_tester.assess_security.side_effect = RuntimeError("Test error")

        engine._component_testers["llm"] = mock_tester

        # Run assessment
        result = await engine.assess_component_security(
            component_type="llm",
            component_id="test_llm",
            component_config=create_llm_config(),
        )

        # Should handle error gracefully
        assert_assessment_result_valid(result)
        assert result.status == SecurityStatus.FAILED
        assert len(result.threats) == 1
        assert result.threats[0].severity == SecurityLevel.CRITICAL
        assert "Test error" in result.threats[0].description

    async def test_full_configuration_assessment(self, security_config):
        """Test assessment of a full configuration with multiple components."""
        engine = SecurityEngine(security_config)

        # Create mock testers for different component types
        mock_llm_tester = AsyncMock()
        mock_llm_tester.assess_security.return_value = SecurityAssessmentResult(
            assessment_id="llm_assessment",
            component_type="llm",
            component_id="primary_llm",
            status=SecurityStatus.COMPLETED,
            overall_score=8.0,
            threats=[],
            recommendations=[],
            test_results=[],
            metadata={},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=3.0,
        )

        mock_agent_tester = AsyncMock()
        mock_agent_tester.assess_security.return_value = SecurityAssessmentResult(
            assessment_id="agent_assessment",
            component_type="agent",
            component_id="main_agent",
            status=SecurityStatus.COMPLETED,
            overall_score=7.5,
            threats=[],
            recommendations=[],
            test_results=[],
            metadata={},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=4.0,
        )

        engine._component_testers["llm"] = mock_llm_tester
        engine._component_testers["agent"] = mock_agent_tester

        # Create full configuration
        configuration = {
            "llm": {
                "primary_llm": create_llm_config(),
                "secondary_llm": create_llm_config(),
            },
            "agent": {
                "main_agent": create_agent_config(),
            },
        }

        # Run full assessment
        results = await engine.assess_full_configuration(configuration)

        # Verify results
        assert len(results) == 3
        assert "llm_primary_llm" in results
        assert "llm_secondary_llm" in results
        assert "agent_main_agent" in results

        for result in results.values():
            assert_assessment_result_valid(result)
            assert result.status == SecurityStatus.COMPLETED

    async def test_cross_component_threat_analysis(self, security_config):
        """Test cross-component threat analysis."""
        engine = SecurityEngine(security_config)

        # Create mock testers that return privilege-related threats
        privilege_threat = SecurityThreat(
            threat_id="priv_001",
            threat_type="privilege_escalation",
            severity=SecurityLevel.HIGH,
            component_type="llm",
            component_id="test_llm",
            description="Elevated privileges detected",
            details={},
            mitigation_suggestions=[],
        )

        mock_llm_tester = AsyncMock()
        mock_llm_tester.assess_security.return_value = SecurityAssessmentResult(
            assessment_id="llm_assessment",
            component_type="llm",
            component_id="test_llm",
            status=SecurityStatus.COMPLETED,
            overall_score=5.0,
            threats=[privilege_threat],
            recommendations=[],
            test_results=[],
            metadata={},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=3.0,
        )

        mock_agent_tester = AsyncMock()
        mock_agent_tester.assess_security.return_value = SecurityAssessmentResult(
            assessment_id="agent_assessment",
            component_type="agent",
            component_id="test_agent",
            status=SecurityStatus.COMPLETED,
            overall_score=5.0,
            threats=[privilege_threat],
            recommendations=[],
            test_results=[],
            metadata={},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=3.0,
        )

        engine._component_testers["llm"] = mock_llm_tester
        engine._component_testers["agent"] = mock_agent_tester

        # Create configuration with multiple components
        configuration = {
            "llm": {"test_llm": create_llm_config()},
            "agent": {"test_agent": create_agent_config()},
        }

        # Run full assessment
        results = await engine.assess_full_configuration(configuration)

        # Check for cross-component threats
        cross_component_threats_found = False
        for result in results.values():
            for threat in result.threats:
                if "cross_component" in threat.threat_type:
                    cross_component_threats_found = True
                    assert threat.severity == SecurityLevel.HIGH
                    # Check for either "privilege escalation" or "elevated privileges"
                    assert (
                        "privilege" in threat.description.lower()
                        or "privilege escalation" in threat.description.lower()
                    )

        assert cross_component_threats_found

    async def test_assessment_status_tracking(self, security_config):
        """Test tracking of assessment status."""
        engine = SecurityEngine(security_config)

        # Create a mock tester with delayed response
        mock_tester = AsyncMock()

        async def delayed_assessment(*args, **kwargs):
            # Simulate processing time
            import asyncio

            await asyncio.sleep(0.1)
            return SecurityAssessmentResult(
                assessment_id="test_assessment",
                component_type="llm",
                component_id="test_llm",
                status=SecurityStatus.COMPLETED,
                overall_score=8.0,
                threats=[],
                recommendations=[],
                test_results=[],
                metadata={},
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=0.1,
            )

        mock_tester.assess_security = delayed_assessment
        engine._component_testers["llm"] = mock_tester

        # Start assessment
        import asyncio

        assessment_task = asyncio.create_task(
            engine.assess_component_security(
                component_type="llm",
                component_id="test_llm",
                component_config=create_llm_config(),
            )
        )

        # Check active assessments (should be running)
        await asyncio.sleep(0.05)  # Let it start
        active = engine.get_active_assessments()
        assert len(active) > 0

        # Wait for completion
        result = await assessment_task

        # Check completed assessments
        completed = engine.get_completed_assessments()
        assert len(completed) > 0
        assert result.assessment_id in completed

    async def test_cancel_assessment(self, security_config):
        """Test cancelling a running assessment."""
        engine = SecurityEngine(security_config)

        # Create a mock tester with very long delay
        mock_tester = AsyncMock()

        async def long_running_assessment(*args, **kwargs):
            import asyncio

            await asyncio.sleep(10)  # Very long delay
            return SecurityAssessmentResult(
                assessment_id="test_assessment",
                component_type="llm",
                component_id="test_llm",
                status=SecurityStatus.COMPLETED,
                overall_score=8.0,
                threats=[],
                recommendations=[],
                test_results=[],
                metadata={},
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=10.0,
            )

        mock_tester.assess_security = long_running_assessment
        engine._component_testers["llm"] = mock_tester

        # Start assessment
        import asyncio

        assessment_task = asyncio.create_task(
            engine.assess_component_security(
                component_type="llm",
                component_id="test_llm",
                component_config=create_llm_config(),
            )
        )

        # Let it start
        await asyncio.sleep(0.1)

        # Get the assessment ID
        active = engine.get_active_assessments()
        assessment_id = list(active.keys())[0] if active else None

        if assessment_id:
            # Cancel the assessment
            cancelled = await engine.cancel_assessment(assessment_id)
            assert cancelled

            # Check status
            result = engine.get_assessment_status(assessment_id)
            if result:
                assert result.status == SecurityStatus.CANCELLED

        # Cancel the task to clean up
        assessment_task.cancel()
        try:
            await assessment_task
        except asyncio.CancelledError:
            pass

    async def test_cleanup_old_assessments(self, security_config):
        """Test cleanup of old assessment results."""
        engine = SecurityEngine(security_config)

        # Add some old assessments
        old_assessment = SecurityAssessmentResult(
            assessment_id="old_assessment",
            component_type="llm",
            component_id="old_llm",
            status=SecurityStatus.COMPLETED,
            overall_score=7.0,
            threats=[],
            recommendations=[],
            test_results=[],
            metadata={},
            started_at=datetime(2020, 1, 1),  # Very old
            completed_at=datetime(2020, 1, 1),
            duration_seconds=5.0,
        )

        recent_assessment = SecurityAssessmentResult(
            assessment_id="recent_assessment",
            component_type="llm",
            component_id="recent_llm",
            status=SecurityStatus.COMPLETED,
            overall_score=8.0,
            threats=[],
            recommendations=[],
            test_results=[],
            metadata={},
            started_at=datetime.utcnow(),  # Recent
            completed_at=datetime.utcnow(),
            duration_seconds=5.0,
        )

        engine._active_assessments["old_assessment"] = old_assessment
        engine._active_assessments["recent_assessment"] = recent_assessment

        # Clean up old assessments
        cleaned = engine.cleanup_old_assessments(max_age_hours=24)

        # Old assessment should be removed
        assert cleaned == 1
        assert "old_assessment" not in engine._active_assessments
        assert "recent_assessment" in engine._active_assessments

    async def test_engine_shutdown(self, security_config):
        """Test engine shutdown and cleanup."""
        engine = SecurityEngine(security_config)

        # Add a mock tester with shutdown method
        mock_tester = AsyncMock()
        mock_tester.shutdown = AsyncMock()
        engine._component_testers["llm"] = mock_tester

        # Add an active assessment
        active_assessment = SecurityAssessmentResult(
            assessment_id="active_assessment",
            component_type="llm",
            component_id="test_llm",
            status=SecurityStatus.RUNNING,
            overall_score=0.0,
            threats=[],
            recommendations=[],
            test_results=[],
            metadata={},
            started_at=datetime.utcnow(),
        )
        engine._active_assessments["active_assessment"] = active_assessment

        # Shutdown the engine
        await engine.shutdown()

        # Verify tester shutdown was called
        mock_tester.shutdown.assert_called_once()

        # Verify active assessment was cancelled
        assert active_assessment.status == SecurityStatus.CANCELLED

    async def test_assessment_with_options(self, security_config):
        """Test assessment with custom options."""
        engine = SecurityEngine(security_config)

        # Create a mock tester that uses options
        mock_tester = AsyncMock()

        async def assessment_with_options(component_id, component_config, options):
            # Use options to determine behavior
            if options.get("strict_mode"):
                score = 5.0
                threats = [
                    SecurityThreat(
                        threat_id="strict_001",
                        threat_type="configuration_error",
                        severity=SecurityLevel.MEDIUM,
                        component_type="llm",
                        component_id=component_id,
                        description="Strict mode violation",
                        details={"option": "strict_mode"},
                        mitigation_suggestions=[],
                    )
                ]
            else:
                score = 9.0
                threats = []

            return SecurityAssessmentResult(
                assessment_id="test_assessment",
                component_type="llm",
                component_id=component_id,
                status=SecurityStatus.COMPLETED,
                overall_score=score,
                threats=threats,
                recommendations=[],
                test_results=[],
                metadata=options,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=2.0,
            )

        mock_tester.assess_security = assessment_with_options
        engine._component_testers["llm"] = mock_tester

        # Run assessment with strict mode
        result_strict = await engine.assess_component_security(
            component_type="llm",
            component_id="test_llm",
            component_config=create_llm_config(),
            assessment_options={"strict_mode": True},
        )

        assert result_strict.overall_score == 5.0
        assert len(result_strict.threats) == 1
        assert result_strict.metadata["strict_mode"] is True

        # Run assessment without strict mode
        result_normal = await engine.assess_component_security(
            component_type="llm",
            component_id="test_llm",
            component_config=create_llm_config(),
            assessment_options={"strict_mode": False},
        )

        assert result_normal.overall_score == 9.0
        assert len(result_normal.threats) == 0
        assert result_normal.metadata["strict_mode"] is False


@pytest.mark.anyio
@pytest.mark.testing
class TestSecurityModels:
    """Test suite for Security model classes."""

    def test_security_assessment_result_methods(self, sample_assessment_result):
        """Test SecurityAssessmentResult methods."""
        # Test get_threats_by_severity
        high_threats = sample_assessment_result.get_threats_by_severity(SecurityLevel.HIGH)
        assert len(high_threats) == 1
        assert high_threats[0].threat_type == "prompt_injection"

        medium_threats = sample_assessment_result.get_threats_by_severity(SecurityLevel.MEDIUM)
        assert len(medium_threats) == 1
        assert medium_threats[0].threat_type == "data_leakage"

        # Test get_critical_threats
        critical_threats = sample_assessment_result.get_critical_threats()
        assert len(critical_threats) == 0  # No critical threats in sample

        # Test has_critical_threats
        assert not sample_assessment_result.has_critical_threats()

    def test_security_assessment_with_critical_threats(self, failed_assessment_result):
        """Test SecurityAssessmentResult with critical threats."""
        # Test get_critical_threats
        critical_threats = failed_assessment_result.get_critical_threats()
        assert len(critical_threats) == 2

        # Test has_critical_threats
        assert failed_assessment_result.has_critical_threats()

        # Verify all critical threats
        for threat in critical_threats:
            assert threat.severity == SecurityLevel.CRITICAL
            assert threat.confidence_score > 0.9

    def test_add_threat_to_assessment(self):
        """Test adding threats to assessment result."""
        # Create empty assessment
        assessment = SecurityAssessmentResult(
            assessment_id="test",
            component_type="llm",
            component_id="test_llm",
            status=SecurityStatus.COMPLETED,
            overall_score=10.0,
            threats=[],
            recommendations=[],
            test_results=[],
            metadata={},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=1.0,
        )

        # Add a threat
        new_threat = SecurityThreat(
            threat_id="new_threat",
            threat_type="test_threat",
            severity=SecurityLevel.HIGH,
            component_type="llm",
            component_id="test_llm",
            description="Test threat",
            details={},
            mitigation_suggestions=[],
        )

        assessment.add_threat(new_threat)

        # Verify threat was added
        assert len(assessment.threats) == 1
        assert assessment.threats[0] == new_threat

    def test_legacy_format_conversion(self, sample_assessment_result):
        """Test conversion to legacy format."""
        legacy = sample_assessment_result.to_legacy_format()

        assert isinstance(legacy, dict)
        assert legacy["assessment_id"] == "security_test123"
        assert legacy["status"] == "completed"
        assert legacy["overall_score"] == 8.5

        # Check threats are in legacy format
        assert len(legacy["threats"]) == 3
        for threat in legacy["threats"]:
            assert "threat_id" in threat
            assert "severity" in threat
            assert "description" in threat

        # Check recommendations
        assert len(legacy["recommendations"]) == 4
        assert "Implement input validation" in legacy["recommendations"]
