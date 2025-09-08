"""
Integration tests for the QA Engine.

This module tests the QAEngine functionality, including component-specific testers,
test case evaluation, expectation analysis, schema validation, and backward compatibility.
"""

from unittest.mock import MagicMock, patch

import pytest

from aurite.lib.models.api.requests import EvaluationCase, EvaluationRequest
from aurite.testing.qa.components import AgentQATester, WorkflowQATester
from aurite.testing.qa.qa_engine import QAEngine
from aurite.testing.qa.qa_models import (
    CaseEvaluationResult,
    QATestRequest,
)

# Import fixtures
from tests.fixtures.qa_fixtures import (
    assert_case_result_valid,
    assert_evaluation_result_valid,
)


@pytest.mark.anyio
@pytest.mark.testing
class TestQAEngine:
    """Test suite for the QAEngine class."""

    async def test_component_tester_registration(self):
        """Test that component testers are properly registered."""
        qa_engine = QAEngine()

        # Check that testers are registered
        assert "agent" in qa_engine._component_testers
        assert "workflow" in qa_engine._component_testers
        assert "linear_workflow" in qa_engine._component_testers
        assert "custom_workflow" in qa_engine._component_testers

        # Check tester types
        assert isinstance(qa_engine._component_testers["agent"], AgentQATester)
        assert isinstance(qa_engine._component_testers["workflow"], WorkflowQATester)

    async def test_agent_evaluation_through_qa_engine(self, mock_llm_client):
        """Test agent evaluation through QAEngine delegation."""
        from aurite.lib.config.config_manager import ConfigManager

        # Mock config manager to return a valid agent configuration
        mock_config_manager = MagicMock(spec=ConfigManager)
        mock_config_manager.get_config.return_value = {
            "name": "test_agent",
            "type": "agent",
            "llm_config_id": "claude-3-5-sonnet",
            "system_prompt": "You are a helpful assistant",
            "temperature": 0.3,
        }

        qa_engine = QAEngine(config_manager=mock_config_manager)

        # Create agent evaluation request
        request = EvaluationRequest(
            eval_name="test_agent",
            eval_type="agent",
            test_cases=[
                EvaluationCase(
                    input="Hello, how are you?",
                    output="Hello! I'm doing well, thank you for asking. How can I help you today?",
                    expectations=["The response is polite and helpful", "The response acknowledges the greeting"],
                )
            ],
        )

        # Mock the LLM client in the component tester
        with patch("aurite.testing.qa.components.agent.agent_qa_tester.LiteLLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm_client

            result = await qa_engine.evaluate_component(request, executor=None)

        # Verify result structure
        assert_evaluation_result_valid(result)
        assert result.component_type == "agent"
        assert result.total_cases == 1

    async def test_workflow_evaluation_through_qa_engine(self, mock_llm_client):
        """Test workflow evaluation through QAEngine delegation."""
        from aurite.lib.config.config_manager import ConfigManager

        # Mock config manager to return a valid workflow configuration
        mock_config_manager = MagicMock(spec=ConfigManager)
        mock_config_manager.get_config.return_value = {
            "name": "test_workflow",
            "type": "linear_workflow",
            "steps": [{"name": "step1", "agent": "agent1"}, {"name": "step2", "agent": "agent2"}],
            "timeout_seconds": 120,
        }

        qa_engine = QAEngine(config_manager=mock_config_manager)

        # Create workflow evaluation request
        request = EvaluationRequest(
            eval_name="test_workflow",
            eval_type="linear_workflow",
            test_cases=[
                EvaluationCase(
                    input="Process this request",
                    output="Request processed successfully through workflow steps",
                    expectations=["The workflow processes the request", "The output indicates successful completion"],
                )
            ],
        )

        # Mock the LLM client in the component tester
        with patch("aurite.testing.qa.components.workflow.workflow_qa_tester.LiteLLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm_client

            result = await qa_engine.evaluate_component(request, executor=None)

        # Verify result structure
        assert_evaluation_result_valid(result)
        assert result.component_type == "workflow"
        assert result.total_cases == 1

    async def test_fallback_evaluation_for_unsupported_type(self, mock_llm_client):
        """Test fallback evaluation for unsupported component types."""
        qa_engine = QAEngine()

        # Create request with no eval_type to trigger fallback
        request = EvaluationRequest(
            eval_name="test_llm",
            eval_type=None,  # No eval_type to trigger fallback
            test_cases=[
                EvaluationCase(input="Test input", output="Test output", expectations=["The output is helpful"])
            ],
        )

        # Mock the QAEngine to not have an "agent" tester to force fallback
        qa_engine._component_testers = {}  # Remove all component testers to force fallback

        with patch.object(qa_engine, "_get_llm_client", return_value=mock_llm_client):
            result = await qa_engine.evaluate_component(request, executor=None)

        # Should use fallback evaluation
        assert_evaluation_result_valid(result)
        assert result.component_type is None  # Fallback evaluation uses None for component_type
        assert result.total_cases == 1

    async def test_basic_evaluation_with_provided_outputs(self, basic_evaluation_request, mock_llm_client):
        """Test basic evaluation with pre-provided outputs using component testers."""
        from aurite.lib.config.config_manager import ConfigManager

        # Mock config manager to return a valid agent configuration
        mock_config_manager = MagicMock(spec=ConfigManager)
        mock_config_manager.get_config.return_value = {
            "name": "test_agent",
            "type": "agent",
            "llm": "claude-3-5-sonnet",
            "system_prompt": "You are a helpful assistant",
            "temperature": 0.7,
        }

        qa_engine = QAEngine(config_manager=mock_config_manager)

        # Mock the LLM client for component testers
        with patch("aurite.testing.qa.components.agent.agent_qa_tester.LiteLLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm_client

            result = await qa_engine.evaluate_component(basic_evaluation_request)

        # Verify result structure
        assert_evaluation_result_valid(result)
        assert result.component_type == "agent"
        assert result.component_name == "test_agent"
        assert result.total_cases == 6  # 4 weather + 2 math cases

        # Verify all cases were evaluated
        assert len(result.case_results) == 6

        # Check that each case has a valid result
        for _case_id, case_result in result.case_results.items():
            assert_case_result_valid(case_result)

    async def test_schema_validation_through_component_tester(self, evaluation_request_with_schema, mock_llm_client):
        """Test schema validation functionality through component testers."""
        from aurite.lib.config.config_manager import ConfigManager

        # Mock config manager to return a valid agent configuration
        mock_config_manager = MagicMock(spec=ConfigManager)
        mock_config_manager.get_config.return_value = {
            "name": "test_agent",
            "type": "agent",
            "llm": "claude-3-5-sonnet",
            "system_prompt": "You are a helpful assistant that returns JSON data",
            "temperature": 0.3,
        }

        qa_engine = QAEngine(config_manager=mock_config_manager)

        with patch("aurite.testing.qa.components.agent.agent_qa_tester.LiteLLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm_client

            result = await qa_engine.evaluate_component(evaluation_request_with_schema)

        assert_evaluation_result_valid(result)

        # Check schema validation results
        case_ids = list(result.case_results.keys())

        # First case should pass schema validation
        first_result = result.case_results[case_ids[0]]
        assert first_result.schema_valid is True
        assert first_result.grade == "PASS"

        # Second case should fail (age is string instead of number)
        second_result = result.case_results[case_ids[1]]
        assert second_result.schema_valid is False
        assert second_result.grade == "FAIL"
        assert len(second_result.schema_errors) > 0

        # Third case should fail (not valid JSON)
        third_result = result.case_results[case_ids[2]]
        assert third_result.schema_valid is False
        assert third_result.grade == "FAIL"

    async def test_error_handling_in_component_delegation(self, mock_llm_client):
        """Test error handling when component tester fails."""
        from aurite.lib.config.config_manager import ConfigManager

        # Mock config manager to return a valid agent configuration
        mock_config_manager = MagicMock(spec=ConfigManager)
        mock_config_manager.get_config.return_value = {
            "name": "test_agent",
            "type": "agent",
            "llm": "claude-3-5-sonnet",
            "system_prompt": "You are a helpful assistant",
            "temperature": 0.7,
        }

        qa_engine = QAEngine(config_manager=mock_config_manager)

        # Create a request that will cause an error in the component tester
        request = EvaluationRequest(
            eval_name="test_agent",
            eval_type="agent",
            test_cases=[
                EvaluationCase(
                    input="Test",
                    expectations=["Should handle error"],
                )
            ],
        )

        # Mock component tester to raise an exception
        with patch.object(qa_engine._component_testers["agent"], "test_component") as mock_test:
            mock_test.side_effect = Exception("Component tester failed")

            with pytest.raises(Exception, match="Component tester failed"):
                await qa_engine.evaluate_component(request, None)

    async def test_component_config_loading(self, mock_llm_client):
        """Test that component configurations are loaded from ConfigManager."""
        from aurite.lib.config.config_manager import ConfigManager

        # Mock config manager
        mock_config_manager = MagicMock(spec=ConfigManager)
        mock_config_manager.get_config.return_value = {
            "name": "test_agent",
            "type": "agent",
            "llm": "claude-3-5-sonnet",
            "system_prompt": "You are a helpful assistant",
        }

        qa_engine = QAEngine(config_manager=mock_config_manager)

        request = EvaluationRequest(
            eval_name="test_agent",
            eval_type="agent",
            test_cases=[EvaluationCase(input="Hello", output="Hi there!", expectations=["The response is friendly"])],
        )

        with patch("aurite.testing.qa.components.agent.agent_qa_tester.LiteLLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm_client

            result = await qa_engine.evaluate_component(request, executor=None)

        # Verify config was loaded
        mock_config_manager.get_config.assert_called_with(component_type="agent", component_id="test_agent")

        assert_evaluation_result_valid(result)


@pytest.mark.anyio
@pytest.mark.testing
class TestComponentTesters:
    """Test suite for component-specific testers."""

    async def test_agent_qa_tester_direct(self, mock_llm_client):
        """Test AgentQATester directly."""
        agent_tester = AgentQATester()

        # Create test request
        request = QATestRequest(
            component_type="agent",
            component_config={
                "name": "test_agent",
                "type": "agent",
                "llm": "claude-3-5-sonnet",
                "system_prompt": "You are a helpful research assistant",
                "tools": ["web_search"],
                "temperature": 0.3,
            },
            test_cases=[
                EvaluationCase(
                    input="Research renewable energy",
                    output="Renewable energy sources include solar, wind, and hydroelectric power...",
                    expectations=[
                        "The response provides information about renewable energy",
                        "The response is informative and well-structured",
                    ],
                )
            ],
            eval_name="test_agent",
            eval_type="agent",
        )

        with patch("aurite.testing.qa.components.agent.agent_qa_tester.LiteLLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm_client

            result = await agent_tester.test_component(request, executor=None)

        assert_evaluation_result_valid(result)
        assert result.component_type == "agent"
        assert result.total_cases == 1

    async def test_workflow_qa_tester_direct(self, mock_llm_client):
        """Test WorkflowQATester directly."""
        workflow_tester = WorkflowQATester()

        # Create test request
        request = QATestRequest(
            component_type="workflow",
            component_config={
                "name": "test_workflow",
                "type": "linear_workflow",
                "steps": [{"name": "step1", "agent": "agent1"}, {"name": "step2", "agent": "agent2"}],
                "timeout_seconds": 120,
            },
            test_cases=[
                EvaluationCase(
                    input="Process this workflow",
                    output="Workflow completed successfully with coordinated agent steps",
                    expectations=["The workflow executes all steps", "The workflow shows proper coordination"],
                )
            ],
            eval_name="test_workflow",
            eval_type="linear_workflow",
        )

        with patch("aurite.testing.qa.components.workflow.workflow_qa_tester.LiteLLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm_client

            result = await workflow_tester.test_component(request, executor=None)

        assert_evaluation_result_valid(result)
        assert result.component_type == "workflow"
        assert result.total_cases == 1

    async def test_agent_tester_validation(self):
        """Test AgentQATester request validation."""
        agent_tester = AgentQATester()

        # Test invalid request
        invalid_request = QATestRequest(
            component_type="workflow",  # Wrong type for agent tester
            component_config={},
            test_cases=[],
        )

        errors = agent_tester.validate_request(invalid_request)
        assert len(errors) > 0
        assert any("Component type must be 'agent'" in error for error in errors)

    async def test_workflow_tester_validation(self):
        """Test WorkflowQATester request validation."""
        workflow_tester = WorkflowQATester()

        # Test invalid request
        invalid_request = QATestRequest(
            component_type="agent",  # Wrong type for workflow tester
            component_config={},
            test_cases=[],
        )

        errors = workflow_tester.validate_request(invalid_request)
        assert len(errors) > 0
        assert any("Component type must be workflow-related" in error for error in errors)

    async def test_agent_recommendations(self, mock_llm_client):
        """Test agent-specific recommendations generation."""
        agent_tester = AgentQATester()

        # Create request with problematic agent config
        request = QATestRequest(
            component_type="agent",
            component_config={
                "name": "problematic_agent",
                "type": "agent",
                "llm": "gpt-3.5-turbo",
                "system_prompt": "AI",  # Very short prompt
                "tools": [],  # No tools
                "temperature": 1.5,  # Very high temperature
                "max_tokens": 100,  # Very low max tokens
                "conversation_memory": False,
            },
            test_cases=[
                EvaluationCase(
                    input="Research something complex",
                    output="I can't help with that",
                    expectations=["The response provides detailed research", "The response uses appropriate tools"],
                )
            ],
            eval_name="problematic_agent",
            eval_type="agent",
        )

        # Mock LLM to return failures
        mock_llm_client.create_message.return_value = MagicMock(
            content='{"analysis": "Agent failed to meet expectations", "expectations_broken": ["The response provides detailed research", "The response uses appropriate tools"]}'
        )

        with patch("aurite.testing.qa.components.agent.agent_qa_tester.LiteLLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm_client

            result = await agent_tester.test_component(request, executor=None)

        # Should have agent-specific recommendations
        recommendations = result.recommendations
        assert len(recommendations) > 0

        # Check for specific agent recommendations
        rec_text = " ".join(recommendations).lower()
        assert "system prompt" in rec_text or "temperature" in rec_text or "tools" in rec_text

    async def test_workflow_recommendations(self, mock_llm_client):
        """Test workflow-specific recommendations generation."""
        workflow_tester = WorkflowQATester()

        # Create request with problematic workflow config
        request = QATestRequest(
            component_type="workflow",
            component_config={
                "name": "problematic_workflow",
                "type": "linear_workflow",
                "steps": [
                    {"agent": "agent1"},  # Missing name
                    {"name": "step2"},  # Missing agent
                ],
                "timeout_seconds": 5,  # Very short timeout
                "parallel_execution": True,  # Bad for linear workflow
            },
            test_cases=[
                EvaluationCase(
                    input="Execute workflow",
                    output="Workflow failed",
                    expectations=["The workflow executes successfully", "The workflow coordinates agents properly"],
                )
            ],
            eval_name="problematic_workflow",
            eval_type="linear_workflow",
        )

        # Mock LLM to return failures
        mock_llm_client.create_message.return_value = MagicMock(
            content='{"analysis": "Workflow failed coordination", "expectations_broken": ["The workflow executes successfully", "The workflow coordinates agents properly"]}'
        )

        with patch("aurite.testing.qa.components.workflow.workflow_qa_tester.LiteLLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm_client

            result = await workflow_tester.test_component(request, executor=None)

        # Should have workflow-specific recommendations
        recommendations = result.recommendations
        assert len(recommendations) > 0

        # Check for specific workflow recommendations
        rec_text = " ".join(recommendations).lower()
        assert any(keyword in rec_text for keyword in ["step", "timeout", "parallel", "agent"])


@pytest.mark.anyio
@pytest.mark.testing
class TestQAModels:
    """Test suite for QA model classes."""

    def test_qa_evaluation_result_to_legacy_format(self, sample_qa_evaluation_result):
        """Test conversion to legacy format."""
        legacy = sample_qa_evaluation_result.to_legacy_format()

        assert isinstance(legacy, dict)
        assert legacy["status"] == "partial"
        assert "result" in legacy

        # Check case results are in legacy format
        for _case_id, case_data in legacy["result"].items():
            assert "input" in case_data
            assert "output" in case_data
            assert "grade" in case_data
            assert "analysis" in case_data
            assert "expectations_broken" in case_data

    def test_case_evaluation_result_validation(self):
        """Test CaseEvaluationResult model validation."""
        # Valid case result
        result = CaseEvaluationResult(
            case_id="test_1",
            input="Test input",
            output="Test output",
            grade="PASS",
            analysis="All good",
            expectations_broken=[],
        )

        assert result.case_id == "test_1"
        assert result.grade == "PASS"
        assert result.schema_valid is True  # Default value

        # Test with schema failure
        result_with_schema_error = CaseEvaluationResult(
            case_id="test_2",
            input="Test input",
            output="Invalid output",
            grade="FAIL",
            analysis="Schema validation failed",
            expectations_broken=[],
            schema_valid=False,
            schema_errors=["Not valid JSON"],
        )

        assert result_with_schema_error.schema_valid is False
        assert len(result_with_schema_error.schema_errors) == 1

    def test_qa_test_request_validation(self):
        """Test QATestRequest model validation."""
        # Valid request
        request = QATestRequest(
            component_type="agent",
            component_config={"name": "test_agent", "type": "agent"},
            test_cases=[EvaluationCase(input="Test", expectations=["Should work"])],
        )

        assert request.component_type == "agent"
        assert request.framework == "aurite"  # Default value
        assert len(request.test_cases) == 1
