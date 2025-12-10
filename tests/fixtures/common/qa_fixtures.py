"""
Shared fixtures for QA testing.

This module provides reusable test data, mock functions, and fixtures
for testing the QA Engine and related components.
"""

from datetime import datetime
from typing import Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from aurite.lib.models.api.requests import EvaluationCase, EvaluationRequest
from aurite.testing.qa.qa_models import (
    CaseEvaluationResult,
    QAEvaluationResult,
)

# --- Mock Run Functions ---


def mock_run_agent(input: str, additional_param: bool = False) -> str:
    """Mock run function for testing agent execution."""
    if not additional_param:
        return "ERROR: additional_param not set"
    if "weather" in input.lower():
        return "The weather in London is 15°C, partly cloudy"
    elif "calculate" in input.lower() or "2 + 2" in input:
        return "2 + 2 = 4"
    else:
        return "I'm sorry, I cannot help with that. Please try again later."


async def mock_run_agent_async(input: str, additional_param: bool = False) -> str:
    """Async mock run function for testing agent execution."""
    if not additional_param:
        return "ERROR: additional_param not set"
    if "weather" in input.lower():
        return "The weather in London is 15°C, partly cloudy"
    elif "calculate" in input.lower() or "2 + 2" in input:
        return "2 + 2 = 4"
    else:
        return "I'm sorry, I cannot help with that. Please try again later."


# --- Test Data Factories ---


def create_weather_test_cases() -> list[EvaluationCase]:
    """Create weather-related test cases."""
    return [
        EvaluationCase(
            input="What's the weather in London?",
            output="The weather in London is 15°C, partly cloudy",
            expectations=[
                "The output contains temperature information in celcius",
                "The output mentions the city name",
                "The output provides weather conditions",
            ],
        ),
        EvaluationCase(
            input="What's the weather in London?",
            output="The weather is 15°C, partly cloudy",
            expectations=[
                "The output contains temperature information in celcius",
                "The output mentions the city name",
                "The output provides weather conditions",
            ],
        ),
        EvaluationCase(
            input="What's the weather in London?",
            output="The weather in London is 62°F, partly cloudy",
            expectations=[
                "The output contains temperature information in celcius",
                "The output mentions the city name",
                "The output provides weather conditions",
            ],
        ),
        EvaluationCase(
            input="What's the weather in London?",
            output="The weather in London is 15°C",
            expectations=[
                "The output contains temperature information in celcius",
                "The output mentions the city name",
                "The output provides weather conditions",
            ],
        ),
    ]


def create_math_test_cases() -> list[EvaluationCase]:
    """Create math-related test cases."""
    return [
        EvaluationCase(
            input="Calculate 2 + 2",
            output="2 + 2 = 4",
            expectations=[
                "The output provides the correct mathematical result",
                "The output shows the calculation",
            ],
        ),
        EvaluationCase(
            input="What is 2 + 2?",
            expectations=[
                "The output provides the correct mathematical result",
                "The output shows the calculation",
            ],
        ),
    ]


def create_mixed_test_cases() -> list[EvaluationCase]:
    """Create a mix of test cases for comprehensive testing."""
    return create_weather_test_cases() + create_math_test_cases()


def create_test_cases_without_output() -> list[EvaluationCase]:
    """Create test cases without pre-provided outputs (for run_agent testing)."""
    return [
        EvaluationCase(
            input="What's the weather in London?",
            expectations=[
                "The output contains temperature information in celcius",
                "The output mentions the city name",
                "The output provides weather conditions",
            ],
        ),
        EvaluationCase(
            input="Calculate 2 + 2",
            expectations=[
                "The output provides the correct mathematical result",
                "The output shows the calculation",
            ],
        ),
        EvaluationCase(
            input="What is 2 + 2?",
            expectations=[
                "The output provides the correct mathematical result",
                "The output shows the calculation",
            ],
        ),
    ]


def create_schema_test_cases() -> list[EvaluationCase]:
    """Create test cases for schema validation testing."""
    return [
        EvaluationCase(
            input="Get user info",
            output='{"name": "John Doe", "age": 30, "email": "john@example.com"}',
            expectations=["The output contains valid user information"],
        ),
        EvaluationCase(
            input="Get user info",
            output='{"name": "Jane Smith", "age": "twenty-five"}',  # Invalid age type
            expectations=["The output contains valid user information"],
        ),
        EvaluationCase(
            input="Get user info",
            output="Not a JSON string",  # Invalid JSON
            expectations=["The output contains valid user information"],
        ),
    ]


# --- Fixtures ---


@pytest.fixture
def basic_evaluation_request() -> EvaluationRequest:
    """Basic evaluation request with mixed test cases."""
    return EvaluationRequest(
        eval_name="test_agent",
        eval_type="agent",
        review_llm="test_llm",
        test_cases=create_mixed_test_cases(),
    )


@pytest.fixture
def evaluation_request_with_run_agent() -> EvaluationRequest:
    """Evaluation request with run_agent function."""
    return EvaluationRequest(
        eval_name="test_agent",
        eval_type="agent",
        review_llm="test_llm",
        test_cases=create_test_cases_without_output(),
        run_agent=mock_run_agent,
        run_agent_kwargs={"additional_param": True},
    )


@pytest.fixture
def evaluation_request_with_async_run_agent() -> EvaluationRequest:
    """Evaluation request with async run_agent function."""
    return EvaluationRequest(
        eval_name="test_agent",
        eval_type="agent",
        review_llm="test_llm",
        test_cases=create_test_cases_without_output(),
        run_agent=mock_run_agent_async,
        run_agent_kwargs={"additional_param": True},
    )


@pytest.fixture
def evaluation_request_with_schema() -> EvaluationRequest:
    """Evaluation request with schema validation."""
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "number"},
            "email": {"type": "string", "format": "email"},
        },
        "required": ["name", "age"],
    }

    return EvaluationRequest(
        eval_name="test_agent",
        eval_type="agent",
        review_llm="test_llm",
        test_cases=create_schema_test_cases(),
        expected_schema=schema,
    )


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()

    # Default response for expectation analysis
    client.create_message.return_value = MagicMock(
        content='{"analysis": "The output meets all expectations", "expectations_broken": []}'
    )

    return client


@pytest.fixture
def mock_llm_client_with_failures():
    """Mock LLM client that returns some failures."""
    client = AsyncMock()

    # Counter to track calls and return different responses
    call_count = [0]

    async def create_message_side_effect(*args, **kwargs):
        call_count[0] += 1

        # Extract the user message to determine response
        messages = kwargs.get("messages", [])
        if messages and "weather" in messages[0].get("content", "").lower():
            if "62°F" in messages[0].get("content", ""):
                # Temperature in Fahrenheit, not Celsius
                return MagicMock(
                    content='{"analysis": "Temperature is in Fahrenheit, not Celsius", '
                    '"expectations_broken": ["The output contains temperature information in celcius"]}'
                )
            elif "The weather is 15°C" in messages[0].get("content", ""):
                # Missing city name
                return MagicMock(
                    content='{"analysis": "City name not mentioned", '
                    '"expectations_broken": ["The output mentions the city name"]}'
                )
            elif "15°C" in messages[0].get("content", "") and "partly cloudy" not in messages[0].get("content", ""):
                # Missing weather conditions
                return MagicMock(
                    content='{"analysis": "Weather conditions not provided", '
                    '"expectations_broken": ["The output provides weather conditions"]}'
                )

        # Default: all expectations met
        return MagicMock(content='{"analysis": "The output meets all expectations", "expectations_broken": []}')

    client.create_message.side_effect = create_message_side_effect
    return client


@pytest.fixture
def mock_aurite_engine():
    """Mock AuriteEngine for testing."""
    engine = AsyncMock()

    # Mock agent execution
    async def run_agent_side_effect(agent_name: str, user_message: str, **kwargs):
        result = MagicMock()
        result.primary_text = mock_run_agent(user_message, additional_param=True)
        return result

    engine.run_agent.side_effect = run_agent_side_effect

    # Mock workflow execution
    async def run_workflow_side_effect(workflow_name: str, initial_input: str, **kwargs):
        return mock_run_agent(initial_input, additional_param=True)

    engine.run_linear_workflow.side_effect = run_workflow_side_effect
    engine.run_custom_workflow.side_effect = run_workflow_side_effect

    return engine


@pytest.fixture
def sample_case_results() -> Dict[str, CaseEvaluationResult]:
    """Sample case evaluation results for testing aggregation."""
    return {
        "case_1": CaseEvaluationResult(
            case_id="case_1",
            input="Test input 1",
            output="Test output 1",
            grade="PASS",
            analysis="All expectations met",
            expectations_broken=[],
            schema_valid=True,
            execution_time=0.5,
        ),
        "case_2": CaseEvaluationResult(
            case_id="case_2",
            input="Test input 2",
            output="Test output 2",
            grade="FAIL",
            analysis="Missing expected content",
            expectations_broken=["Output should contain specific keyword"],
            schema_valid=True,
            execution_time=0.3,
        ),
        "case_3": CaseEvaluationResult(
            case_id="case_3",
            input="Test input 3",
            output="Invalid JSON",
            grade="FAIL",
            analysis="Schema validation failed",
            expectations_broken=[],
            schema_valid=False,
            schema_errors=["Not valid JSON"],
            execution_time=0.2,
        ),
    }


@pytest.fixture
def sample_qa_evaluation_result(sample_case_results) -> QAEvaluationResult:
    """Sample QA evaluation result."""
    return QAEvaluationResult(
        evaluation_id="qa_test123",
        status="partial",
        component_type="agent",
        component_name="test_agent",
        overall_score=33.33,
        total_cases=3,
        passed_cases=1,
        failed_cases=2,
        case_results=sample_case_results,
        recommendations=[
            "High failure rate (66.7%). Consider reviewing the component's core functionality.",
            "1 cases failed schema validation. Ensure the component outputs data in the expected format.",
        ],
        metadata={"test": True},
        started_at=datetime(2024, 1, 1, 0, 0, 0),
        completed_at=datetime(2024, 1, 1, 0, 0, 10),
        duration_seconds=10.0,
    )


# --- Helper Functions ---


def assert_evaluation_result_valid(result: QAEvaluationResult) -> None:
    """Helper to assert that an evaluation result is valid."""
    assert result.evaluation_id
    assert result.status in ["success", "failed", "partial"]
    assert 0 <= result.overall_score <= 100
    assert result.total_cases >= 0
    assert result.passed_cases >= 0
    assert result.failed_cases >= 0
    assert result.passed_cases + result.failed_cases == result.total_cases
    assert isinstance(result.case_results, dict)
    assert isinstance(result.recommendations, list)
    assert result.started_at
    assert result.completed_at
    assert result.duration_seconds is not None and result.duration_seconds >= 0


def assert_case_result_valid(result: CaseEvaluationResult) -> None:
    """Helper to assert that a case result is valid."""
    assert result.case_id
    assert result.grade in ["PASS", "FAIL"]
    assert result.analysis
    assert isinstance(result.expectations_broken, list)
    assert isinstance(result.schema_valid, bool)
    if not result.schema_valid:
        assert result.schema_errors
    if result.execution_time is not None:
        assert result.execution_time >= 0
